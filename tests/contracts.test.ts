/**
 * Executable contract tests derived from `.spec/contracts/**`,
 * `.spec/policies/**`, and feature acceptance criteria.
 *
 * The helpers in this file are intentionally deterministic: they encode the
 * fail-closed gates that must protect autonomous GitHub MCP writes, merges,
 * runtime state, and Discord notifications before production adapters exist.
 */

import { test } from "node:test";
import * as assert from "node:assert";
import * as fs from "node:fs";
import { execFileSync } from "node:child_process";
import {
	malformedResponseToExternalServiceDecision,
	timeoutRejectionToExternalServiceDecision,
	type ExternalServiceDecision,
} from "../src/external/fail-closed-adapter";
import {
	validateToolPolicy,
	type MergePreconditions,
} from "../src/mcp/tool-policy";
import {
	assertValidJsonSchema,
	validateJsonSchema,
	type JsonSchema,
} from "../src/validation/schema-validator";

type ProbeResult = { ok: boolean; status: number };
type UrlProbe = (url: string) => Promise<ProbeResult>;

interface CloudflareDeploymentEvent {
	id: string;
	project_name: string;
	deployment: {
		id: string;
		url: string;
		environment: "production" | "preview";
		status: "success" | "failure" | "pending" | "skipped" | "canceled";
		created_on: string;
		modified_on: string;
		meta: {
			branch: string;
			commit_hash: string;
			commit_message: string;
		};
	};
}

function canAutonomouslyMerge(gates: MergePreconditions): boolean {
	return Object.values(gates).every((status) => status === "passed");
}

interface NotificationState {
	notifiedDeploymentIds: string[];
	notifiedCommitHashes: string[];
}

interface NotificationConfig {
	publicBaseUrl: string;
	latestReportUrl: string;
}

interface NotificationDecision {
	shouldNotify: boolean;
	reason: string;
	reportUrlChecked: boolean;
}

interface ExternalApiFailureDecision
	extends NotificationDecision,
		ExternalServiceDecision {}

type ShouldNotifyDiscord = (
	event: CloudflareDeploymentEvent,
	state: NotificationState,
	config: NotificationConfig,
	probeReportUrl: UrlProbe,
) => Promise<NotificationDecision>;

interface ContractSchemaValidationError extends Error {
	validationErrors: ReturnType<typeof validateJsonSchema>;
}

function readJsonSchema(schemaPath: string): JsonSchema {
	return JSON.parse(fs.readFileSync(schemaPath, "utf8")) as JsonSchema;
}

function assertValidExternalPayload(schema: JsonSchema, value: unknown): void {
	assertValidJsonSchema(
		schema,
		value,
		"external payload schema validation failed",
	);
}

function assertContractSchemaValid(schema: JsonSchema, payload: unknown): void {
	const errors = validateJsonSchema(schema, payload);
	if (errors.length === 0) return;

	const error = new Error(
		`Contract schema validation failed immediately: ${errors
			.map(({ path, message }) => `${path} ${message}`)
			.join("; ")}`,
	) as ContractSchemaValidationError;
	error.validationErrors = errors;
	throw error;
}

async function evaluateProbeFailureNotificationContract(
	event: CloudflareDeploymentEvent,
	state: NotificationState,
	config: NotificationConfig,
	probeReportUrl: UrlProbe,
): Promise<ExternalApiFailureDecision> {
	if (event.deployment.status !== "success") {
		return {
			shouldNotify: false,
			reason: `deployment status is ${event.deployment.status}; pending/error responses do not notify`,
			reportUrlChecked: false,
			status: "pending",
			stateFrozen: true,
			retryAttempted: false,
		};
	}

	try {
		const probeDecision = malformedResponseToExternalServiceDecision(
			await probeReportUrl(config.latestReportUrl),
		);
		if (probeDecision.status !== "ready") {
			return {
				shouldNotify: false,
				reason: probeDecision.reason,
				reportUrlChecked: true,
				status: probeDecision.status,
				stateFrozen: probeDecision.stateFrozen,
				retryAttempted: probeDecision.retryAttempted,
			};
		}
	} catch (error) {
		const probeDecision = timeoutRejectionToExternalServiceDecision(error);
		return {
			shouldNotify: false,
			reason: probeDecision.reason,
			reportUrlChecked: true,
			status: probeDecision.status,
			stateFrozen: probeDecision.stateFrozen,
			retryAttempted: probeDecision.retryAttempted,
		};
	}

	return {
		shouldNotify:
			!state.notifiedDeploymentIds.includes(event.deployment.id) &&
			!state.notifiedCommitHashes.includes(event.deployment.meta.commit_hash),
		reason: "report URL is reachable",
		reportUrlChecked: true,
		status: "ready",
		stateFrozen: false,
		retryAttempted: false,
	};
}

const allGreenGates: MergePreconditions = {
	ci: "passed",
	takumiGuard: "passed",
	deterministicContentGuards: "passed",
	branchPolicy: "passed",
	immutableFiles: "passed",
	internalLinks: "passed",
};

