import type { Fetcher } from "./crawler/fetch";
import type { StateBackendAdapter } from "./crawler/state";
import type { CrawlerState, SsotSource } from "./types";
import type {
	GateStatus,
	MergePreconditions,
	PolicyMcpToolCall,
} from "./mcp/tool-policy";
import type {
	OrchestratorEvent,
	OrchestratorState,
	TransitionContext,
	TransitionRecord,
} from "./orchestrator/state-machine";

export type OrchestratorGateStatus = GateStatus;
export type OrchestratorMergePreconditions = MergePreconditions;

export type McpToolCall = PolicyMcpToolCall;

export interface McpClient {
	callTool(call: PolicyMcpToolCall): Promise<unknown> | unknown;
}

export interface ToolMcpClient extends McpClient {}

export interface CrawlerEscalationDependencies {
	stateBackend?: StateBackendAdapter<CrawlerState>;
	mcpClient: McpClient;
	owner: string;
	repo: string;
	fetcher?: Fetcher;
	now?: Date | (() => Date);
	idFactory?: () => number;
	thirdPartyMailer?: { send: (...args: unknown[]) => unknown };
}

export interface CrawlerSourceSuccess {
	status: "success";
	source: SsotSource;
	sourceId: string;
	content: string;
	lastModifiedHeader: string | null;
	isNotModified: boolean;
}

export interface CrawlerSourceFailure {
	status: "failure";
	source: SsotSource;
	sourceId: string;
	error: string;
	escalated: boolean;
}

export type CrawlerSourceResult = CrawlerSourceSuccess | CrawlerSourceFailure;

export interface CrawlerEscalationResult {
	policy: "continue_after_source_failure" | "state_conflict_aborted";
	results: CrawlerSourceResult[];
	successes: CrawlerSourceSuccess[];
	failures: CrawlerSourceFailure[];
	state?: CrawlerState;
	escalationCalls: PolicyMcpToolCall[];
	escalatedIssueCalls: PolicyMcpToolCall[];
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
	reason: string;
	state?: OrchestratorState;
}

export type ExecutionStatus = "success" | "failure" | "no_changes";

export interface OrchestratorDependencies {
	mcpClient?: McpClient;
	reviewProposal?:
		| ((loop: number) => unknown)
		| ((diffs: DiffResult[]) => unknown);
	mergePreconditions?: MergePreconditions;
	maxReviewLoops?: number;
}

export interface AegisOrchestratorContract {
	readonly state: OrchestratorState;
	readonly prState: PRState | null;
	readonly diffs: DiffResult[];
	readonly transitionHistory: TransitionRecord[];
	readonly loopCount: number;
	readonly raisedIssue?: boolean;
	readonly launchedMcp?: boolean;
	run(): Promise<OrchestrationResult>;
}

export declare class AegisOrchestrator implements AegisOrchestratorContract {
	readonly diffs: DiffResult[];
	readonly transitionHistory: TransitionRecord[];
	readonly loopCount: number;
	readonly raisedIssue?: boolean;
	readonly launchedMcp?: boolean;
	state: OrchestratorState;
	prState: PRState | null;
	constructor(diffs: DiffResult[], dependencies?: OrchestratorDependencies);
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

export interface RunOrchestrationHooks {
	startMcp?: () => unknown;
	writeProposal?: (...args: unknown[]) => unknown;
	reviewProposal?: (...args: unknown[]) => unknown;
}

export interface RunOrchestrationContractResult {
	orchestrator: AegisOrchestratorContract;
	result: OrchestrationResult;
}

export declare function runOrchestration(
	diffs: DiffResult[],
	hooks?: RunOrchestrationHooks,
): Promise<RunOrchestrationContractResult>;
export declare function runOrchestration(
	request?: OrchestrationRequest,
): Promise<OrchestrationResult>;
export declare function crawlSourcesWithFailureEscalation(
	sources: SsotSource[],
	dependencies: CrawlerEscalationDependencies,
): Promise<CrawlerEscalationResult>;

export interface OrchestratorTransitionHistoryRecord {
	state: OrchestratorState;
	event: OrchestratorEvent;
	context: TransitionContext;
	result: TransitionRecord["result"];
}
