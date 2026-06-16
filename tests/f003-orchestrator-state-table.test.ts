/**
 * F003 red contract tests for the future explicit orchestrator state table.
 *
 * These tests intentionally describe required behavior before production
 * `transition()` is implemented. They are derived from:
 * - `.spec/features/003-orchestrator-mcp-review-loop/spec.md`
 * - `.spec/features/003-orchestrator-mcp-review-loop/acceptance.md`
 */

import * as assert from "node:assert";
import { test } from "node:test";

import { transition } from "../src/orchestrator/state-machine";
import type {
	OrchestratorEvent,
	TerminalState,
	TransitionAction,
	TransitionContext,
} from "../src/orchestrator/state-machine";

const baseContext: TransitionContext = {
	loopCount: 0,
	maxLoops: 3,
	allGatesPassed: true,
	prExists: true,
	contentChanged: true,
	ciPassed: true,
	takumiGuardPassed: true,
	contentGuardPassed: true,
	protectedBranchEvidencePresent: true,
};

function assertNoActions(
	actions: readonly TransitionAction[],
	forbidden: readonly TransitionAction[],
): void {
	for (const action of forbidden) {
		assert.equal(
			actions.includes(action),
			false,
			`unexpected action: ${action}`,
		);
	}
}

test("F003 unchanged content exits without writer, reviewer, or MCP startup", () => {
	const result = transition("INIT", "diff_empty", {
		...baseContext,
		contentChanged: false,
		prExists: false,
	});

	assert.equal(result.next, "DONE");
	assertNoActions(result.actions, [
		"start_writer",
		"start_reviewer",
		"start_mcp",
	]);
});

test("F003 changed content starts MCP and then creates a writer action", () => {
	const mcpReady = transition("INIT", "diff_found", baseContext);
	assert.deepEqual(mcpReady, { next: "MCP_READY", actions: ["start_mcp"] });

	const proposed = transition("MCP_READY", "writer_success", baseContext);
	assert.equal(proposed.next, "PROPOSED");
	assert.equal(proposed.actions.includes("start_writer"), true);
});

test("F003 reviewer rejection retries writer up to three attempts", () => {
	for (const loopCount of [0, 1, 2]) {
		const rejected = transition("PROPOSED", "reviewer_rejected", {
			...baseContext,
			loopCount,
			allGatesPassed: false,
		});
		assert.equal(rejected.next, "REJECTED");

		const retry = transition("REJECTED", "loop_remaining", {
			...baseContext,
			loopCount,
			allGatesPassed: false,
		});
		assert.equal(retry.next, "PROPOSED");
		assert.equal(retry.actions.includes("writer_revise"), true);
	}
});

test("F003 rejection beyond three attempts escalates", () => {
	const result = transition("REJECTED", "loop_exhausted", {
		...baseContext,
		loopCount: 3,
		allGatesPassed: false,
	});

	assert.equal(result.next, "ESCALATED");
	assert.equal(result.actions.includes("escalate_issue"), true);
	assert.equal(result.actions.includes("cleanup_mcp"), true);
});

const nonMergeableGateCases: Array<{
	name: string;
	event: OrchestratorEvent;
	context: Partial<TransitionContext>;
}> = [
	{ name: "CI failure", event: "ci_failed", context: { ciPassed: false } },
	{
		name: "Takumi Guard failure",
		event: "takumi_guard_failed",
		context: { takumiGuardPassed: false },
	},
	{
		name: "content guard failure",
		event: "content_guard_failed",
		context: { contentGuardPassed: false },
	},
	{
		name: "protected branch evidence missing",
		event: "protected_branch_evidence_missing",
		context: { protectedBranchEvidencePresent: false },
	},
];

for (const { name, event, context } of nonMergeableGateCases) {
	test(`F003 ${name} is not mergeable`, () => {
		const result = transition("PROPOSED", event, {
			...baseContext,
			...context,
			allGatesPassed: false,
		});

		assert.notEqual(result.next, "MERGED");
		assert.notEqual(result.actions.includes("squash_merge"), true);
		assert.equal(result.mergeable, false);
	});
}

const cleanupCases: Array<{
	terminal: TerminalState;
	state: "PROPOSED" | "REJECTED";
	event: OrchestratorEvent;
	context: TransitionContext;
}> = [
	{
		terminal: "MERGED",
		state: "PROPOSED",
		event: "reviewer_approved",
		context: baseContext,
	},
	{
		terminal: "ESCALATED",
		state: "REJECTED",
		event: "loop_exhausted",
		context: { ...baseContext, loopCount: 3, allGatesPassed: false },
	},
	{
		terminal: "FAILED",
		state: "PROPOSED",
		event: "fatal_error",
		context: baseContext,
	},
	{
		terminal: "TIMEOUT",
		state: "PROPOSED",
		event: "timeout",
		context: baseContext,
	},
];

for (const { terminal, state, event, context } of cleanupCases) {
	test(`F003 ${terminal} transition includes MCP cleanup`, () => {
		const result = transition(state, event, context);

		assert.equal(result.next, terminal);
		assert.equal(result.actions.includes("cleanup_mcp"), true);
	});
}
