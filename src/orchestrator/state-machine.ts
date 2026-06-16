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

	if (state === "REJECTED" && context.loopCount >= context.maxLoops) {
		return {
			next: "ESCALATED",
			actions: context.contentChanged
				? ["escalate_issue", "cleanup_mcp"]
				: ["create_issue", "cleanup_mcp"],
		};
	}

	if (state === "INIT" && event === "diff_empty") {
		return { next: "DONE", actions: ["exit_0"] };
	}

	if (state === "INIT" && event === "diff_found") {
		return { next: "MCP_READY", actions: ["start_mcp"] };
	}

	if (state === "MCP_READY" && event === "writer_success" && context.prExists) {
		return {
			next: "PROPOSED",
			actions: context.contentChanged
				? ["start_writer", "wait_ci"]
				: ["wait_ci"],
		};
	}

	if (
		state === "PROPOSED" &&
		(event === "deterministic_guard_failed" || event === "reviewer_rejected")
	) {
		return { next: "REJECTED", actions: ["comment_reject"], mergeable: false };
	}

	if (
		state === "PROPOSED" &&
		[
			"ci_failed",
			"takumi_guard_failed",
			"content_guard_failed",
			"protected_branch_evidence_missing",
		].includes(event)
	) {
		return {
			next: "FAILED",
			actions: ["create_issue", "cleanup_mcp"],
			mergeable: false,
		};
	}

	if (
		state === "PROPOSED" &&
		event === "reviewer_approved" &&
		context.allGatesPassed
	) {
		return {
			next: "MERGED",
			actions: ["squash_merge", "cleanup_mcp"],
			mergeable: true,
		};
	}

	if (
		state === "REJECTED" &&
		event === "loop_remaining" &&
		context.loopCount < context.maxLoops
	) {
		return { next: "PROPOSED", actions: ["writer_revise"], mergeable: false };
	}

	if (
		state === "REJECTED" &&
		event === "loop_exhausted" &&
		context.loopCount >= context.maxLoops
	) {
		return {
			next: "ESCALATED",
			actions: context.contentChanged
				? ["escalate_issue", "cleanup_mcp"]
				: ["create_issue", "cleanup_mcp"],
			mergeable: false,
		};
	}

	return {
		next: "FAILED",
		actions: ["create_issue", "cleanup_mcp"],
		mergeable: false,
	};
}
