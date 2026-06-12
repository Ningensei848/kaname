export type OrchestratorState =
	| "INIT"
	| "MCP_READY"
	| "PROPOSED"
	| "REJECTED"
	| "MERGED"
	| "ESCALATED"
	| "FAILED"
	| "DONE";

export type OrchestratorEvent =
	| "diff_empty"
	| "diff_found"
	| "writer_success"
	| "deterministic_guard_failed"
	| "reviewer_approved"
	| "loop_remaining"
	| "loop_exhausted"
	| "fatal_error";

export type OrchestratorAction =
	| "exit_0"
	| "start_mcp"
	| "wait_ci"
	| "comment_reject"
	| "squash_merge"
	| "cleanup_mcp"
	| "writer_revise"
	| "create_issue";

export interface TransitionContext {
	loopCount: number;
	maxLoops: number;
	allGatesPassed: boolean;
	prExists: boolean;
}

export interface TransitionResult {
	next: OrchestratorState;
	actions: OrchestratorAction[];
}

export interface TransitionRecord {
	state: OrchestratorState;
	event: OrchestratorEvent;
	context: TransitionContext;
	result: TransitionResult;
}

export type OrchestratorTransitionContract =
	| {
			from: "INIT";
			on: "diff_empty";
			to: "DONE";
			actions: ["exit_0"];
	  }
	| {
			from: "INIT";
			on: "diff_found";
			to: "MCP_READY";
			actions: ["start_mcp"];
	  }
	| {
			from: "MCP_READY";
			on: "writer_success";
			to: "PROPOSED";
			actions: ["wait_ci"];
	  }
	| {
			from: "PROPOSED";
			on: "deterministic_guard_failed";
			to: "REJECTED";
			actions: ["comment_reject"];
	  }
	| {
			from: "PROPOSED";
			on: "reviewer_approved";
			to: "MERGED" | "FAILED";
			actions:
				| ["squash_merge", "cleanup_mcp"]
				| ["create_issue", "cleanup_mcp"];
	  }
	| {
			from: "REJECTED";
			on: "loop_remaining" | "loop_exhausted";
			to: "PROPOSED" | "ESCALATED";
			actions: ["writer_revise"] | ["create_issue", "cleanup_mcp"];
	  };

export declare function transition(
	state: OrchestratorState,
	event: OrchestratorEvent,
	context: TransitionContext,
): TransitionResult;
