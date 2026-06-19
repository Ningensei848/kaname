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
export type McpToolName =
	| "create_issue"
	| "create_or_update_file"
	| "create_pull_request"
	| "merge_pull_request";
export interface McpToolPolicyViolation {
	code: string;
	message: string;
	path?: string;
}
export interface ReviewerGateEvidence {
	name: keyof MergePreconditions;
	status: GateStatus;
	details?: string;
}
export interface WriterPathPolicy {
	allowedPatterns: readonly RegExp[];
	rejectGeneratedIndexesUntilExplicitlyListed: boolean;
	rejectNestedTopicPaths: boolean;
}
export interface McpToolCall {
	jsonrpc: "2.0";
	method: "tools/call";
	params: { name: McpToolName; arguments: JsonObject };
	id: number;
}
export type PolicyMcpToolCall = McpToolCall;
export type MergePolicyVerdict = "allowed" | "blocked";
