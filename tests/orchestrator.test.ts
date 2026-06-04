/**
 * tests/orchestrator.test.ts
 *
 * Covers: spec.md §5.4 (Cooperative Loop), §5.6 (Failure Escalation),
 * business-rules.md §5 (Review Control), agent-logic.md §1 (Orchestrator Logic)
 *
 * Key rules under test:
 * - If no content changes are detected (idempotent), the orchestrator exits cleanly with code 0, without launching LLM/MCP.
 * - Under normal flow (happy path), the cooperative loop transitions: PENDING -> PROPOSED -> APPROVED.
 * - Under rejection flow, Writer is re-triggered up to 3 times (the hard loop limit).
 * - If the loop count exceeds 3 without approval, the orchestrator raises a GitHub Issue via MCP and terminates with code 1.
 */

import { test } from "node:test";
import * as assert from "node:assert";

// ---------------------------------------------------------------------------
// Mock Interfaces for Test Isolation
// ---------------------------------------------------------------------------

interface MockDiffResult {
	sourceId: string;
	hasChanged: boolean;
	content: string;
}

interface MockPRState {
	prNumber: number;
	status: "OPEN" | "CLOSED" | "MERGED";
	commits: string[];
	approved: boolean;
}

// ---------------------------------------------------------------------------
// Simulated Aegis-Orchestrator State Machine under test
// ---------------------------------------------------------------------------

class SimulatedOrchestrator {
	public loopCount = 0;
	public maxLoops = 3;
	public prState: MockPRState | null = null;
	public executionStatus: "PENDING" | "PROPOSED" | "APPROVED" | "REJECTED" | "ESCALATED" = "PENDING";
	public raisedIssue: { title: string; body: string } | null = null;
	public launchedMcp = false;

	constructor(
		private diffData: MockDiffResult[],
		private reviewerBehavior: (loops: number) => { approve: boolean; comment: string }
	) {}

	public async run() {
		// 1. べき等性変更検知（ハッシュ差分のシミュレーション）
		const hasAnyChange = this.diffData.some(d => d.hasChanged);
		if (!hasAnyChange) {
			this.executionStatus = "PENDING";
			return { exitCode: 0, reason: "No changes detected. Idempotent skip." };
		}

		// 2. 変更を検知したため、インプロセスでGitHub MCPを仮想起動
		this.launchedMcp = true;

		// 3. マルチエージェント対話ループ
		while (this.loopCount < this.maxLoops && this.executionStatus !== "APPROVED") {
			this.loopCount++;

			// 提案フェーズ (Aegis-Writer のターン)
			if (this.executionStatus === "PENDING" || this.executionStatus === "REJECTED") {
				if (!this.prState) {
					// 新規にPRを起票
					this.prState = {
						prNumber: 42,
						status: "OPEN",
						commits: ["Initial intelligence commit"],
						approved: false
					};
				} else {
					// 差し戻しによる再提案（コミットの追加）
					this.prState.commits.push(`Revision commit ${this.loopCount}`);
				}
				this.executionStatus = "PROPOSED";
			}

			// 査読フェーズ (Aegis-Reviewer のターン)
			if (this.executionStatus === "PROPOSED") {
				const review = this.reviewerBehavior(this.loopCount);
				if (review.approve) {
					this.executionStatus = "APPROVED";
					this.prState!.approved = true;
					this.prState!.status = "MERGED"; // 自律マージ成功
				} else {
					this.executionStatus = "REJECTED";
				}
			}
		}

		// 4. 最大ループ回数（3回）に達してもマージ合意されなかった場合の安全エスカレーション
		if (this.executionStatus !== "APPROVED") {
			this.executionStatus = "ESCALATED";
			this.raisedIssue = {
				title: "[System Error] Cooperative agent loop exceeded max limit",
				body: `Review loop failed to resolve after ${this.loopCount} iterations.`
			};
			return { exitCode: 1, reason: "Agreement failed. Escalated via Issue." };
		}

		return { exitCode: 0, reason: "Consensus reached and merged successfully." };
	}
}

// ---------------------------------------------------------------------------
// TDD Test Suites
// ---------------------------------------------------------------------------

