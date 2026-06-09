import * as assert from "node:assert";
import * as fs from "node:fs";
import * as path from "node:path";
import { test } from "node:test";

import {
	allGreenMergePreconditions,
	type McpToolCall,
	validateToolPolicy,
} from "../src/mcp/tool-policy";
import { AegisOrchestrator, type DiffResult } from "../src/orchestrator";

function readFixture(...segments: string[]): McpToolCall {
	return JSON.parse(
		fs.readFileSync(
			path.join(__dirname, "fixtures", "f003", ...segments),
			"utf8",
		),
	) as McpToolCall;
}

const changedDiff: DiffResult[] = [
	{ sourceId: "nco", hasChanged: true, content: "updated content" },
];

test("validateToolPolicy rejects broken F002 content guard verdict aggregation", () => {
	const call = readFixture("mcp", "valid", "merge-pull-request.json");

	assert.deepStrictEqual(
		validateToolPolicy(call, {
			...allGreenMergePreconditions,
			f002ContentGuards: "failed",
		}),
		[
			"merge precondition f002ContentGuards is failed",
			"merge preconditions are not all passed",
		],
	);
});

test("validateToolPolicy rejects indeterminate merge gates", () => {
	const call = readFixture("mcp", "valid", "merge-pull-request.json");

	assert.deepStrictEqual(
		validateToolPolicy(call, {
			...allGreenMergePreconditions,
			takumiGuard: "indeterminate",
		}),
		[
			"merge precondition takumiGuard is indeterminate",
			"merge preconditions are not all passed",
		],
	);
});

test("validateToolPolicy rejects disallowed writer and merge branches", () => {
	assert.ok(
		validateToolPolicy(
			readFixture("mcp", "invalid", "writer-main-branch.json"),
		).includes("Writer branch must be osint/*"),
	);

	const mergeCall = readFixture("mcp", "valid", "merge-pull-request.json");
	mergeCall.params.arguments.head = "main";
	assert.ok(
		validateToolPolicy(mergeCall).includes("merge head must be osint/*"),
	);
});

test("validateToolPolicy rejects disallowed writer paths", () => {
	assert.ok(
		validateToolPolicy(
			readFixture("mcp", "invalid", "writer-nested-topic-path.json"),
		).includes(
			"Writer path is not allowed: topics/bad/nested/sub/dir/exploit.md",
		),
	);
});

test("AegisOrchestrator performs successful all-green squash merge through MCP", async () => {
	const calls: McpToolCall[] = [];
	const orchestrator = new AegisOrchestrator(changedDiff, {
		mcpClient: {
			callTool: (call) => {
				calls.push(call);
			},
		},
		reviewProposal: () => ({
			approve: true,
			comment: "all deterministic gates passed",
			mergePreconditions: allGreenMergePreconditions,
		}),
	});

	const result = await orchestrator.run();

	assert.strictEqual(result.exitCode, 0);
	assert.strictEqual(orchestrator.prState?.status, "MERGED");
	assert.strictEqual(calls.length, 1);
	assert.strictEqual(calls[0].params.name, "merge_pull_request");
	assert.strictEqual(calls[0].params.arguments.merge_method, "squash");
	assert.deepStrictEqual(validateToolPolicy(calls[0]), []);
});

test("AegisOrchestrator blocks approved merges when any gate is indeterminate", async () => {
	const calls: McpToolCall[] = [];
	const orchestrator = new AegisOrchestrator(changedDiff, {
		mcpClient: {
			callTool: (call) => {
				calls.push(call);
			},
		},
		reviewProposal: () => ({
			approve: true,
			comment: "reviewer approval is not enough without deterministic gates",
			mergePreconditions: {
				...allGreenMergePreconditions,
				node: "indeterminate",
			},
		}),
	});

	const result = await orchestrator.run();

	assert.strictEqual(result.exitCode, 1);
	assert.strictEqual(orchestrator.state, "FAILED");
	assert.deepStrictEqual(calls, []);
	assert.match(result.reason, /Agreement failed|Orchestration failed/);
});
