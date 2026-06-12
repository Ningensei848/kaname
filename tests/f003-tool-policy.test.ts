import * as assert from "node:assert";
import * as fs from "node:fs";
import * as path from "node:path";
import { test } from "node:test";

import type {
	MergePreconditions,
	PolicyMcpToolCall,
} from "../src/mcp/tool-policy";
import type { DiffResult } from "../src/orchestrator";

const allGreenMergePreconditions: MergePreconditions = {
	ci: "passed",
	takumiGuard: "passed",
	deterministicContentGuards: "passed",
	branchPolicy: "passed",
	immutableFiles: "passed",
	internalLinks: "passed",
};

const mergePreconditionKeys = [
	"ci",
	"takumiGuard",
	"deterministicContentGuards",
	"branchPolicy",
	"immutableFiles",
	"internalLinks",
] as const;

type ToolName = PolicyMcpToolCall["params"]["name"];
type JsonObject = Record<string, unknown>;
type ArgumentTypeName = "integer" | "string";

interface ToolArgumentShape {
	required: readonly string[];
	properties: Readonly<Record<string, ArgumentTypeName>>;
}

const toolArgumentShapes: Record<ToolName, ToolArgumentShape> = {
	create_or_update_file: {
		required: ["owner", "repo", "path", "content", "branch", "message"],
		properties: {
			owner: "string",
			repo: "string",
			path: "string",
			content: "string",
			branch: "string",
			message: "string",
		},
	},
	create_pull_request: {
		required: ["owner", "repo", "title", "head", "base", "body"],
		properties: {
			owner: "string",
			repo: "string",
			title: "string",
			head: "string",
			base: "string",
			body: "string",
		},
	},
	merge_pull_request: {
		required: ["owner", "repo", "pull_number", "merge_method", "commit_title"],
		properties: {
			owner: "string",
			repo: "string",
			pull_number: "integer",
			merge_method: "string",
			commit_title: "string",
		},
	},
	create_issue: {
		required: ["owner", "repo", "title", "body"],
		properties: {
			owner: "string",
			repo: "string",
			title: "string",
			body: "string",
		},
	},
};

function validateToolPolicy(
	call: PolicyMcpToolCall,
	preconditions: MergePreconditions = allGreenMergePreconditions,
): string[] {
	const errors = validateEnvelopeShape(call);
	if (errors.length > 0) return errors;

	const args = call.params.arguments;
	errors.push(...validateArgumentTypes(call));
	errors.push(...validateToolArgumentsShape(call.params.name, args));
	switch (call.params.name) {
		case "create_or_update_file": {
			if (!String(args.branch).startsWith("osint/")) {
				errors.push("Writer branch must be osint/*");
			}
			if (!isAllowedMcpWriterPath(String(args.path))) {
				errors.push(`Writer path is not allowed: ${String(args.path)}`);
			}
			if (String(args.path) === "crawler-state.json") {
				errors.push("crawler-state.json must not be written through Git MCP");
			}
			if (!String(args.message).startsWith("[Aegis-Writer]")) {
				errors.push("Writer commit message prefix is required");
			}
			break;
		}
		case "create_pull_request": {
			if (!String(args.head).startsWith("osint/")) {
				errors.push("PR head must be osint/*");
			}
			if (args.base !== "main") errors.push("PR base must be main");
			if (!String(args.title).startsWith("[Wiki-Sync]")) {
				errors.push("PR title prefix is required");
			}
			break;
		}
		case "merge_pull_request": {
			for (const disallowedProperty of ["head", "base"] as const) {
				if (disallowedProperty in args) {
					errors.push(
						`$.params.arguments.${disallowedProperty}: additional property is not allowed`,
					);
				}
			}
			if (args.merge_method !== "squash") {
				errors.push("merge method must be squash");
			}
			if (!String(args.commit_title).startsWith("[Aegis-Reviewer]")) {
				errors.push("Reviewer merge commit title prefix is required");
			}
			const mergePreconditionErrors = validateMergePreconditions(preconditions);
			errors.push(...mergePreconditionErrors);
			if (mergePreconditionErrors.length > 0) {
				errors.push("merge preconditions are not all passed");
			}
			break;
		}
		case "create_issue": {
			if (!String(args.title).startsWith("[System Error]")) {
				errors.push("Issue title must signal system error");
			}
			const body = String(args.body);
			if (
				!body.includes("## 障害発生報告") &&
				!body.includes("## crawler-state.json 世代競合")
			) {
				errors.push("Issue body must use failure report heading");
			}
			for (const requiredField of [
				"- **発生日時**:",
				"- **ステータス**:",
			] as const) {
				if (!body.includes(requiredField)) {
					errors.push(`Issue body missing required field: ${requiredField}`);
				}
			}
			break;
		}
	}
	return errors;
}