const deploymentSuccess: CloudflareDeploymentEvent = {
	id: "evt_pages_deploy_success",
	project_name: "osint-kaname",
	deployment: {
		id: "deploy_id_98765",
		url: "https://osint-kaname.pages.dev",
		environment: "production",
		status: "success",
		created_on: "2026-05-27T09:45:00Z",
		modified_on: "2026-05-27T09:50:00Z",
		meta: {
			branch: "main",
			commit_hash: "a1b2c3d4e5f6g7h8i9j0",
			commit_message:
				"[Aegis-Reviewer] Self-Merge: Intelligence Update Passed Review",
		},
	},
};

test("MCP JSON-RPC contracts from .spec/contracts/mcp-contracts.md", async (t) => {
	await t.test(
		"create_or_update_file rejects direct writer writes to main",
		() => {
			const call = {
				jsonrpc: "2.0",
				method: "tools/call",
				params: {
					name: "create_or_update_file",
					arguments: {
						owner: "Ningensei848",
						repo: "kaname-vault",
						path: "topics/gov-agencies/NCO.md",
						content: "# unsafe direct write",
						branch: "main",
						message: "[Aegis-Writer] Unsafe direct main write",
					},
				},
				id: 201,
			} as const;

			assert.deepStrictEqual(validateToolPolicy(call), [
				"Writer branch must be osint/*",
			]);
		},
	);

	await t.test(
		"invalid MCP JSON-RPC payload fails contract validation immediately",
		() => {
			const mcpToolCallSchema = readJsonSchema(
				".spec/schemas/mcp-tool-call.schema.json",
			);
			const missingJsonRpc = {
				method: "tools/call",
				params: {
					name: "create_issue",
					arguments: { owner: "Ningensei848", repo: "kaname-vault" },
				},
				id: 301,
			};

			assert.throws(
				() => assertContractSchemaValid(mcpToolCallSchema, missingJsonRpc),
				/Contract schema validation failed immediately: .*missing required property jsonrpc/,
			);
		},
	);

	await t.test(
		"external MCP payload helper fails closed and accepts valid payloads",
		() => {
			const mcpToolCallSchema = readJsonSchema(
				".spec/schemas/mcp-tool-call.schema.json",
			);
			const validPayload = {
				jsonrpc: "2.0",
				method: "tools/call",
				params: {
					name: "create_issue",
					arguments: { owner: "Ningensei848", repo: "kaname-vault" },
				},
				id: 302,
			};
			const invalidPayload = {
				...validPayload,
				params: {
					...validPayload.params,
					name: "delete_repository",
				},
			};

			assert.throws(
				() => assertValidExternalPayload(mcpToolCallSchema, invalidPayload),
				/schema validation failed/,
			);
			assert.doesNotThrow(() =>
				assertValidExternalPayload(mcpToolCallSchema, validPayload),
			);
		},
	);

	await t.test("defers MCP fixture and policy ownership to F003 tests", () => {
		const contract = fs.readFileSync(
			".spec/contracts/mcp-contracts.md",
			"utf8",
		);

		assert.match(contract, /create_or_update_file/);
		assert.match(contract, /merge_pull_request/);
		assert.match(contract, /create_issue/);
	});
});

test("Protected merge and Takumi Guard gates fail closed", async (t) => {
	await t.test(
		"all protected autonomous merge requirements must be green",
		() => {
			assert.strictEqual(canAutonomouslyMerge(allGreenGates), true);
		},
	);

	await t.test(
		"any failed, unavailable, or indeterminate gate blocks merge_pull_request",
		() => {
			const gateNames = Object.keys(allGreenGates) as Array<
				keyof MergePreconditions
			>;

			for (const gateName of gateNames) {
				for (const badStatus of [
					"failed",
					"unavailable",
					"indeterminate",
				] as const) {
					const gates = { ...allGreenGates, [gateName]: badStatus };
					assert.strictEqual(
						canAutonomouslyMerge(gates),
						false,
						`${gateName}=${badStatus} must fail closed`,
					);
				}
			}
		},
	);
});

