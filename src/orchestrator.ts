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
	public executionStatus: ExecutionStatus = "PENDING";
	public raisedIssue: { title: string; body: string } | null = null;
	public launchedMcp = false;

	public constructor(
		private readonly diffData: DiffResult[],
		private readonly dependencies: OrchestratorDependencies,
		maxLoops = 3,
	) {
		this.maxLoops = maxLoops;
	}

	public async run(): Promise<OrchestrationResult> {
		const hasAnyChange = this.diffData.some((diff) => diff.hasChanged);
		if (!hasAnyChange) {
			return { exitCode: 0, reason: "No changes detected. Idempotent skip." };
		}

		this.launchedMcp = true;
		await this.dependencies.startMcp?.();

		while (
			this.loopCount < this.maxLoops &&
			this.executionStatus !== "APPROVED"
		) {
			this.loopCount++;

			if (
				this.executionStatus === "PENDING" ||
				this.executionStatus === "REJECTED"
			) {
				this.prState = await this.runWriter(this.loopCount);
				this.executionStatus = "PROPOSED";
			}

			if (this.executionStatus === "PROPOSED" && this.prState) {
				const review = await this.dependencies.reviewProposal(
					this.loopCount,
					this.prState,
				);
				if (review.approve) {
					this.executionStatus = "APPROVED";
					this.prState.approved = true;
					this.prState.status = "MERGED";
				} else {
					this.executionStatus = "REJECTED";
				}
			}
		}

		if (this.executionStatus !== "APPROVED") {
			this.executionStatus = "ESCALATED";
			this.raisedIssue = await this.raiseIssue();
			return { exitCode: 1, reason: "Agreement failed. Escalated via Issue." };
		}

		return {
			exitCode: 0,
			reason: "Consensus reached and merged successfully.",
		};
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
