import { isAllowedMcpWriterPath } from "../policies/mcp-write-policy";

export type GateStatus = "passed" | "failed" | "unavailable" | "indeterminate";

export type MergePreconditionKey =
	| "installFrozenLockfile"
	| "typecheck"
	| "lintFormat"
	| "node"
	| "takumiGuard"
	| "f002ContentGuards";

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
	installFrozenLockfile: "passed",
	typecheck: "passed",
	lintFormat: "passed",
	node: "passed",
	takumiGuard: "passed",
	f002ContentGuards: "passed",
};

const allowedToolNames = new Set([
	"create_or_update_file",
	"create_pull_request",
	"merge_pull_request",
	"create_issue",
]);

export function validateToolPolicy(
	call: McpToolCall,
	preconditions: MergePreconditions = allGreenMergePreconditions,
): string[] {
	const errors = validateEnvelopeShape(call);
	if (errors.length > 0) return errors;

	const args = call.params.arguments;
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
			if (args.base !== "main") {
				errors.push("PR base must be main");
			}
			if (!String(args.title).startsWith("[Wiki-Sync]")) {
				errors.push("PR title prefix is required");
			}
			break;
		}
		case "merge_pull_request": {
			if (!String(args.head).startsWith("osint/")) {
				errors.push("merge head must be osint/*");
			}
			if (args.base !== "main") {
				errors.push("merge base must be main");
			}
			if (args.merge_method !== "squash") {
				errors.push("merge method must be squash");
			}
			if (!String(args.commit_title).startsWith("[Aegis-Reviewer]")) {
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
			if (!String(args.title).startsWith("[System Error]")) {
				errors.push("Issue title must signal system error");
			}
			const body = String(args.body);
			if (!body.includes("## 障害発生報告")) {
				errors.push("Issue body must use failure report heading");
			}
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
		if (!(requiredKey in call.params.arguments)) {
			errors.push(
				`$.params.arguments: missing required property ${requiredKey}`,
			);
		} else if (typeof call.params.arguments[requiredKey] !== "string") {
			errors.push(`$.params.arguments.${requiredKey}: expected type string`);
		} else if (String(call.params.arguments[requiredKey]).length < 1) {
			errors.push(
				`$.params.arguments.${requiredKey}: expected minimum length 1`,
			);
		}
	}
	return errors;
}

function isRecord(value: unknown): value is JsonObject {
	return value !== null && typeof value === "object" && !Array.isArray(value);
}
