import {
	type OrchestratorEvent,
	type OrchestratorState,
	type TransitionContext,
	type TransitionRecord,
	transition,
} from "./orchestrator/state-machine";

export interface DiffResult {
	sourceId: string;
	hasChanged: boolean;
	content: string;
}

export interface ReviewResult {
	approve: boolean;
	comment: string;
}

export interface PRState {
	prNumber: number;
	status: "OPEN" | "CLOSED" | "MERGED";
	commits: string[];
	approved: boolean;
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

export class AegisOrchestrator {
	public loopCount = 0;
	public readonly maxLoops: number;
	public prState: PRState | null = null;
	public state: OrchestratorState = "INIT";
	public executionStatus: ExecutionStatus = "PENDING";
	public raisedIssue: { title: string; body: string } | null = null;
	public launchedMcp = false;
	public readonly transitionHistory: TransitionRecord[] = [];

	public constructor(
		private readonly diffData: DiffResult[],
		private readonly dependencies: OrchestratorDependencies,
		maxLoops = 3,
	) {
		this.maxLoops = maxLoops;
	}

	public async run(): Promise<OrchestrationResult> {
		try {
			const hasAnyChange = this.diffData.some((diff) => diff.hasChanged);
			if (!hasAnyChange) {
				this.applyTransition("diff_empty");
				return { exitCode: 0, reason: "No changes detected. Idempotent skip." };
			}

			this.applyTransition("diff_found");
			this.launchedMcp = this.state === "MCP_READY";
			await this.dependencies.startMcp?.();

			this.loopCount++;
			this.prState = await this.runWriter(this.loopCount);
			this.applyTransition("writer_success");

			for (;;) {
				if (this.state !== "PROPOSED") {
					break;
				}

				const review = await this.dependencies.reviewProposal(
					this.loopCount,
					this.prState,
				);

				const reviewState = this.applyTransition(
					review.approve ? "reviewer_approved" : "deterministic_guard_failed",
					review.approve,
				);

				if (reviewState === "MERGED") {
					this.mergePr();
					return {
						exitCode: 0,
						reason: "Consensus reached and merged successfully.",
					};
				}

				if (reviewState !== "REJECTED") {
					break;
				}

				const loopEvent: OrchestratorEvent =
					this.loopCount >= this.maxLoops ? "loop_exhausted" : "loop_remaining";
				const loopState = this.applyTransition(loopEvent, review.approve);

				if (loopState === "PROPOSED") {
					this.loopCount++;
					this.prState = await this.runWriter(this.loopCount);
				}
			}

			if (this.state === "ESCALATED" || this.state === "FAILED") {
				this.raisedIssue = await this.raiseIssue();
				return {
					exitCode: 1,
					reason: "Agreement failed. Escalated via Issue.",
				};
			}

			this.applyTransition("fatal_error");
			this.raisedIssue = await this.raiseIssue();
			return { exitCode: 1, reason: "Orchestration failed." };
		} catch (error) {
			if (this.state !== "FAILED") {
				this.applyTransition("fatal_error");
			}
			this.raisedIssue = await this.raiseIssue();
			const message = error instanceof Error ? error.message : "Unknown error";
			return { exitCode: 1, reason: `Orchestration failed: ${message}` };
		}
	}

	private applyTransition(
		event: OrchestratorEvent,
		allGatesPassed = true,
	): OrchestratorState {
		const context = this.currentTransitionContext(allGatesPassed);
		const state = this.state;
		const result = transition(state, event, context);
		this.transitionHistory.push({ state, event, context, result });
		this.state = result.next;
		this.executionStatus = this.executionStatusFor(result.next);
		return result.next;
	}

	private currentTransitionContext(allGatesPassed: boolean): TransitionContext {
		return {
			loopCount: this.loopCount,
			maxLoops: this.maxLoops,
			allGatesPassed,
			prExists: this.prState !== null,
		};
	}

	private executionStatusFor(state: OrchestratorState): ExecutionStatus {
		if (state === "PROPOSED") {
			return "PROPOSED";
		}
		if (state === "REJECTED") {
			return "REJECTED";
		}
		if (state === "MERGED") {
			return "APPROVED";
		}
		if (state === "ESCALATED" || state === "FAILED") {
			return "ESCALATED";
		}
		return "PENDING";
	}

	private mergePr(): void {
		if (!this.prState) {
			return;
		}
		this.prState.approved = true;
		this.prState.status = "MERGED";
	}

	private async runWriter(loop: number): Promise<PRState> {
		if (this.dependencies.writeProposal) {
			return this.dependencies.writeProposal(loop, this.prState, this.diffData);
		}

		if (!this.prState) {
			return {
				prNumber: 42,
				status: "OPEN",
				commits: ["Initial intelligence commit"],
				approved: false,
			};
		}

		return {
			...this.prState,
			commits: [...this.prState.commits, `Revision commit ${loop}`],
		};
	}

	private async raiseIssue(): Promise<{ title: string; body: string }> {
		if (this.dependencies.raiseIssue) {
			return this.dependencies.raiseIssue(this.loopCount, this.prState);
		}

		return {
			title: "[System Error] Cooperative agent loop exceeded max limit",
			body: `Review loop failed to resolve after ${this.loopCount} iterations.`,
		};
	}
}

export async function runOrchestration(
	diffData: DiffResult[],
	dependencies: OrchestratorDependencies,
	maxLoops = 3,
): Promise<{ orchestrator: AegisOrchestrator; result: OrchestrationResult }> {
	const orchestrator = new AegisOrchestrator(diffData, dependencies, maxLoops);
	const result = await orchestrator.run();
	return { orchestrator, result };
}

if (require.main === module) {
	console.log(
		"kaname orchestrator module loaded. Use runOrchestration() from Cloud Run entrypoint wiring.",
	);
}
