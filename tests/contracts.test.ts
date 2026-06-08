/**
 * Executable contract tests derived from `.spec/contracts/**`,
 * `.spec/policies/**`, and feature acceptance criteria.
 *
 * The helpers in this file are intentionally deterministic: they encode the
 * fail-closed gates that must protect autonomous GitHub MCP writes, merges,
 * and runtime state before production adapters exist. Discord notification
 * prototypes live in `tests/f004-cloudflare-discord.test.ts`.
 */

import { test } from "node:test";
import * as assert from "node:assert";
import * as fs from "node:fs";
import { execFileSync } from "node:child_process";

interface JsonRpcToolCall {
	jsonrpc: string;
	method: string;
	params: {
		name: string;
		arguments: Record<string, unknown>;
	};
	id: number;
}

type GateStatus = "passed" | "failed" | "unavailable" | "indeterminate";

interface MergePreconditions {
	ci: GateStatus;
	takumiGuard: GateStatus;
	deterministicContentGuards: GateStatus;
	branchPolicy: GateStatus;
	immutableFiles: GateStatus;
	internalLinks: GateStatus;
}

const owner = "example-org";
const repo = "kaname-vault";

function baseCall(
	name: string,
	args: Record<string, unknown>,
	id: number,
): JsonRpcToolCall {
	return {
		jsonrpc: "2.0",
		method: "tools/call",
		params: { name, arguments: args },
		id,
	};
}

function assertJsonRpcToolEnvelope(call: JsonRpcToolCall): void {
	assert.strictEqual(call.jsonrpc, "2.0");
	assert.strictEqual(call.method, "tools/call");
	assert.ok(Number.isInteger(call.id), "JSON-RPC id must be an integer");
	assert.ok(call.params.name.length > 0, "tool name is required");
	assert.strictEqual(typeof call.params.arguments.owner, "string");
	assert.strictEqual(typeof call.params.arguments.repo, "string");
}

function isAllowedContentPath(filePath: string): boolean {
	return (
		/^topics\/.+\.md$/.test(filePath) ||
		/^reports\/\d{4}-\d{2}-\d{2}_Report\.md$/.test(filePath)
	);
}

function assertValidMcpCall(
	call: JsonRpcToolCall,
	preconditions?: MergePreconditions,
): void {
	assertJsonRpcToolEnvelope(call);

	const args = call.params.arguments;
	switch (call.params.name) {
		case "create_or_update_file": {
			assert.match(String(args.branch), /^osint\//);
			assert.notStrictEqual(args.branch, "main");
			assert.ok(
				isAllowedContentPath(String(args.path)),
				"Writer may only modify approved generated content paths",
			);
			assert.notStrictEqual(
				String(args.path),
				"crawler-state.json",
				"runtime crawler state must not be written through Git",
			);
			assert.strictEqual(typeof args.content, "string");
			assert.match(String(args.message), /^\[Aegis-Writer\]/);
			return;
		}
		case "create_pull_request": {
			assert.match(String(args.head), /^osint\//);
			assert.strictEqual(args.base, "main");
			assert.match(String(args.title), /^\[Wiki-Sync\]/);
			assert.ok(String(args.body).includes("## 提案要約"));
			return;
		}
		case "merge_pull_request": {
			assert.ok(preconditions, "merge calls require explicit gate evidence");
			assert.strictEqual(canAutonomouslyMerge(preconditions), true);
			assert.strictEqual(args.merge_method, "squash");
			assert.match(String(args.commit_title), /^\[Aegis-Reviewer\]/);
			return;
		}
		case "create_issue": {
			assert.match(String(args.title), /^\[System Error\]/);
			assert.ok(String(args.body).includes("## 障害発生報告"));
			return;
		}
		default:
			assert.fail(`Unexpected MCP tool name: ${call.params.name}`);
	}
}

function canAutonomouslyMerge(gates: MergePreconditions): boolean {
	return Object.values(gates).every((status) => status === "passed");
}

const allGreenGates: MergePreconditions = {
	ci: "passed",
	takumiGuard: "passed",
	deterministicContentGuards: "passed",
	branchPolicy: "passed",
	immutableFiles: "passed",
	internalLinks: "passed",
};

test("MCP JSON-RPC contracts from .spec/contracts/mcp-contracts.md", async (t) => {
	await t.test(
		"accepts all canonical tool fixtures with strict envelopes",
		() => {
			const calls = [
				baseCall(
					"create_or_update_file",
					{
						owner,
						repo,
						path: "topics/gov-agencies/NCO.md",
						content: "---\ntitle: NCO\n---\n# 本文...",
						branch: "osint/content-acd-update-20260527",
						message: "[Aegis-Writer] Update NCO cybersecurity policy",
					},
					101,
				),
				baseCall(
					"create_pull_request",
					{
						owner,
						repo,
						title: "[Wiki-Sync] Intelligence Update (2026-05-27)",
						head: "osint/content-acd-update-20260527",
						base: "main",
						body: "## 提案要約\n- 既存のトピック `[[能動的サイバー防御]]` のインクリメンタル更新を完了。",
					},
					102,
				),
				baseCall(
					"merge_pull_request",
					{
						owner,
						repo,
						pull_number: 42,
						merge_method: "squash",
						commit_title:
							"[Aegis-Reviewer] Self-Merge: Intelligence Update Passed Review",
					},
					103,
				),
				baseCall(
					"create_issue",
					{
						owner,
						repo,
						title: "[System Error] Crawling Failed for ID: nco",
						body: "## 障害発生報告\n- **対象ソース**: 国家サイバー統括室",
					},
					104,
				),
			];

			for (const call of calls) {
				assertValidMcpCall(call, allGreenGates);
			}
		},
	);

	await t.test(
		"rejects Writer calls outside osint branches and approved paths",
		() => {
			const invalidCalls = [
				baseCall(
					"create_or_update_file",
					{
						owner,
						repo,
						path: "topics/gov-agencies/NCO.md",
						content: "# overwrite",
						branch: "main",
						message: "[Aegis-Writer] direct main write",
					},
					201,
				),
				baseCall(
					"create_or_update_file",
					{
						owner,
						repo,
						path: "crawler-state.json",
						content: "{}",
						branch: "osint/runtime-state",
						message: "[Aegis-Writer] Commit crawler state",
					},
					202,
				),
				baseCall(
					"create_or_update_file",
					{
						owner,
						repo,
						path: "src/orchestrator.ts",
						content: "malicious code",
						branch: "osint/content-update",
						message: "[Aegis-Writer] Modify runtime code",
					},
					203,
				),
			];

			for (const call of invalidCalls) {
				assert.throws(() => assertValidMcpCall(call, allGreenGates));
			}
		},
	);
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
