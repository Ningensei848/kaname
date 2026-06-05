/**
 * tests/orchestrator.test.ts
 *
 * Covers: spec.md §5.4 (Cooperative Loop), §5.6 (Failure Escalation),
 * business-rules.md §5 (Review Control), agent-logic.md §1 (Orchestrator Logic)
 */

import { test } from "node:test";
import * as assert from "node:assert";
import { AegisOrchestrator, type DiffResult } from "../src/orchestrator";

test("Aegis-Orchestrator State Machine TDD Tests", async (t) => {
	await t.test(
		"べき等性の成立：差分ハッシュが不変の場合は、MCPやLLMを起動せずに終了コード 0 で早期リターンすること",
		async () => {
			const unchangedDiff: DiffResult[] = [
				{ sourceId: "jpcert", hasChanged: false, content: "Same" },
			];

			const orchestrator = new AegisOrchestrator(unchangedDiff, {
				reviewProposal: () => ({
					approve: true,
					comment: "Will not be called",
				}),
			});

			const result = await orchestrator.run();

			assert.strictEqual(result.exitCode, 0);
			assert.strictEqual(
				orchestrator.launchedMcp,
				false,
				"MCP should not be launched for unchanged content",
			);
			assert.strictEqual(
				orchestrator.loopCount,
				0,
				"No agent loops should run",
			);
			assert.strictEqual(orchestrator.executionStatus, "PENDING");
		},
	);

	await t.test(
		"正常系：エージェントが協調し、1発で査読合格して main に自律マージ完了すること",
		async () => {
			const changedDiff: DiffResult[] = [
				{
					sourceId: "jpcert",
					hasChanged: true,
					content: "New advisory details",
				},
			];

			const orchestrator = new AegisOrchestrator(changedDiff, {
				reviewProposal: () => ({
					approve: true,
					comment: "Review passed. Excellent.",
				}),
			});

			const result = await orchestrator.run();

			assert.strictEqual(result.exitCode, 0);
			assert.strictEqual(orchestrator.launchedMcp, true);
			assert.strictEqual(
				orchestrator.loopCount,
				1,
				"Should reach consensus in 1 loop",
			);
			assert.strictEqual(orchestrator.executionStatus, "APPROVED");
			assert.strictEqual(orchestrator.prState?.status, "MERGED");
			assert.strictEqual(orchestrator.prState?.approved, true);
		},
	);

	await t.test(
		"準正常系：1回目の査読却下に対してWriterが修正提案を行い、2回目で合意マージ完了すること",
		async () => {
			const changedDiff: DiffResult[] = [
				{
					sourceId: "nco",
					hasChanged: true,
					content: "New cabinet decision details",
				},
			];

			const orchestrator = new AegisOrchestrator(changedDiff, {
				reviewProposal: (loop: number) => {
					if (loop === 1) {
						return {
							approve: false,
							comment: "Missing inbound link for orphan NICT note",
						};
					}
					return { approve: true, comment: "Link fixed. Approved." };
				},
			});

			const result = await orchestrator.run();

			assert.strictEqual(result.exitCode, 0);
			assert.strictEqual(
				orchestrator.loopCount,
				2,
				"Consensus reached on loop 2",
			);
			assert.strictEqual(orchestrator.executionStatus, "APPROVED");
			assert.strictEqual(
				orchestrator.prState?.commits.length,
				2,
				"Should contain corrective commit",
			);
			assert.strictEqual(orchestrator.prState?.status, "MERGED");
		},
	);

	await t.test(
		"異常系：3回のループ制限で却下され続けた場合、マージを遮断し、GitHub Issueを起票してエラー（終了コード1）終了すること",
		async () => {
			const changedDiff: DiffResult[] = [
				{
					sourceId: "jpcert",
					hasChanged: true,
					content: "Critical malware notice",
				},
			];

			const orchestrator = new AegisOrchestrator(changedDiff, {
				reviewProposal: () => ({
					approve: false,
					comment: "OFM layout violation: tags are malformed.",
				}),
			});

			const result = await orchestrator.run();

			assert.strictEqual(result.exitCode, 1, "Must exit with failure code 1");
			assert.strictEqual(
				orchestrator.loopCount,
				3,
				"Hard loop limit capped at 3",
			);
			assert.strictEqual(orchestrator.executionStatus, "ESCALATED");
			assert.strictEqual(
				orchestrator.prState?.status,
				"OPEN",
				"PR must remain open (not merged)",
			);
			assert.ok(orchestrator.raisedIssue, "System must raise an Issue");
			assert.ok(orchestrator.raisedIssue.title.includes("[System Error]"));
			assert.ok(
				orchestrator.raisedIssue.body.includes(
					"Review loop failed to resolve after 3 iterations",
				),
			);
		},
	);
});
