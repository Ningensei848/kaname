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

interface PagesDeploymentEvent {
	id: string;
	project_name: string;
	deployment: {
		id: string;
		url: string;
		environment: string;
		status: string;
		created_on: string;
		modified_on: string;
		meta: {
			branch: string;
			commit_hash: string;
			commit_message: string;
		};
	};
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

function shouldNotifyDiscord(
	event: PagesDeploymentEvent,
	publicBaseUrl: string,
	latestReportLive: boolean,
	notifiedCommitHashes: Set<string>,
): boolean {
	return (
		event.deployment.status === "success" &&
		event.deployment.environment === "production" &&
		event.deployment.meta.branch === "main" &&
		event.deployment.url === publicBaseUrl &&
		latestReportLive &&
		!notifiedCommitHashes.has(event.deployment.meta.commit_hash)
	);
}

function buildDiscordPayload(event: PagesDeploymentEvent) {
	return {
		username: "Aegis-Intelligence",
		avatar_url:
			"https://raw.githubusercontent.com/github/spec-kit/main/media/logo_small.webp",
		embeds: [
			{
				title: "🛡️ インテリジェンス更新 ＆ 本番デプロイ成功報告",
				description:
					"提案・査読エージェントによる検証をすべてパスし、最新のサイバーセキュリティインテリジェンスが本番環境へ安全にホスティングされました。",
				url: event.deployment.url,
				color: 3066993,
				fields: [
					{
						name: "📑 更新要約レポート (最新)",
						value:
							"[2026-05-27_Report](https://osint-kaname.pages.dev/reports/2026-05-27_Report)",
						inline: true,
					},
					{
						name: "🔗 関連トピック解説",
						value:
							"- [[能動的サイバー防御]](https://osint-kaname.pages.dev/topics/gov-agencies/NCO)\n- [[サイバー演習CYDER]](https://osint-kaname.pages.dev/topics/cyber-exercises/CYDER)",
						inline: false,
					},
					{
						name: "⚙️ 実行履歴",
						value: `マージコミット: \`${event.deployment.meta.commit_hash.slice(0, 10)}\` by Aegis-Reviewer`,
						inline: false,
					},
				],
				footer: {
					text: "`kaname` • サーバーレス自律監視システム",
					icon_url:
						"https://raw.githubusercontent.com/github/spec-kit/main/media/logo_small.webp",
				},
				timestamp: new Date(event.deployment.modified_on).toISOString(),
			},
		],
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

const deploymentSuccess: PagesDeploymentEvent = {
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

test("Cloudflare Pages deployment gate and Discord webhook contract", async (t) => {
	await t.test(
		"allows notification only for first successful production main deployment",
		() => {
			assert.strictEqual(
				shouldNotifyDiscord(
					deploymentSuccess,
					"https://osint-kaname.pages.dev",
					true,
					new Set(),
				),
				true,
			);
		},
	);

	await t.test(
		"blocks every non-production, non-main, failed, broken, or duplicate event",
		() => {
			const cases: Array<[string, PagesDeploymentEvent, boolean, Set<string>]> =
				[
					[
						"failed deployment",
						{
							...deploymentSuccess,
							deployment: {
								...deploymentSuccess.deployment,
								status: "failure",
							},
						},
						true,
						new Set(),
					],
					[
						"preview environment",
						{
							...deploymentSuccess,
							deployment: {
								...deploymentSuccess.deployment,
								environment: "preview",
							},
						},
						true,
						new Set(),
					],
					[
						"non-main branch",
						{
							...deploymentSuccess,
							deployment: {
								...deploymentSuccess.deployment,
								meta: {
									...deploymentSuccess.deployment.meta,
									branch: "osint/draft",
								},
							},
						},
						true,
						new Set(),
					],
					["latest report URL not live", deploymentSuccess, false, new Set()],
					[
						"duplicate commit hash",
						deploymentSuccess,
						true,
						new Set([deploymentSuccess.deployment.meta.commit_hash]),
					],
				];

			for (const [name, event, latestReportLive, notified] of cases) {
				assert.strictEqual(
					shouldNotifyDiscord(
						event,
						"https://osint-kaname.pages.dev",
						latestReportLive,
						notified,
					),
					false,
					name,
				);
			}

			assert.strictEqual(
				shouldNotifyDiscord(
					deploymentSuccess,
					"https://evil.example.invalid",
					true,
					new Set(),
				),
				false,
				"public base URL mismatch must block notification",
			);
		},
	);

	await t.test(
		"Discord rich embed fixture has required public URL and audit trail",
		() => {
			const payload = buildDiscordPayload(deploymentSuccess);
			assert.strictEqual(payload.username, "Aegis-Intelligence");
			assert.strictEqual(payload.embeds.length, 1);
			assert.strictEqual(
				payload.embeds[0].url,
				"https://osint-kaname.pages.dev",
			);
			assert.strictEqual(payload.embeds[0].color, 3066993);
			assert.ok(
				payload.embeds[0].fields[0].value.includes("2026-05-27_Report"),
			);
			assert.ok(
				payload.embeds[0].fields[1].value.includes("[[能動的サイバー防御]]"),
			);
			assert.ok(payload.embeds[0].fields[2].value.includes("a1b2c3d4e5"));
			assert.strictEqual(
				payload.embeds[0].timestamp,
				"2026-05-27T09:50:00.000Z",
			);
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
