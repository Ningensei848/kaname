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
import type { MergePreconditions } from "../src/mcp/tool-policy";

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

type ShouldNotifyDiscord = (
	event: CloudflareDeploymentEvent,
	state: NotificationState,
	config: NotificationConfig,
	probeReportUrl: UrlProbe,
) => Promise<NotificationDecision>;

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
