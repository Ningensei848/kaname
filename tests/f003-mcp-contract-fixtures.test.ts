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
import type { McpToolCall, MergePreconditions } from "../src/mcp/tool-policy";
import {
	allGreenMergePreconditions,
	validateToolPolicyFixtureOracle,
} from "./helpers/mcp-policy-oracle";

const allGreenGates: MergePreconditions = allGreenMergePreconditions;

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

test("F003 external MCP JSON fixtures are executable", async (t) => {
	await t.test(
		"all valid fixtures satisfy the JSON-RPC envelope and tool policy",
		() => {
			for (const fixtureName of listJsonFixtures("mcp", "valid")) {
				const call = readFixture("mcp", "valid", fixtureName);
				assert.deepStrictEqual(
					validateToolPolicyFixtureOracle(call),
					[],
					fixtureName,
				);
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
					validateToolPolicyFixtureOracle(call, gates).includes(expectedError),
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
				const errors = validateToolPolicyFixtureOracle(mergeCall, {
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

test("F003 deterministic fixture oracle validates every external fixture before tool calls", () => {
	for (const fixtureName of listJsonFixtures("mcp", "valid")) {
		const call = readFixture("mcp", "valid", fixtureName);
		assert.deepStrictEqual(
			validateToolPolicyFixtureOracle(call, allGreenMergePreconditions),
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
	};

	assert.ok(
		validateToolPolicyFixtureOracle(generatedIndexCall).includes(
			"Writer path is not allowed: topics/index.md",
		),
		"generated index paths stay rejected until an exact feature-plan path is added",
	);
});
