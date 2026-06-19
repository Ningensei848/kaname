import type {
	McpToolCall,
	MergePreconditions,
} from "../../src/mcp/tool-policy";

export const allGreenMergePreconditions: MergePreconditions = {
	ci: "passed",
	takumiGuard: "passed",
	deterministicContentGuards: "passed",
	branchPolicy: "passed",
	immutableFiles: "passed",
	internalLinks: "passed",
};

const WRITER_BRANCH_PREFIX = "osint/";
const WRITER_COMMIT_PREFIX = "[Aegis-Writer]";
const PR_TITLE_PREFIX = "[Wiki-Sync]";
const REVIEWER_COMMIT_TITLE_PREFIX = "[Aegis-Reviewer]";
const SYSTEM_ERROR_TITLE_PREFIX = "[System Error]";
const SPEC_WRITER_PATH_PATTERN =
	/^\.spec\/(?:contracts|schemas)\/[^/]+(?:\/[^/]+)*\.[A-Za-z0-9_-]+$/;
const TOPIC_SLUG_SEGMENT_PATTERN = /^[^/]+$/;

function asString(value: unknown): string {
	return typeof value === "string" ? value : String(value);
}

function hasPassedMergePreconditions(
	preconditions: MergePreconditions,
): boolean {
	return Object.values(preconditions).every((status) => status === "passed");
}

function isAllowedTopicPath(filePath: string): boolean {
	if (!filePath.startsWith("topics/") || !filePath.endsWith(".md"))
		return false;
	if (filePath === "topics/index.md") return false;

	const topicSegments = filePath.slice("topics/".length).split("/");
	if (topicSegments.length !== 1 && topicSegments.length !== 2) return false;
	return topicSegments.every((segment) =>
		TOPIC_SLUG_SEGMENT_PATTERN.test(segment),
	);
}

function isAllowedMcpWriterPath(filePath: string): boolean {
	if (filePath.includes("..")) return false;
	if (filePath === "crawler-state.json") return false;
	if (filePath.startsWith("reports/")) return true;
	if (isAllowedTopicPath(filePath)) return true;
	return SPEC_WRITER_PATH_PATTERN.test(filePath);
}

function validateEnvelopeShape(call: McpToolCall): string[] {
	const errors: string[] = [];
	if (call.jsonrpc !== "2.0")
		errors.push("/jsonrpc: must be equal to constant");
	if (call.method !== "tools/call")
		errors.push("/method: must be equal to constant");
	if (!call.params || typeof call.params !== "object")
		errors.push("/params: must be object");
	if (!Number.isInteger(call.id)) errors.push("/id: must be integer");
	return errors;
}

export function validateToolPolicyFixtureOracle(
	call: McpToolCall,
	preconditions: MergePreconditions = allGreenMergePreconditions,
): string[] {
	const errors = validateEnvelopeShape(call);
	if (errors.length > 0) return errors;

	const args = call.params.arguments;
	switch (call.params.name) {
		case "create_or_update_file": {
			const branch = asString(args.branch);
			const filePath = asString(args.path);
			const message = asString(args.message);
			if (!branch.startsWith(WRITER_BRANCH_PREFIX))
				errors.push("Writer branch must be osint/*");
			if (!isAllowedMcpWriterPath(filePath))
				errors.push(`Writer path is not allowed: ${filePath}`);
			if (filePath === "crawler-state.json")
				errors.push("crawler-state.json must not be written through Git MCP");
			if (!message.startsWith(WRITER_COMMIT_PREFIX))
				errors.push("Writer commit message prefix is required");
			break;
		}
		case "create_pull_request": {
			const head = asString(args.head);
			const title = asString(args.title);
			if (!head.startsWith(WRITER_BRANCH_PREFIX))
				errors.push("PR head must be osint/*");
			if (args.base !== "main") errors.push("PR base must be main");
			if (!title.startsWith(PR_TITLE_PREFIX))
				errors.push("PR title prefix is required");
			break;
		}
		case "merge_pull_request": {
			const commitTitle = asString(args.commit_title);
			if (args.merge_method !== "squash")
				errors.push("merge method must be squash");
			if (!commitTitle.startsWith(REVIEWER_COMMIT_TITLE_PREFIX))
				errors.push("Reviewer merge commit title prefix is required");
			if (!hasPassedMergePreconditions(preconditions))
				errors.push("merge preconditions are not all passed");
			break;
		}
		case "create_issue": {
			const title = asString(args.title);
			const body = asString(args.body);
			if (!title.startsWith(SYSTEM_ERROR_TITLE_PREFIX))
				errors.push("Issue title must signal system error");
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

export function assertMcpToolCallAllowedFixtureOracle(
	call: McpToolCall,
	preconditions: MergePreconditions = allGreenMergePreconditions,
): void {
	const errors = validateToolPolicyFixtureOracle(call, preconditions);
	if (errors.length === 0) return;
	throw new Error(`MCP tool call rejected: ${errors.join("; ")}`);
}
