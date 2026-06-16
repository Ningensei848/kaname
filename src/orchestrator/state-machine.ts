export type OrchestratorState =
	| "INIT"
	| "MCP_READY"
	| "PROPOSED"
	| "REJECTED"
	| TerminalState;

export type TerminalState =
	| "DONE"
	| "MERGED"
	| "ESCALATED"
	| "FAILED"
	| "TIMEOUT";

export type OrchestratorEvent =
	| "diff_empty"
	| "diff_found"
	| "writer_success"
	| "reviewer_approved"
	| "reviewer_rejected"
	| "ci_failed"
	| "takumi_guard_failed"
	| "content_guard_failed"
	| "protected_branch_evidence_missing"
	| "deterministic_guard_failed"
	| "loop_remaining"
	| "loop_exhausted"
	| "timeout"
	| "fatal_error";

export interface ReviewAttempt {
	readonly attempt: number;
	readonly reviewerApproved: boolean;
}

export interface TransitionContext {
	readonly loopCount: number;
	readonly maxLoops: number;
	readonly allGatesPassed: boolean;
	readonly prExists: boolean;
	readonly contentChanged?: boolean;
	readonly ciPassed?: boolean;
	readonly takumiGuardPassed?: boolean;
	readonly contentGuardPassed?: boolean;
	readonly protectedBranchEvidencePresent?: boolean;
	readonly reviewAttempts?: readonly ReviewAttempt[];
}

export type TransitionAction =
	| "exit_0"
	| "start_mcp"
	| "start_writer"
	| "start_reviewer"
	| "wait_ci"
	| "comment_reject"
	| "squash_merge"
	| "writer_revise"
	| "create_issue"
	| "escalate_issue"
	| "cleanup_mcp";

export type OrchestratorAction = TransitionAction;

export interface TransitionResult {
	readonly next: OrchestratorState;
	readonly actions: readonly TransitionAction[];
	readonly mergeable?: boolean;
}

export interface TransitionRecord {
	readonly state: OrchestratorState;
	readonly event: OrchestratorEvent;
	readonly context: TransitionContext;
	readonly result: TransitionResult;
}

export class OrchestratorStateMachine {
	public transition(
		state: OrchestratorState,
		event: OrchestratorEvent,
		context: TransitionContext,
	): TransitionResult {
		return transition(state, event, context);
	}
}

export function transition(
	_state: OrchestratorState,
	_event: OrchestratorEvent,
	_context: TransitionContext,
): TransitionResult {
	throw new Error("F003 transition table is not implemented yet");
}