test("Cloudflare Pages deployment and Discord webhook cross-contracts", async (t) => {
	await t.test(
		"notification gate contract is the async DI surface owned by F004 tests",
		async () => {
			const probeReportUrl: UrlProbe = async (url) => ({
				ok: url === "https://osint-kaname.pages.dev/reports/2026-05-27_Report",
				status: 200,
			});
			const contract: ShouldNotifyDiscord = async (
				event,
				state,
				config,
				probe,
			) => {
				assert.strictEqual(event, deploymentSuccess);
				assert.deepStrictEqual(state, {
					notifiedDeploymentIds: [],
					notifiedCommitHashes: [],
				});
				assert.strictEqual(
					config.latestReportUrl,
					"https://osint-kaname.pages.dev/reports/2026-05-27_Report",
				);
				const probeResult = await probe(config.latestReportUrl);
				return {
					shouldNotify: probeResult.ok,
					reason: "contract shape only; decision logic is covered in F004",
					reportUrlChecked: true,
				};
			};

			const decision = await contract(
				deploymentSuccess,
				{ notifiedDeploymentIds: [], notifiedCommitHashes: [] },
				{
					publicBaseUrl: "https://osint-kaname.pages.dev",
					latestReportUrl:
						"https://osint-kaname.pages.dev/reports/2026-05-27_Report",
				},
				probeReportUrl,
			);

			assert.deepStrictEqual(decision, {
				shouldNotify: true,
				reason: "contract shape only; decision logic is covered in F004",
				reportUrlChecked: true,
			});
		},
	);

	await t.test(
		"invalid Cloudflare deployment payload fails contract validation immediately",
		() => {
			const deploymentSchema = readJsonSchema(
				".spec/schemas/cloudflare-pages-deployment.schema.json",
			);
			const invalidDeployment = {
				...deploymentSuccess,
				deployment: {
					...deploymentSuccess.deployment,
					status: "unknown",
					meta: {
						branch: deploymentSuccess.deployment.meta.branch,
						commit_message: deploymentSuccess.deployment.meta.commit_message,
					},
				},
			};

			assert.throws(
				() => assertContractSchemaValid(deploymentSchema, invalidDeployment),
				/Contract schema validation failed immediately: .*(expected enum value|missing required property commit_hash)/,
			);
		},
	);

	await t.test(
		"broken report URL probe response is a single pending/error decision without retry increment",
		async () => {
			let callCount = 0;
			let retryCounter = 0;
			const brokenProbe: UrlProbe = async () => {
				callCount += 1;
				return { ok: false, status: 0 };
			};

			const decision = await evaluateProbeFailureNotificationContract(
				deploymentSuccess,
				{ notifiedDeploymentIds: [], notifiedCommitHashes: [] },
				{
					publicBaseUrl: "https://osint-kaname.pages.dev",
					latestReportUrl:
						"https://osint-kaname.pages.dev/reports/2026-05-27_Report",
				},
				brokenProbe,
			);
			if (decision.shouldNotify) retryCounter += 1;

			assert.strictEqual(callCount, 1);
			assert.strictEqual(retryCounter, 0);
			assert.strictEqual(decision.shouldNotify, false);
			assert.strictEqual(decision.status, "pending");
			assert.strictEqual(decision.stateFrozen, true);
			assert.strictEqual(decision.retryAttempted, false);
			assert.match(decision.reason, /pending|error/);
		},
	);

	await t.test(
		"malformed report URL probe response is converted without retrying",
		async () => {
			let callCount = 0;
			const malformedProbe = (async () => {
				callCount += 1;
				return { status: Number.NaN };
			}) as unknown as UrlProbe;

			const decision = await evaluateProbeFailureNotificationContract(
				deploymentSuccess,
				{ notifiedDeploymentIds: [], notifiedCommitHashes: [] },
				{
					publicBaseUrl: "https://osint-kaname.pages.dev",
					latestReportUrl:
						"https://osint-kaname.pages.dev/reports/2026-05-27_Report",
				},
				malformedProbe,
			);

			assert.strictEqual(callCount, 1);
			assert.strictEqual(decision.shouldNotify, false);
			assert.strictEqual(decision.status, "error");
			assert.strictEqual(decision.stateFrozen, true);
			assert.strictEqual(decision.retryAttempted, false);
			assert.match(decision.reason, /malformed response/);
		},
	);

	await t.test(
		"rejected report URL probe is a single error decision without retry increment",
		async () => {
			let callCount = 0;
			let retryCounter = 0;
			const rejectingProbe: UrlProbe = async () => {
				callCount += 1;
				throw new Error("network timeout");
			};

			const decision = await evaluateProbeFailureNotificationContract(
				deploymentSuccess,
				{ notifiedDeploymentIds: [], notifiedCommitHashes: [] },
				{
					publicBaseUrl: "https://osint-kaname.pages.dev",
					latestReportUrl:
						"https://osint-kaname.pages.dev/reports/2026-05-27_Report",
				},
				rejectingProbe,
			);
			if (decision.shouldNotify) retryCounter += 1;

			assert.strictEqual(callCount, 1);
			assert.strictEqual(retryCounter, 0);
			assert.strictEqual(decision.shouldNotify, false);
			assert.match(decision.status, /pending|error/);
			assert.strictEqual(decision.stateFrozen, true);
			assert.strictEqual(decision.retryAttempted, false);
			assert.match(decision.reason, /pending|error/);
		},
	);
});

test("Crawler state repository-safety acceptance criteria", async (t) => {
	await t.test("crawler-state.json is ignored and never tracked in Git", () => {
		const gitignore = fs.readFileSync(".gitignore", "utf8");
		assert.match(gitignore, /(^|\n)crawler-state\.json(\n|$)/);

		const trackedFiles = execFileSync("git", ["ls-files"], {
			encoding: "utf8",
		})
			.split("\n")
			.filter(Boolean);
		assert.deepStrictEqual(
			trackedFiles.filter((filePath) =>
				filePath.endsWith("crawler-state.json"),
			),
			[],
		);
	});
});
