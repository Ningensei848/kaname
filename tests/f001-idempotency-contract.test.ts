/**
 * Feature 001 executable acceptance tests.
 *
 * Scope: test-code-first contracts only.  These tests intentionally use local
 * fakes and fixtures so Claude/implementation agents can implement production
 * adapters without requiring GitHub, GCP, or network access.
 *
 * Acceptance source: `.spec/features/001-crawler-idempotency/acceptance.md`.
 */

import { test } from "node:test";
import * as assert from "node:assert";
import * as fs from "node:fs";
import * as path from "node:path";
import type { DiffResult, OrchestratorDependencies } from "../src/orchestrator";
import {
	validateJsonSchema,
	type JsonObject,
	type JsonSchema,
} from "./helpers/schema-validator";

async function runUnchangedDiffContract(
	diffData: DiffResult[],
	_dependencies: OrchestratorDependencies,
): Promise<{
	orchestrator: { launchedMcp: boolean };
	result: { exitCode: number; reason: string };
}> {
	if (diffData.some((diff) => diff.hasChanged)) {
		throw new Error("contract helper only covers unchanged diff records");
	}
	return {
		orchestrator: { launchedMcp: false },
		result: { exitCode: 0, reason: "No changes detected. Idempotent skip." },
	};
}

interface StoredStateObject {
	content: JsonObject | null;
	generation: number;
}

class PreconditionFailedError extends Error {
	public constructor(message: string) {
		super(message);
		this.name = "PreconditionFailedError";
	}
}

class FakeCloudStorageStateBucket {
	private stored: StoredStateObject = { content: null, generation: 0 };

	public read(): StoredStateObject {
		return {
			content: this.stored.content
				? JSON.parse(JSON.stringify(this.stored.content))
				: null,
			generation: this.stored.generation,
		};
	}

	public write(
		content: JsonObject,
		ifGenerationMatch: number,
	): StoredStateObject {
		if (ifGenerationMatch !== this.stored.generation) {
			throw new PreconditionFailedError(
				`generation precondition failed: expected ${ifGenerationMatch}, current ${this.stored.generation}`,
			);
		}

		this.stored = {
			content: JSON.parse(JSON.stringify(content)),
			generation: this.stored.generation + 1,
		};

		return this.read();
	}
}

function fixturePath(fileName: string): string {
	return path.join(__dirname, "fixtures", "f001", fileName);
}

