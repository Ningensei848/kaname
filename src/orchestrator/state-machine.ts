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
	| "detailed_reject"
	| "ci_failed"
	| "takumi_guard_failed"
	| "content_guard_failed"
	| "protected_branch_evidence_missing"
	| "deterministic_guard_failed"
	| "loop_remaining"
	| "loop_exhausted"
	| "timeout"
	| "fatal_error";
export type DetailedRejectTargetGuard =
	| "reviewer"
	| "ci"
	| "takumi_guard"
	| "content_guard"
	| "protected_branch"
	| "deterministic_guard";

export interface DetailedRejectPayload {
	readonly rejectReason: string;
	readonly targetGuard: DetailedRejectTargetGuard;
	readonly revisionInstruction: string;
	readonly loopCount: number;
}

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
export interface OrchestratorStateMachineContract {
	transition(
		state: OrchestratorState,
		event: OrchestratorEvent,
		context: TransitionContext,
	): TransitionResult;
}

const proposedRejectionEvents: ReadonlySet<OrchestratorEvent> = new Set([
	"reviewer_rejected",
	"detailed_reject",
	"ci_failed",
	"takumi_guard_failed",
	"content_guard_failed",
	"protected_branch_evidence_missing",
	"deterministic_guard_failed",
]);

export function transition(
	state: OrchestratorState,
	event: OrchestratorEvent,
	context: TransitionContext,
): TransitionResult {
	if (event === "fatal_error") {
		return { next: "FAILED", actions: ["create_issue", "cleanup_mcp"] };
	}

	if (event === "timeout") {
		return { next: "TIMEOUT", actions: ["cleanup_mcp"] };
	}

	if (state === "INIT" && event === "diff_empty") {
		return { next: "DONE", actions: ["exit_0", "cleanup_mcp"] };
	}

	if (state === "INIT" && event === "diff_found") {
		return { next: "MCP_READY", actions: ["start_mcp"] };
	}

	if (state === "MCP_READY" && event === "writer_success") {
		return { next: "PROPOSED", actions: ["start_writer", "wait_ci"] };
	}

	if (state === "PROPOSED" && proposedRejectionEvents.has(event)) {
		return { next: "REJECTED", actions: ["comment_reject"], mergeable: false };
	}

	if (
		state === "PROPOSED" &&
		event === "reviewer_approved" &&
		context.allGatesPassed === true
	) {
		return {
			next: "MERGED",
			actions: ["squash_merge", "cleanup_mcp"],
			mergeable: true,
		};
	}

	if (state === "REJECTED" && event === "loop_remaining") {
		return { next: "PROPOSED", actions: ["writer_revise"] };
	}

	if (state === "REJECTED" && event === "loop_exhausted") {
		return { next: "ESCALATED", actions: ["escalate_issue", "cleanup_mcp"] };
	}

	return { next: "FAILED", actions: ["cleanup_mcp"], mergeable: false };
}
