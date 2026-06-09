import { isAllowedMcpWriterPath } from "../policies/mcp-write-policy";

export type JsonObject = Record<string, unknown>;

export type GateStatus = "passed" | "failed" | "unavailable" | "indeterminate";

export interface MergePreconditions {
	ci: GateStatus;
	takumiGuard: GateStatus;
	deterministicContentGuards: GateStatus;
	branchPolicy: GateStatus;
	immutableFiles: GateStatus;
	internalLinks: GateStatus;
}

export interface PolicyMcpToolCall {
	jsonrpc: "2.0";
	method: "tools/call";
	params: {
		name:
			| "create_issue"
			| "create_or_update_file"
			| "create_pull_request"
			| "merge_pull_request";
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

export function validateToolPolicy(
	call: PolicyMcpToolCall,
	preconditions: MergePreconditions = allGreenMergePreconditions,
): string[] {
	const errors = validateEnvelopeShape(call);
	if (errors.length > 0) {
		return errors;
	}

	const args = call.params.arguments;
	errors.push(...validateToolArgumentsShape(call.params.name, args));
	recordFailedMergePreconditions(call.params.name, preconditions, errors);

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
			if (args.merge_method !== "squash") {
				errors.push("merge method must be squash");
			}
			if (!String(args.commit_title).startsWith("[Aegis-Reviewer]")) {
				errors.push("Reviewer merge commit title prefix is required");
			}
			if (!canMerge(preconditions)) {
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

export function canMerge(gates: MergePreconditions): boolean {
	return Object.values(gates).every((status) => status === "passed");
}

type ToolName = PolicyMcpToolCall["params"]["name"];
type ArgumentTypeName = "integer" | "string";
interface ToolArgumentShape {
	required: string[];
	properties: Record<string, ArgumentTypeName>;
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
	if (expectedType === "integer") {
		return Number.isInteger(value);
	}
	return typeof value === "string";
}

function recordFailedMergePreconditions(
	toolName: PolicyMcpToolCall["params"]["name"],
	preconditions: MergePreconditions,
	errors: string[],
): void {
	if (toolName !== "merge_pull_request") {
		return;
	}
	for (const [gateName, status] of Object.entries(preconditions)) {
		if (status !== "passed") {
			errors.push(`merge precondition ${gateName} is ${status}`);
		}
	}
}

function validateEnvelopeShape(call: PolicyMcpToolCall): string[] {
	const errors: string[] = [];
	if (call.jsonrpc !== "2.0") {
		errors.push("$.jsonrpc: expected const 2.0");
	}
	if (call.method !== "tools/call") {
		errors.push("$.method: expected const tools/call");
	}
	if (!Number.isInteger(call.id)) {
		errors.push("$.id: expected integer");
	}
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
