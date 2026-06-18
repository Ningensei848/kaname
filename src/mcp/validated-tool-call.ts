import {
	defaultMergePreconditions,
	validateToolPolicy,
	type McpToolCall,
	type MergePreconditions,
} from "./tool-policy";

export function assertMcpToolCallAllowed(
	call: McpToolCall,
	preconditions: MergePreconditions = defaultMergePreconditions,
): void {
	const errors = validateToolPolicy(call, preconditions);
	if (errors.length === 0) return;

	throw new Error(`MCP tool call rejected: ${errors.join("; ")}`);
}
