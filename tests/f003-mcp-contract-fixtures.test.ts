/**
 * F003 executable MCP contract fixtures.
 *
 * This test turns `.spec/contracts/mcp-contracts.md` into external JSON
 * fixtures that can be replayed without real GitHub access. The production
 * implementation should eventually validate every MCP call against equivalent
 * contracts before it is sent to the GitHub MCP server.
 */

import * as assert from "node:assert";
import * as fs from "node:fs";
import * as path from "node:path";
import { test } from "node:test";
import type { PolicyMcpToolCall } from "../src/mcp/tool-policy";

import {
	validateJsonSchema,
	type JsonObject,
	type JsonSchema,
} from "./helpers/schema-validator";
type GateStatus = "passed" | "failed" | "unavailable" | "indeterminate";

type MergePreconditions = Record<
	| "ci"
	| "takumiGuard"
	| "deterministicContentGuards"
	| "branchPolicy"
	| "immutableFiles"
	| "internalLinks",
	GateStatus
>;

const allGreenGates: MergePreconditions = {
	ci: "passed",
	takumiGuard: "passed",
	deterministicContentGuards: "passed",
	branchPolicy: "passed",
	immutableFiles: "passed",
	internalLinks: "passed",
};

const allGreenMergePreconditions = allGreenGates;

interface McpToolCall {
	jsonrpc: string;
	method: string;
	params: { name: string; arguments: JsonObject };
	id: number;
}

function fixturePath(...segments: string[]): string {
	return path.join(__dirname, "fixtures", "f003", ...segments);
}

