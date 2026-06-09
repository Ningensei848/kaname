import { isAllowedMcpWriterPath } from "../policies/mcp-write-policy";

export type GateStatus = "passed" | "failed" | "unavailable" | "indeterminate";

export type MergePreconditionKey =
	| "ci"
	| "takumiGuard"
	| "deterministicContentGuards"
	| "branchPolicy"
	| "immutableFiles"
	| "internalLinks";

export type MergePreconditions = Record<MergePreconditionKey, GateStatus>;

export type JsonObject = Record<string, unknown>;

export interface McpToolCall {
	jsonrpc: string;
	method: string;
	params: {
		name: string;
		arguments: JsonObject;
	};
	id: number;
}

export const allGreenMergePreconditions: MergePreconditions = {
	ci: "passed",
	takumiGuard: "passed",
	deterministicContentGuards: "passed",
	branchPolicy: "passed",
	immutableFiles: "passed",
	internalLinks: "passed",
};

const allowedToolNames = new Set([
	"create_or_update_file",
	"create_pull_request",
	"merge_pull_request",
	"create_issue",
]);

const toolArgumentKeys: Record<string, readonly string[]> = {
	create_or_update_file: [
		"owner",
		"repo",
		"path",
		"content",
		"branch",
		"message",
	],
	create_pull_request: ["owner", "repo", "title", "head", "base", "body"],
	merge_pull_request: [
		"owner",
		"repo",
		"pull_number",
		"merge_method",
		"commit_title",
	],
	create_issue: ["owner", "repo", "title", "body"],
};

export function validateToolPolicy(
	call: McpToolCall,
	preconditions: MergePreconditions = allGreenMergePreconditions,
): string[] {
	const errors = validateEnvelopeShape(call);
	if (errors.length > 0) return errors;

	const args = call.params.arguments;
	validateToolArguments(call.params.name, args, errors);

	switch (call.params.name) {
		case "create_or_update_file": {
			const branch = getStringArg(args, "branch", errors);
			const filePath = getStringArg(args, "path", errors);
			const message = getStringArg(args, "message", errors);
			getStringArg(args, "content", errors);

			if (branch !== undefined && !branch.startsWith("osint/")) {
				errors.push("Writer branch must be osint/*");
			}
			if (filePath !== undefined && !isAllowedMcpWriterPath(filePath)) {
				errors.push(`Writer path is not allowed: ${filePath}`);
			}
			if (filePath === "crawler-state.json") {
				errors.push("crawler-state.json must not be written through Git MCP");
			}
			if (message !== undefined && !message.startsWith("[Aegis-Writer]")) {
				errors.push("Writer commit message prefix is required");
			}
			break;
		}
		case "create_pull_request": {
			const head = getStringArg(args, "head", errors);
			const base = getStringArg(args, "base", errors);
			const title = getStringArg(args, "title", errors);
			const body = getStringArg(args, "body", errors);

			if (head !== undefined && !head.startsWith("osint/")) {
				errors.push("PR head must be osint/*");
			}
			if (base !== undefined && base !== "main") {
				errors.push("PR base must be main");
			}
			if (title !== undefined && !title.startsWith("[Wiki-Sync]")) {
				errors.push("PR title prefix is required");
			}
			if (body !== undefined && !body.includes("## 提案要約")) {
				errors.push("PR body must include proposal summary heading");
			}
			break;
		}
		case "merge_pull_request": {
			const pullNumber = args.pull_number;
			const mergeMethod = getStringArg(args, "merge_method", errors);
			const commitTitle = getStringArg(args, "commit_title", errors);

			if (!Number.isInteger(pullNumber)) {
				errors.push("merge pull_number must be an integer");
			}
			if (mergeMethod !== undefined && mergeMethod !== "squash") {
				errors.push("merge method must be squash");
			}
			if (
				commitTitle !== undefined &&
				!commitTitle.startsWith("[Aegis-Reviewer]")
			) {
				errors.push("Reviewer merge commit title prefix is required");
			}
			for (const [gateName, status] of Object.entries(preconditions)) {
				if (status !== "passed") {
					errors.push(`merge precondition ${gateName} is ${status}`);
				}
			}
			if (errors.some((error) => error.startsWith("merge precondition "))) {
				errors.push("merge preconditions are not all passed");
			}
			break;
		}
		case "create_issue": {
			const title = getStringArg(args, "title", errors);
			const body = getStringArg(args, "body", errors);
			if (title !== undefined && !title.startsWith("[System Error]")) {
				errors.push("Issue title must signal system error");
			}
			if (body !== undefined && !body.includes("## 障害発生報告")) {
				errors.push("Issue body must use failure report heading");
			}
			if (body !== undefined) {
				for (const requiredField of [
					"- **発生日時**:",
					"- **対象ソース**:",
					"- **エラー内容**:",
					"- **ステータス**:",
				]) {
					if (!body.includes(requiredField)) {
						errors.push(`Issue body missing required field: ${requiredField}`);
					}
				}
			}
			break;
		}
	}
	return errors;
}

