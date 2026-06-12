export type JsonObject = Record<string, unknown>;

export type GateStatus = "passed" | "failed" | "unavailable" | "indeterminate";

export interface MergePreconditions {
	ci: GateStatus;
	takumiGuard: GateStatus;
	deterministicContentGuards: GateStatus;
	branchPolicy: GateStatus;
	immutableFiles: GateStatus;
	internalLinks: GateStatus;
	artifact?: GateStatus;
}

export type ToolName =
	| "create_or_update_file"
	| "create_pull_request"
	| "merge_pull_request"
	| "create_issue";

export interface McpToolCallEnvelope<TName extends ToolName, TArguments> {
	jsonrpc: "2.0";
	method: "tools/call";
	id: number;
	params: {
		name: TName;
		arguments: TArguments;
	};
}

export interface BaseRepoArguments extends JsonObject {
	owner: string;
	repo: string;
}

export interface CreateOrUpdateFileArguments extends BaseRepoArguments {
	branch: string;
	path: string;
	message: string;
	content: string;
	sha?: string;
}

export interface CreatePullRequestArguments extends BaseRepoArguments {
	title: string;
	head: string;
	base: string;
	body: string;
}

export interface MergePullRequestArguments extends BaseRepoArguments {
	pull_number: number;
	commit_title: string;
	commit_message?: string;
	merge_method: "squash";
}

export interface CreateIssueArguments extends BaseRepoArguments {
	title: string;
	body: string;
	labels?: string[];
}

export interface ToolArguments extends JsonObject {
	owner?: string;
	repo?: string;
	branch?: unknown;
	path?: unknown;
	message?: unknown;
	content?: unknown;
	sha?: unknown;
	title?: string;
	head?: unknown;
	base?: unknown;
	body?: string;
	pull_number?: unknown;
	commit_title?: unknown;
	commit_message?: unknown;
	merge_method?: unknown;
	labels?: unknown;
}

export interface PolicyMcpToolCall {
	jsonrpc: "2.0";
	method: "tools/call";
	id: number;
	params: {
		name: ToolName;
		arguments: ToolArguments;
	};
}

export type StrictPolicyMcpToolCall =
	| McpToolCallEnvelope<"create_or_update_file", CreateOrUpdateFileArguments>
	| McpToolCallEnvelope<"create_pull_request", CreatePullRequestArguments>
	| McpToolCallEnvelope<"merge_pull_request", MergePullRequestArguments>
	| McpToolCallEnvelope<"create_issue", CreateIssueArguments>;

export type ToolPolicyViolation =
	| { kind: "envelope"; path: string; message: string }
	| { kind: "arguments"; tool: ToolName; path: string; message: string }
	| {
			kind: "merge_precondition";
			gate: keyof MergePreconditions;
			status: GateStatus;
	  }
	| { kind: "repository_boundary"; path: string; message: string };

export declare const allGreenMergePreconditions: MergePreconditions;
export interface JsonRpcToolCallLike {
	jsonrpc: string;
	method: string;
	id: number;
	params: { name: string; arguments: Record<string, unknown> };
}

export declare function validateToolPolicy(
	call: JsonRpcToolCallLike,
	preconditions?: MergePreconditions,
): string[];
export declare function canMerge(gates: MergePreconditions): boolean;
export declare function validateMergePreconditions(
	preconditions: MergePreconditions,
): string[];