function readJson(filePath: string): unknown {
	return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function readFixture(...segments: string[]): McpToolCall {
	return readJson(fixturePath(...segments)) as McpToolCall;
}

function listJsonFixtures(...segments: string[]): string[] {
	return fs
		.readdirSync(fixturePath(...segments))
		.filter((fileName) => fileName.endsWith(".json"))
		.sort();
}

function validateEnvelopeShape(call: McpToolCall) {
	const schema = readJson(
		".spec/schemas/mcp-tool-call.schema.json",
	) as JsonSchema;
	return validateJsonSchema(schema, call);
}

function canMerge(gates: MergePreconditions): boolean {
	return Object.values(gates).every((status) => status === "passed");
}

function validateToolPolicy(
	call: McpToolCall,
	preconditions: MergePreconditions = allGreenGates,
): string[] {
	const errors = validateEnvelopeShape(call).map(
		(error) => `${error.path}: ${error.message}`,
	);
	if (errors.length > 0) return errors;

	const args = call.params.arguments;
	switch (call.params.name) {
		case "create_or_update_file":
			if (!String(args.branch).startsWith("osint/"))
				errors.push("Writer branch must be osint/*");
			if (!isAllowedWriterPath(String(args.path)))
				errors.push(`Writer path is not allowed: ${String(args.path)}`);
			if (String(args.path) === "crawler-state.json")
				errors.push("crawler-state.json must not be written through Git MCP");
			if (!String(args.message).startsWith("[Aegis-Writer]"))
				errors.push("Writer commit message prefix is required");
			break;
		case "create_pull_request":
			if (!String(args.head).startsWith("osint/"))
				errors.push("PR head must be osint/*");
			if (args.base !== "main") errors.push("PR base must be main");
			if (!String(args.title).startsWith("[Wiki-Sync]"))
				errors.push("PR title prefix is required");
			break;
		case "merge_pull_request":
			if (args.merge_method !== "squash")
				errors.push("merge method must be squash");
			if (!String(args.commit_title).startsWith("[Aegis-Reviewer]"))
				errors.push("Reviewer merge commit title prefix is required");
			if (!canMerge(preconditions))
				errors.push("merge preconditions are not all passed");
			break;
		case "create_issue": {
			if (!String(args.title).startsWith("[System Error]"))
				errors.push("Issue title must signal system error");
			const body = String(args.body);
			if (!body.includes("## 障害発生報告"))
				errors.push("Issue body must use failure report heading");
			for (const requiredField of [
				"- **発生日時**:",
				"- **対象ソース**:",
				"- **エラー内容**:",
				"- **ステータス**:",
			]) {
				if (!body.includes(requiredField))
					errors.push(`Issue body missing required field: ${requiredField}`);
			}
			break;
		}
	}
	return errors;
}

function isAllowedWriterPath(filePath: string): boolean {
	return (
		/^(reports\/|topics\/(?:[^/]+\/)?[^/]+\.md$|\.spec\/)/.test(filePath) &&
		!filePath.includes("..") &&
		filePath !== "crawler-state.json" &&
		filePath !== "topics/index.md"
	);
}

test("F003 external MCP JSON fixtures are executable", async (t) => {
	await t.test(
		"all valid fixtures satisfy the JSON-RPC envelope and tool policy",
		() => {
			for (const fixtureName of listJsonFixtures("mcp", "valid")) {
				const call = readFixture("mcp", "valid", fixtureName);
				assert.deepStrictEqual(validateToolPolicy(call), [], fixtureName);
			}
		},
	);

	await t.test(
		"invalid fixtures are rejected for branch, path, or merge gate violations",
		() => {
			const invalidCases = new Map([
				["writer-main-branch.json", "Writer branch must be osint/*"],
				[
					"writer-outside-path.json",
					"Writer path is not allowed: src/orchestrator.ts",
				],
				[
					"writer-runtime-state-git-write.json",
					"crawler-state.json must not be written through Git MCP",
				],
				[
					"writer-nested-topic-path.json",
					"Writer path is not allowed: topics/bad/nested/sub/dir/exploit.md",
				],
				[
					"writer-generated-index-path.json",
					"Writer path is not allowed: topics/index.md",
				],
				[
					"merge-bad-commit-title.json",
					"Reviewer merge commit title prefix is required",
				],
				// This fixture is structurally valid JSON-RPC, but is intentionally
				// rejected because the active merge-gate context below is red.
				["merge-failed-gates.json", "merge preconditions are not all passed"],
			]);

			for (const [fixtureName, expectedError] of invalidCases) {
				const call = readFixture("mcp", "invalid", fixtureName);
				const gates =
					fixtureName === "merge-failed-gates.json"
						? {
								...allGreenGates,
								deterministicContentGuards: "failed" as const,
							}
						: allGreenGates;
				assert.ok(
					validateToolPolicy(call, gates).includes(expectedError),
					fixtureName,
				);
			}
		},
	);

	await t.test("every merge gate fails closed for merge_pull_request", () => {
		const mergeCall = readFixture("mcp", "valid", "merge-pull-request.json");
		for (const gateName of Object.keys(allGreenGates) as Array<
			keyof MergePreconditions
		>) {
			for (const badStatus of [
				"failed",
				"unavailable",
				"indeterminate",
			] as const) {
				const errors = validateToolPolicy(mergeCall, {
					...allGreenGates,
					[gateName]: badStatus,
				});
				assert.ok(
					errors.includes("merge preconditions are not all passed"),
					`${gateName}=${badStatus}`,
				);
			}
		}
	});
});

test("F003 production MCP policy validates every external fixture before tool calls", () => {
	for (const fixtureName of listJsonFixtures("mcp", "valid")) {
		const call = readFixture("mcp", "valid", fixtureName) as PolicyMcpToolCall;
		assert.deepStrictEqual(
			validateToolPolicy(call, allGreenMergePreconditions),
			[],
			fixtureName,
		);
	}

	const generatedIndexCall = {
		...readFixture("mcp", "valid", "create-or-update-file.json"),
		params: {
			...readFixture("mcp", "valid", "create-or-update-file.json").params,
			arguments: {
				...readFixture("mcp", "valid", "create-or-update-file.json").params
					.arguments,
				path: "topics/index.md",
			},
		},
	} as PolicyMcpToolCall;

	assert.ok(
		validateToolPolicy(generatedIndexCall).includes(
			"Writer path is not allowed: topics/index.md",
		),
		"generated index paths stay rejected until an exact feature-plan path is added",
	);
});
