/**
 * F003 fake MCP lifecycle harness.
 *
 * This file intentionally avoids real OS signals, real child processes, and
 * stdio resource assertions. Real process coverage belongs in the Phase 2
 * integration backlog.
 */

import * as assert from "node:assert";
import { test } from "node:test";

import type { TerminalState } from "../src/orchestrator/state-machine";

type FakeLifecycleReason = TerminalState | "SIGTERM";

class FakeMcpLifecycleHarness {
	public started = false;
	public cleanupCalls: FakeLifecycleReason[] = [];

	public start(): void {
		this.started = true;
	}

	public cleanup(reason: FakeLifecycleReason): void {
		if (!this.started || this.cleanupCalls.length > 0) return;
		this.cleanupCalls.push(reason);
	}
}

test("F003 fake lifecycle harness records idempotent cleanup reasons", () => {
	const lifecycle = new FakeMcpLifecycleHarness();
	lifecycle.start();

	lifecycle.cleanup("MERGED");
	lifecycle.cleanup("FAILED");

	assert.deepEqual(lifecycle.cleanupCalls, ["MERGED"]);
});

test("F003 fake lifecycle harness covers terminal cleanup reasons without real processes", () => {
	for (const reason of [
		"DONE",
		"MERGED",
		"ESCALATED",
		"FAILED",
		"TIMEOUT",
	] as const) {
		const lifecycle = new FakeMcpLifecycleHarness();
		lifecycle.start();

		lifecycle.cleanup(reason);

		assert.deepEqual(lifecycle.cleanupCalls, [reason]);
	}
});
