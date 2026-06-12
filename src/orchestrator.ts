import type { Fetcher } from "./crawler/fetch";
import type { StateBackendAdapter } from "./crawler/state";
import type { CrawlerState, SsotSource } from "./types";
import type {
	GateStatus,
	MergePreconditions,
	PolicyMcpToolCall,
} from "./mcp/tool-policy";
import type { OrchestratorState } from "./orchestrator/state-machine";

export type OrchestratorGateStatus = GateStatus;
export type OrchestratorMergePreconditions = MergePreconditions;

export type McpToolCall = PolicyMcpToolCall;

export interface McpClient {
	callTool(call: PolicyMcpToolCall): Promise<unknown> | unknown;
}

export interface ToolMcpClient extends McpClient {}

export interface CrawlerEscalationDependencies {
	stateBackend: StateBackendAdapter<CrawlerState>;
	mcpClient: McpClient;
	fetcher?: Fetcher;
	now?: Date;
}

export interface CrawlerSourceSuccess {
	status: "success";
	source: SsotSource;
	content: string;
	lastModifiedHeader: string | null;
	isNotModified: boolean;
}

export interface CrawlerSourceFailure {
	status: "failure";
	source: SsotSource;
	error: string;
	escalated: boolean;
}

export type CrawlerSourceResult = CrawlerSourceSuccess | CrawlerSourceFailure;

export interface CrawlerEscalationResult {
	results: CrawlerSourceResult[];
	state: CrawlerState;
	escalationCalls: PolicyMcpToolCall[];
}

export interface DiffResult {
	sourceId: string;
	hasChanged: boolean;
	content?: string;
}

export interface ReviewResult {
	approve: boolean;
	comment: string;
	mergePreconditions?: MergePreconditions;
}

export interface PRState {
	status: "NONE" | "OPEN" | "MERGED" | "REJECTED";
	branch?: string;
	pullNumber?: number;
}

export interface OrchestrationResult {
	exitCode: 0 | 1;
	reason?: string;
	state?: OrchestratorState;
}

export type ExecutionStatus = "success" | "failure" | "no_changes";

export interface OrchestratorDependencies {
	mcpClient?: McpClient;
	reviewProposal?: (
		diffs: DiffResult[],
	) => Promise<ReviewResult> | ReviewResult;
	mergePreconditions?: MergePreconditions;
	maxReviewLoops?: number;
}

export interface AegisOrchestratorContract {
	readonly state: OrchestratorState;
	readonly prState: PRState | null;
	readonly diffs: DiffResult[];
	run(): Promise<OrchestrationResult>;
}

export type OrchestrationRequest =
	| {
			kind: "diff_only";
			diffs: DiffResult[];
			dependencies?: OrchestratorDependencies;
	  }
	| {
			kind: "crawl_and_diff";
			sources: SsotSource[];
			state: CrawlerState;
			dependencies: CrawlerEscalationDependencies;
	  };