function validateMergePreconditions(
	preconditions: MergePreconditions,
): string[] {
	const errors: string[] = [];
	for (const key of mergePreconditionKeys) {
		const status = preconditions[key];
		if (status !== "passed") {
			errors.push(`merge precondition ${key} is ${status}`);
		}
	}
	return errors;
}

function validateToolArgumentsShape(
	name: ToolName,
	args: JsonObject,
): string[] {
	const errors: string[] = [];
	const shape = toolArgumentShapes[name];
	for (const requiredProperty of shape.required) {
		if (!(requiredProperty in args)) {
			errors.push(
				`$.params.arguments.${requiredProperty}: required property is missing`,
			);
		}
	}
	for (const [key, value] of Object.entries(args)) {
		const expectedType = shape.properties[key];
		if (!expectedType) {
			errors.push(
				`$.params.arguments.${key}: additional property is not allowed`,
			);
			continue;
		}
		if (!matchesArgumentType(expectedType, value)) {
			errors.push(`$.params.arguments.${key}: expected type ${expectedType}`);
		}
	}
	return errors;
}

function matchesArgumentType(
	expectedType: ArgumentTypeName,
	value: unknown,
): boolean {
	return expectedType === "integer"
		? Number.isInteger(value)
		: typeof value === "string";
}

function validateEnvelopeShape(call: PolicyMcpToolCall): string[] {
	const errors: string[] = [];
	if (call.jsonrpc !== "2.0") errors.push("$.jsonrpc: expected const 2.0");
	if (call.method !== "tools/call") {
		errors.push("$.method: expected const tools/call");
	}
	if (!Number.isInteger(call.id)) errors.push("$.id: expected integer");
	if (!call.params || typeof call.params !== "object") {
		errors.push("$.params: expected object");
		return errors;
	}
	if (typeof call.params.name !== "string") {
		errors.push("$.params.name: expected string");
	}
	if (
		!call.params.arguments ||
		typeof call.params.arguments !== "object" ||
		Array.isArray(call.params.arguments)
	) {
		errors.push("$.params.arguments: expected object");
	}
	return errors;
}

function validateArgumentTypes(call: PolicyMcpToolCall): string[] {
	const errors: string[] = [];
	const args = call.params.arguments;
	switch (call.params.name) {
		case "create_or_update_file":
			expectString(errors, args, "branch");
			expectString(errors, args, "path");
			expectString(errors, args, "message");
			break;
		case "create_pull_request":
			expectString(errors, args, "head");
			expectString(errors, args, "base");
			expectString(errors, args, "title");
			break;
		case "merge_pull_request":
			expectInteger(errors, args, "pull_number");
			expectString(errors, args, "merge_method");
			expectString(errors, args, "commit_title");
			break;
		case "create_issue":
			expectString(errors, args, "title");
			expectString(errors, args, "body");
			break;
	}
	return errors;
}

function expectString(
	errors: string[],
	args: JsonObject,
	property: string,
): void {
	if (typeof args[property] !== "string") {
		errors.push(`$.params.arguments.${property}: expected type string`);
	}
}

function expectInteger(
	errors: string[],
	args: JsonObject,
	property: string,
): void {
	if (!Number.isInteger(args[property])) {
		errors.push(`$.params.arguments.${property}: expected type integer`);
	}
}

function isAllowedMcpWriterPath(filePath: string): boolean {
	if (
		filePath
			.split("/")
			.some((segment) => segment === "." || segment === "..") ||
		[...filePath].some((char) => {
			const codePoint = char.codePointAt(0);
			return codePoint !== undefined && (codePoint < 32 || codePoint === 127);
		})
	) {
		return false;
	}
	return (
		/^topics\/[^/]+\/[^/]+\.md$/.test(filePath) ||
		/^reports\/\d{4}-\d{2}-\d{2}_Report\.md$/.test(filePath)
	);
}

class AegisOrchestratorContract {
	public prState: { status: "OPEN" | "MERGED"; prNumber: number } | null = null;
	public state: "INIT" | "FAILED" | "MERGED" = "INIT";