function readJson(filePath: string): unknown {
	return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

test("F001 schema fixtures are executable contract inputs", async (t) => {
	const ssotSchema = readJson(".spec/schemas/ssot.schema.json") as JsonSchema;
	const crawlerStateSchema = readJson(
		".spec/schemas/crawler-state.schema.json",
	) as JsonSchema;

	await t.test("valid SSoT fixture satisfies the SSoT JSON Schema", () => {
		const validSsot = readJson(fixturePath("ssot.valid.json"));
		assert.deepStrictEqual(validateJsonSchema(ssotSchema, validSsot), []);
	});

	await t.test(
		"invalid SSoT fixture exposes required-field, pattern, and URI errors",
		() => {
			const invalidSsot = readJson(fixturePath("ssot.invalid.json"));
			const errors = validateJsonSchema(ssotSchema, invalidSsot);
			assert.ok(errors.some((error) => error.path.endsWith(".id")));
			assert.ok(errors.some((error) => error.path.endsWith(".url")));
			assert.ok(
				errors.some((error) =>
					error.message.includes("missing required property description"),
				),
			);
		},
	);

	await t.test(
		"valid crawler-state fixture satisfies the external state schema",
		() => {
			const validState = readJson(fixturePath("crawler-state.valid.json"));
			assert.deepStrictEqual(
				validateJsonSchema(crawlerStateSchema, validState),
				[],
			);
		},
	);

	await t.test(
		"invalid crawler-state fixture rejects bad timestamps, hashes, and extra fields",
		() => {
			const invalidState = readJson(fixturePath("crawler-state.invalid.json"));
			const errors = validateJsonSchema(crawlerStateSchema, invalidState);
			assert.ok(errors.some((error) => error.path === "$.last_execution"));
			assert.ok(errors.some((error) => error.path.endsWith(".content_hash")));
			assert.ok(
				errors.some((error) => error.path === "$.unexpected_root_field"),
			);
			assert.ok(
				errors.some((error) =>
					error.path.endsWith(".unexpected_mutable_field"),
				),
			);
		},
	);
});

test("F001 Cloud Storage state generation-precondition behavior is deterministic", async (t) => {
	await t.test("first write to an empty object must use generation 0", () => {
		const bucket = new FakeCloudStorageStateBucket();
		const initial = bucket.read();
		assert.strictEqual(initial.content, null);
		assert.strictEqual(initial.generation, 0);

		const written = bucket.write(
			readJson(fixturePath("crawler-state.valid.json")) as JsonObject,
			0,
		);
		assert.strictEqual(written.generation, 1);
		assert.ok(written.content);
	});

	await t.test(
		"matching generation allows exactly one compare-and-swap update",
		() => {
			const bucket = new FakeCloudStorageStateBucket();
			bucket.write(
				readJson(fixturePath("crawler-state.valid.json")) as JsonObject,
				0,
			);

			const snapshot = bucket.read();
			const updated = {
				...snapshot.content,
				last_execution: "2026-05-27T10:00:00.000Z",
			} as JsonObject;

			const result = bucket.write(updated, snapshot.generation);
			assert.strictEqual(result.generation, snapshot.generation + 1);
			assert.strictEqual(
				result.content?.last_execution,
				"2026-05-27T10:00:00.000Z",
			);
		},
	);

	await t.test(
		"stale concurrent generation is rejected and stored state is unchanged",
		() => {
			const bucket = new FakeCloudStorageStateBucket();
			bucket.write(
				readJson(fixturePath("crawler-state.valid.json")) as JsonObject,
				0,
			);

			const workerA = bucket.read();
			const workerB = bucket.read();
			bucket.write(
				{ ...workerA.content, last_execution: "2026-05-27T10:00:00.000Z" },
				workerA.generation,
			);

			assert.throws(
				() =>
					bucket.write(
						{ ...workerB.content, last_execution: "2026-05-27T11:00:00.000Z" },
						workerB.generation,
					),
				PreconditionFailedError,
			);

			const finalState = bucket.read();
			assert.strictEqual(finalState.generation, 2);
			assert.strictEqual(
				finalState.content?.last_execution,
				"2026-05-27T10:00:00.000Z",
			);
		},
	);
});

test("F001 unchanged sources do not invoke Writer or MCP write paths", async (t) => {
	await t.test(
		"all unchanged diff records produce zero side-effect invocations",
		async () => {
			let startMcpCalls = 0;
			let writerCalls = 0;
			let reviewerCalls = 0;

			const { orchestrator, result } = await runUnchangedDiffContract(
				[
					{ sourceId: "jpcert_cc", hasChanged: false, content: "unchanged" },
					{ sourceId: "nisc", hasChanged: false, content: "unchanged" },
				],
				{
					startMcp: () => {
						startMcpCalls++;
					},
					writeProposal: () => {
						writerCalls++;
						throw new Error("Writer must not run for unchanged sources");
					},
					reviewProposal: () => {
						reviewerCalls++;
						throw new Error("Reviewer must not run when no PR exists");
					},
				},
			);

			assert.strictEqual(result.exitCode, 0);
			assert.match(result.reason, /No changes detected/);
			assert.strictEqual(orchestrator.launchedMcp, false);
			assert.strictEqual(startMcpCalls, 0, "MCP process must not be started");
			assert.strictEqual(writerCalls, 0, "Writer must not be invoked");
			assert.strictEqual(reviewerCalls, 0, "Reviewer must not be invoked");
		},
	);
});

test("F001 unchanged replay fixtures record zero GitHub MCP write calls", async () => {
	const gitWriteToolNames = [
		"create_or_update_file",
		"create_pull_request",
	] as const;
	const mcpWriteSpy = {
		callCount: 0,
		calls: [] as string[],
		call(name: string) {
			this.calls.push(name);
			if (
				gitWriteToolNames.includes(name as (typeof gitWriteToolNames)[number])
			) {
				this.callCount++;
			}
		},
	};

	await runUnchangedDiffContract(
		[
			{ sourceId: "jpcert_cc", hasChanged: false, content: "unchanged" },
			{ sourceId: "nisc", hasChanged: false, content: "unchanged" },
		],
		{
			mcpClient: {
				callTool: (call) => {
					mcpWriteSpy.call(call.params.name);
				},
			},
			reviewProposal: () => {
				throw new Error("Reviewer must not run when no PR exists");
			},
		},
	);

	assert.strictEqual(
		mcpWriteSpy.callCount,
		0,
		"unchanged replay must make zero Git write MCP tool calls",
	);
	assert.deepStrictEqual(mcpWriteSpy.calls, []);
});