function validateEnvelopeShape(call: McpToolCall): string[] {
	const errors: string[] = [];
	if (!isRecord(call)) {
		return ["$: expected type object"];
	}
	for (const requiredKey of ["jsonrpc", "method", "params", "id"]) {
		if (!(requiredKey in call)) {
			errors.push(`$: missing required property ${requiredKey}`);
		}
	}
	for (const key of Object.keys(call)) {
		if (!["jsonrpc", "method", "params", "id"].includes(key)) {
			errors.push(`$.${key}: additional property is not allowed`);
		}
	}
	if (call.jsonrpc !== "2.0") {
		errors.push("$.jsonrpc: expected const 2.0");
	}
	if (call.method !== "tools/call") {
		errors.push("$.method: expected const tools/call");
	}
	if (!Number.isInteger(call.id)) {
		errors.push("$.id: expected type integer");
	}
	if (!isRecord(call.params)) {
		errors.push("$.params: expected type object");
		return errors;
	}
	for (const requiredKey of ["name", "arguments"]) {
		if (!(requiredKey in call.params)) {
			errors.push(`$.params: missing required property ${requiredKey}`);
		}
	}
	for (const key of Object.keys(call.params)) {
		if (!["name", "arguments"].includes(key)) {
			errors.push(`$.params.${key}: additional property is not allowed`);
		}
	}
	if (typeof call.params.name !== "string") {
		errors.push("$.params.name: expected type string");
	} else if (!allowedToolNames.has(call.params.name)) {
		errors.push("$.params.name: expected enum value");
	}
	if (!isRecord(call.params.arguments)) {
		errors.push("$.params.arguments: expected type object");
		return errors;
	}
	for (const requiredKey of ["owner", "repo"]) {
		getStringArg(call.params.arguments, requiredKey, errors);
	}
	return errors;
}

function validateToolArguments(
	toolName: string,
	args: JsonObject,
	errors: string[],
): void {
	const expectedKeys = toolArgumentKeys[toolName];
	if (expectedKeys === undefined) return;
	for (const key of expectedKeys) {
		if (!(key in args)) {
			errors.push(`$.params.arguments: missing required property ${key}`);
		}
	}
	for (const key of Object.keys(args)) {
		if (!expectedKeys.includes(key)) {
			errors.push(
				`$.params.arguments.${key}: additional property is not allowed`,
			);
		}
	}
}

function getStringArg(
	args: JsonObject,
	key: string,
	errors: string[],
): string | undefined {
	const value = args[key];
	if (typeof value !== "string") {
		errors.push(`$.params.arguments.${key}: expected type string`);
		return undefined;
	}
	if (value.length < 1) {
		errors.push(`$.params.arguments.${key}: expected minimum length 1`);
		return undefined;
	}
	return value;
}

function isRecord(value: unknown): value is JsonObject {
	return value !== null && typeof value === "object" && !Array.isArray(value);
}
