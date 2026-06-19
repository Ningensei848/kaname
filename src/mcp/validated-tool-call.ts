import type { McpToolCall, MergePreconditions } from "./tool-policy";

/**
 * Current-phase MCP validation is a type-only contract boundary.
 * Runtime tool-policy enforcement is quarantined until the production phase.
 */
export interface ValidatedMcpToolCallContract {
	call: McpToolCall;
	preconditions?: MergePreconditions;
}