	constructor(
		private readonly diffData: DiffResult[],
		private readonly dependencies: {
			mcpClient: { callTool: (call: PolicyMcpToolCall) => void };
			reviewProposal: () => {
				approve: boolean;
				comment: string;
				mergePreconditions: MergePreconditions;
			};
		},
	) {}

	async run(): Promise<{ exitCode: number; reason: string }> {
		if (!this.diffData.some((diff) => diff.hasChanged)) {
			return { exitCode: 0, reason: "No changes detected. Idempotent skip." };
		}
		this.prState = { status: "OPEN", prNumber: 42 };
		const review = this.dependencies.reviewProposal();
		const call = buildMergePullRequestCall(this.prState.prNumber);
		const policyErrors = review.approve
			? validateToolPolicy(call, review.mergePreconditions)
			: [];
		if (review.approve && policyErrors.length === 0) {
			this.dependencies.mcpClient.callTool(call);
			this.prState.status = "MERGED";
			this.state = "MERGED";
			return {
				exitCode: 0,
				reason: "Consensus reached and merged successfully.",
			};
		}
		this.state = "FAILED";
		return { exitCode: 1, reason: "Agreement failed. Escalated via Issue." };
	}
}

function buildMergePullRequestCall(pullNumber: number): PolicyMcpToolCall {
	return {
		jsonrpc: "2.0",
		method: "tools/call",
		params: {
			name: "merge_pull_request",
			arguments: {
				owner: "Ningensei848",
				repo: "kaname-vault",
				pull_number: pullNumber,
				merge_method: "squash",
				commit_title:
					"[Aegis-Reviewer] Self-Merge: Intelligence Update Passed Review",
			},
		},
		id: 103,
	};
}

function readFixture(...segments: string[]): PolicyMcpToolCall {
	return JSON.parse(
		fs.readFileSync(
			path.join(__dirname, "fixtures", "f003", ...segments),
			"utf8",
		),
	) as PolicyMcpToolCall;
}

const changedDiff: DiffResult[] = [
	{ sourceId: "nco", hasChanged: true, content: "updated content" },
];

test("validateToolPolicy rejects broken F002 content guard verdict aggregation", () => {
	const call = readFixture("mcp", "valid", "merge-pull-request.json");

	assert.deepStrictEqual(
		validateToolPolicy(call, {
			...allGreenMergePreconditions,
			deterministicContentGuards: "failed",
		}),
		[
			"merge precondition deterministicContentGuards is failed",
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

test("validateToolPolicy rejects disallowed writer branches and spec-external merge properties", () => {
	assert.ok(
		validateToolPolicy(
			readFixture("mcp", "invalid", "writer-main-branch.json"),
		).includes("Writer branch must be osint/*"),
	);

	const mergeCall = readFixture("mcp", "valid", "merge-pull-request.json");
	mergeCall.params.arguments.head = "main";
	assert.ok(
		validateToolPolicy(mergeCall).includes(
			"$.params.arguments.head: additional property is not allowed",
		),
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

test("validateToolPolicy fails closed for invalid argument types and merge extras", () => {
	const writerCall = readFixture("mcp", "valid", "create-or-update-file.json");
	writerCall.params.arguments.branch = ["osint/content-update"];
	assert.ok(
		validateToolPolicy(writerCall).includes(
			"$.params.arguments.branch: expected type string",
		),
	);

	const mergeCall = readFixture("mcp", "valid", "merge-pull-request.json");
	mergeCall.params.arguments.base = "main";
	assert.ok(
		validateToolPolicy(mergeCall).includes(
			"$.params.arguments.base: additional property is not allowed",
		),
	);
});

test("AegisOrchestrator performs successful all-green squash merge through MCP", async () => {
	const calls: PolicyMcpToolCall[] = [];
	const orchestrator = new AegisOrchestratorContract(changedDiff, {
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
	const calls: PolicyMcpToolCall[] = [];
	const orchestrator = new AegisOrchestratorContract(changedDiff, {
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
				ci: "indeterminate",
			},
		}),
	});

	const result = await orchestrator.run();

	assert.strictEqual(result.exitCode, 1);
	assert.strictEqual(orchestrator.state, "FAILED");
	assert.deepStrictEqual(calls, []);
	assert.match(result.reason, /Agreement failed|Orchestration failed/);
});