test("Aegis-Orchestrator State Machine TDD Tests", async (t) => {

	await t.test("べき等性の成立：差分ハッシュが不変の場合は、MCPやLLMを起動せずに終了コード 0 で早期リターンすること", async () => {
		const unchangedDiff: MockDiffResult[] = [
			{ sourceId: "jpcert", hasChanged: false, content: "Same" }
		];

		const orchestrator = new SimulatedOrchestrator(unchangedDiff, () => ({
			approve: true,
			comment: "Will not be called"
		}));

		const result = await orchestrator.run();

		assert.strictEqual(result.exitCode, 0);
		assert.strictEqual(orchestrator.launchedMcp, false, "MCP should not be launched for unchanged content");
		assert.strictEqual(orchestrator.loopCount, 0, "No agent loops should run");
		assert.strictEqual(orchestrator.executionStatus, "PENDING");
	});

	await t.test("正常系：エージェントが協調し、1発で査読合格して main に自律マージ完了すること", async () => {
		const changedDiff: MockDiffResult[] = [
			{ sourceId: "jpcert", hasChanged: true, content: "New advisory details" }
		];

		// Reviewerは初回 (ループ1) からApproveを返す
		const orchestrator = new SimulatedOrchestrator(changedDiff, () => ({
			approve: true,
			comment: "Review passed. Excellent."
		}));

		const result = await orchestrator.run();

		assert.strictEqual(result.exitCode, 0);
		assert.strictEqual(orchestrator.launchedMcp, true);
		assert.strictEqual(orchestrator.loopCount, 1, "Should reach consensus in 1 loop");
		assert.strictEqual(orchestrator.executionStatus, "APPROVED");
		assert.strictEqual(orchestrator.prState?.status, "MERGED");
		assert.strictEqual(orchestrator.prState?.approved, true);
	});

	await t.test("準正常系：1回目の査読却下に対してWriterが修正提案を行い、2回目で合意マージ完了すること", async () => {
		const changedDiff: MockDiffResult[] = [
			{ sourceId: "nco", hasChanged: true, content: "New cabinet decision details" }
		];

		// ループ1では却下し、ループ2で合格にする挙動を定義
		const reviewerBehavior = (loop: number) => {
			if (loop === 1) {
				return { approve: false, comment: "Missing inbound link for orphan NICT note" };
			}
			return { approve: true, comment: "Link fixed. Approved." };
		};

		const orchestrator = new SimulatedOrchestrator(changedDiff, reviewerBehavior);

		const result = await orchestrator.run();

		assert.strictEqual(result.exitCode, 0);
		assert.strictEqual(orchestrator.loopCount, 2, "Consensus reached on loop 2");
		assert.strictEqual(orchestrator.executionStatus, "APPROVED");
		assert.strictEqual(orchestrator.prState?.commits.length, 2, "Should contain corrective commit");
		assert.strictEqual(orchestrator.prState?.status, "MERGED");
	});

	await t.test("異常系：3回のループ制限で却下され続けた場合、マージを遮断し、GitHub Issueを起票してエラー（終了コード1）終了すること", async () => {
		const changedDiff: MockDiffResult[] = [
			{ sourceId: "jpcert", hasChanged: true, content: "Critical malware notice" }
		];

		// 常にリジェクトし続ける頑固なReviewer
		const orchestrator = new SimulatedOrchestrator(changedDiff, () => ({
			approve: false,
			comment: "OFM layout violation: tags are malformed."
		}));

		const result = await orchestrator.run();

		assert.strictEqual(result.exitCode, 1, "Must exit with failure code 1");
		assert.strictEqual(orchestrator.loopCount, 3, "Hard loop limit capped at 3");
		assert.strictEqual(orchestrator.executionStatus, "ESCALATED");
		assert.strictEqual(orchestrator.prState?.status, "OPEN", "PR must remain open (not merged)");
		
		// エスカレーションIssueが起票されていることの検証
		assert.ok(orchestrator.raisedIssue, "System must raise an Issue");
		assert.ok(orchestrator.raisedIssue.title.includes("[System Error]"));
		assert.ok(orchestrator.raisedIssue.body.includes("Review loop failed to resolve after 3 iterations"));
	});
});
