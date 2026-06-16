import type { Fetcher } from "./crawler/fetch";
import type { StateBackendAdapter } from "./crawler/state";
import type {
	MergePreconditions,
	PolicyMcpToolCall,
	GateStatus,
} from "./mcp/tool-policy";
import type {
	OrchestratorState,
	TransitionRecord,
} from "./orchestrator/state-machine";
import type { CrawlerState } from "./types";
export type OrchestratorGateStatus = GateStatus;
export type OrchestratorMergePreconditions = MergePreconditions;
export interface McpToolCall extends PolicyMcpToolCall {
	params: {
		name: "create_issue";
		arguments: { owner: string; repo: string; title: string; body: string };
	};
}
export interface McpClient {
	callTool: (call: McpToolCall) => Promise<unknown> | unknown;
}
export interface ToolMcpClient {
	callTool: (call: PolicyMcpToolCall) => Promise<unknown> | unknown;
}
export interface CrawlerEscalationDependencies {
	mcpClient: McpClient;
	owner: string;
	repo: string;
	fetcher?: Fetcher;
	stateBackend?: StateBackendAdapter<CrawlerState>;
	now?: () => Date;
	idFactory?: () => number;
	thirdPartyMailer?: { send: (message: unknown) => Promise<unknown> | unknown };
}
export interface CrawlerSourceSuccess {
	sourceId: string;
	content: string;
	lastModifiedHeader: string | null;
	isNotModified: boolean;
}
export interface CrawlerSourceFailure {
	sourceId: string;
	error: Error;
}
export interface CrawlerEscalationResult {
	policy: "continue_after_source_failure" | "state_conflict_aborted";
	successes: CrawlerSourceSuccess[];
	failures: CrawlerSourceFailure[];
	escalatedIssueCalls: McpToolCall[];
}
export interface DiffResult {
	sourceId: string;
	hasChanged: boolean;
	content: string;
}
export interface ReviewResult {
	approve: boolean;
	comment: string;
	mergePreconditions: MergePreconditions;
}
export interface PRState {
	prNumber: number;
	status: "OPEN" | "CLOSED" | "MERGED";
	commits: string[];
	approved: boolean;
	head?: string;
	base?: string;
}
export interface OrchestrationResult {
	exitCode: 0 | 1;
	reason: string;
}
export type ExecutionStatus =
	| "PENDING"
	| "PROPOSED"
	| "APPROVED"
	| "REJECTED"
	| "ESCALATED";
export interface OrchestratorDependencies {
	startMcp?: () => Promise<void> | void;
	mcpClient?: ToolMcpClient;
	owner?: string;
	repo?: string;
	writeProposal?: (
		loop: number,
		currentPr: PRState | null,
		diffData: DiffResult[],
	) => Promise<PRState> | PRState;
	reviewProposal: (
		loop: number,
		prState: PRState,
	) => Promise<ReviewResult> | ReviewResult;
	raiseIssue?: (
		loopCount: number,
		prState: PRState | null,
	) =>
		| Promise<{ title: string; body: string }>
		| { title: string; body: string };
}
export interface AegisOrchestratorSnapshot {
	loopCount: number;
	maxLoops: number;
	prState: PRState | null;
	state: OrchestratorState;
	executionStatus: ExecutionStatus;
	raisedIssue: { title: string; body: string } | null;
	launchedMcp: boolean;
	transitionHistory: TransitionRecord[];
}
