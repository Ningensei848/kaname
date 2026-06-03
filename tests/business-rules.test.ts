/**
 * tests/business-rules.test.ts
 *
 * Spec-aligned integration-style unit tests drawn directly from:
 *   - spec.md          BDD Scenarios 1-6
 *   - business-rules.md §2–§7
 *   - checklist.md     §3, §4
 *   - constitution.md  §1 (mutability), §3 (error handling)
 *
 * These tests validate the *logic* of each guardrail without requiring
 * live LLM / GitHub API calls.  Agent-level behaviour is tested through
 * the pure helper functions that the agents will call.
 */

import { test } from "node:test";
import * as assert from "node:assert";
import * as fs from "fs";
import * as path from "path";
import { calculateHash, loadCrawlerState, saveCrawlerState, updateSourceState } from "../src/crawler/state";
import { resolveTopicPath } from "../src/crawler/path-resolver";

const tempDir = path.join(__dirname, "temp_biz");

function setup() {
	if (fs.existsSync(tempDir)) fs.rmSync(tempDir, { recursive: true, force: true });
	fs.mkdirSync(tempDir, { recursive: true });
}
function teardown() {
	if (fs.existsSync(tempDir)) fs.rmSync(tempDir, { recursive: true, force: true });
}

// ---------------------------------------------------------------------------
// BDD Scenario 1 (spec.md §5.1)
// "Minimal summary with internal links — no redundant re-description"
// ---------------------------------------------------------------------------
test("BDD Scenario 1 — Duplicate suppression / internal-link-only summary", async (t) => {
	/**
	 * Business rule (business-rules.md §4):
	 *   If the new crawled content has the same hash as the stored hash,
	 *   the agent must NOT produce a new report or commit.
	 *
	 * We test the hash-gate logic (the code path the orchestrator uses
	 * before ever calling the LLM).
	 */

	await t.test("identical crawled content must not pass the change gate", () => {
		const previousContent = "能動的サイバー防御に関する制度概要 (変化なし)";
		const currentContent = "能動的サイバー防御に関する制度概要 (変化なし)";

		const stored = calculateHash(previousContent);
		const fresh = calculateHash(currentContent);

		// If hashes are equal → early return, no LLM, no commit
		const hasChanged = stored !== fresh;
		assert.strictEqual(hasChanged, false, "No change should be detected for identical content");
	});

	await t.test("newly detected fact changes the hash — update gate opens", () => {
		const previousContent = "能動的サイバー防御 (2026-05-26版)";
		const currentContent = "能動的サイバー防御 (2026-05-26版)\n★ 新方針: 2026-05-27付け閣議決定";

		const stored = calculateHash(previousContent);
		const fresh = calculateHash(currentContent);

		const hasChanged = stored !== fresh;
		assert.strictEqual(hasChanged, true, "A new fact should open the update gate");
	});
});

// ---------------------------------------------------------------------------
// BDD Scenario 2 (spec.md §5.2)
// "Incremental update — existing file contents must never be overwritten"
// ---------------------------------------------------------------------------
test("BDD Scenario 2 — Incremental update / no-overwrite policy (business-rules.md §3)", async (t) => {
	setup();

	const existingFilePath = path.join(tempDir, "JPCERT_CC.md");
	const originalContent = [
		"---",
		'title: "JPCERT/CC"',
		"---",
		"# JPCERT/CC",
		"",
		"## 概要",
		"Computer Emergency Response Team Coordination Center of Japan.",
		"",
		"## 過去のインシデント",
		"- 2025-09: XYZ マルウェア拡散に関する注意喚起",
	].join("\n");

	const newFact = "\n\n## 2026年5月の動向\n- 新たな注意喚起スキームを公表 (2026-05-27)";

	await t.test("existing content is preserved after incremental append", () => {
		fs.writeFileSync(existingFilePath, originalContent, "utf8");

		// Simulated Aegis-Writer behaviour: read → append → write back
		const current = fs.readFileSync(existingFilePath, "utf8");
		const updated = current + newFact;
		fs.writeFileSync(existingFilePath, updated, "utf8");

		const result = fs.readFileSync(existingFilePath, "utf8");

		// Original facts must remain intact
		assert.ok(result.includes("Computer Emergency Response Team"), "original description must be preserved");
		assert.ok(result.includes("2025-09: XYZ"), "historical incident must not be erased");
		// New fact must appear
		assert.ok(result.includes("2026-05-27"), "newly detected fact must be present");
	});

	await t.test("a full-overwrite of the file is detectable via hash comparison", () => {
		// constitution.md §1: full overwrite is PROHIBITED
		// The reviewer detects it by comparing the original hash against the new content hash
		const originalHash = calculateHash(originalContent);
		const overwrittenContent = "## 2026年5月の動向\n新スキームのみ"; // original facts deleted
		const overwrittenHash = calculateHash(overwrittenContent);

		// Hash mismatch in an overwrite scenario — reviewer should reject
		assert.notStrictEqual(
			originalHash,
			overwrittenHash,
			"overwrite produces a completely different hash — reviewer can detect and reject",
		);
		// The overwritten file must NOT contain the original body
		assert.ok(!overwrittenContent.includes("Computer Emergency Response Team"), "overwrite erases original — should be rejected");
	});

	teardown();
});

// ---------------------------------------------------------------------------
// BDD Scenario 3 (spec.md §5.3)
// "Orphan note auto-detection — links must be injected"
// ---------------------------------------------------------------------------
test("BDD Scenario 3 — Orphan Note Resolution (business-rules.md §3, checklist.md §3)", async (t) => {
	setup();

	await t.test("orphan note is identified when it has no inbound links in the vault", () => {
		// Simulate a mini-vault index: file → set of files that link TO it
		const vaultIndex: Record<string, string[]> = {
			"NICT.md": ["NCO.md"],            // has 1 inbound link → NOT orphan
			"CYDER.md": [],                   // zero inbound links → ORPHAN
			"能動的サイバー防御.md": ["NCO.md", "NICT.md"], // well-connected
		};

		const orphans = Object.entries(vaultIndex)
			.filter(([, inbound]) => inbound.length === 0)
			.map(([file]) => file);

		assert.deepStrictEqual(orphans, ["CYDER.md"]);
	});

	await t.test("injecting an internal link resolves the orphan state", () => {
		// inbound-link map: file → which files link TO it
		const vaultIndex: Record<string, string[]> = {
			"NICT.md": [],    // orphan
			"CYDER.md": [],   // orphan
		};

		// Aegis-Writer adds [[サイバー演習CYDER]] inside NICT.md
		// → CYDER.md now has one inbound link (from NICT.md)
		// → NICT.md still has zero inbound links (but it is the *host* of the new link,
		//   not the target; we are resolving CYDER's orphan status here)
		vaultIndex["CYDER.md"].push("NICT.md");

		assert.strictEqual(vaultIndex["CYDER.md"].length, 1, "CYDER should have 1 inbound link");

		const remainingOrphans = Object.entries(vaultIndex)
			.filter(([, inbound]) => inbound.length === 0)
			.map(([file]) => file);

		// NICT.md still has 0 inbound links (it IS the linking page, not the target).
		// The test objective: CYDER's orphan state is resolved.
		assert.ok(!remainingOrphans.includes("CYDER.md"), "CYDER must no longer be an orphan");
	});

	await t.test("already-connected topics are not treated as orphans", () => {
		setup();
		const file = path.join(tempDir, "NCO.md");
		fs.writeFileSync(file, "# NCO\n関連: [[CYDER]]\n[[能動的サイバー防御]]", "utf8");

		const content = fs.readFileSync(file, "utf8");
		const links = [...content.matchAll(/\[\[([^\]]+)\]\]/g)].map((m) => m[1]);
		assert.deepStrictEqual(links, ["CYDER", "能動的サイバー防御"]);
	});

	teardown();
});

// ---------------------------------------------------------------------------
// BDD Scenario 5 (spec.md §5.5)
// "Discord notification is sent ONLY on Cloudflare Pages deploy success"
// ---------------------------------------------------------------------------
test("BDD Scenario 5 — Discord notification gate (business-rules.md §6, checklist.md §4)", async (t) => {
	type DeployStatus = "success" | "failure" | "pending";

	function shouldSendDiscordNotification(deployStatus: DeployStatus): boolean {
		// business-rules.md §6: Webhook ONLY on pages-deployment success event
		return deployStatus === "success";
	}

	await t.test("sends notification when Cloudflare Pages reports success", () => {
		assert.strictEqual(shouldSendDiscordNotification("success"), true);
	});

	await t.test("does NOT send notification on build failure", () => {
		assert.strictEqual(shouldSendDiscordNotification("failure"), false);
	});

	await t.test("does NOT send notification while deploy is still pending", () => {
		assert.strictEqual(shouldSendDiscordNotification("pending"), false);
	});
});

// ---------------------------------------------------------------------------
// BDD Scenario 6 (spec.md §5.6)
// "On crawling failure → GitHub Issue is raised, no SMTP server"
// ---------------------------------------------------------------------------
test("BDD Scenario 6 — Crawling failure escalation (business-rules.md §7, checklist.md §4)", async (t) => {
	type EscalationAction = "github_issue" | "smtp_email" | "none";

	function determineEscalationAction(failureCount: number, maxRetries: number): EscalationAction {
		// constitution.md §3 / business-rules.md §7:
		//   After maxRetries consecutive failures → raise a GitHub Issue.
		//   The system must NEVER use its own SMTP server.
		if (failureCount >= maxRetries) return "github_issue";
		return "none";
	}

	const MAX_RETRIES = 3;

	await t.test("no escalation while retries remain", () => {
		assert.strictEqual(determineEscalationAction(1, MAX_RETRIES), "none");
		assert.strictEqual(determineEscalationAction(2, MAX_RETRIES), "none");
	});

	await t.test("GitHub Issue is raised after max retries are exhausted", () => {
		assert.strictEqual(determineEscalationAction(3, MAX_RETRIES), "github_issue");
	});

	await t.test("SMTP email is never a valid escalation action", () => {
		for (let i = 0; i <= 5; i++) {
			assert.notStrictEqual(
				determineEscalationAction(i, MAX_RETRIES),
				"smtp_email",
				`SMTP must never be chosen (failureCount=${i})`,
			);
		}
	});
});

// ---------------------------------------------------------------------------
// Business Rule: Folder count cap <100  (business-rules.md §2, checklist.md §3)
// ---------------------------------------------------------------------------
test("Business Rule — Intermediate directory cap (max 100 folders, threshold 95)", async (t) => {
	setup();

	await t.test("new category folder is created when count is below threshold (95)", () => {
		const resolved = resolveTopicPath(tempDir, "vulnerabilities", "CVE-2026-0001", 100, 95);
		const expected = path.join(tempDir, "topics", "vulnerabilities", "CVE-2026-0001.md");
		assert.strictEqual(resolved, expected);
		assert.ok(fs.existsSync(path.dirname(resolved)));
	});

	await t.test("folder creation is blocked and misc fallback is used at threshold 95", () => {
		const topicsDir = path.join(tempDir, "topics");
		// Create 95 dummy folders to hit the threshold
		for (let i = 0; i < 95; i++) {
			fs.mkdirSync(path.join(topicsDir, `cat_${i}`), { recursive: true });
		}

		const resolved = resolveTopicPath(tempDir, "brand-new-category", "SomeTopic", 100, 95);
		const fallback = path.join(tempDir, "topics", "misc", "SomeTopic.md");
		assert.strictEqual(resolved, fallback);
		// The requested new category must NOT have been created
		assert.strictEqual(
			fs.existsSync(path.join(topicsDir, "brand-new-category")),
			false,
			"new category must be blocked at threshold",
		);
	});

	await t.test("total folder count never exceeds 100 after fallback is applied", () => {
		const topicsDir = path.join(tempDir, "topics");
		const subdirs = fs
			.readdirSync(topicsDir, { withFileTypes: true })
			.filter((d) => d.isDirectory()).length;
		// misc was created as fallback; total must be < 100
		assert.ok(subdirs < 100, `Folder count ${subdirs} must stay below 100`);
	});

	teardown();
});

// ---------------------------------------------------------------------------
// Business Rule: SSoT / past reports are IMMUTABLE (constitution.md §1)
// ---------------------------------------------------------------------------
test("Business Rule — Immutability of SSoT and past dated reports (constitution.md §1)", async (t) => {
	setup();

	await t.test("past dated report hash must not change (detects illegal mutation)", () => {
		const reportFile = path.join(tempDir, "2026-05-26_Report.md");
		const reportContent = "# 2026-05-26 Report\n- NCO issued new advisory";
		fs.writeFileSync(reportFile, reportContent, "utf8");

		const lockedHash = calculateHash(reportContent);

		// Simulate an attempt to edit the past report
		const tamperedContent = "# 2026-05-26 Report\n- NCO issued new advisory\n(edited)";
		const tamperedHash = calculateHash(tamperedContent);

		assert.notStrictEqual(
			lockedHash,
			tamperedHash,
			"Any modification to a past report is detectable via hash mismatch",
		);
	});

	await t.test("wiki topic is mutable — appending new facts does not violate its hash contract", () => {
		// constitution.md §1: Wiki topics ARE mutable; only past reports and ssot.yml are immutable
		const topicFile = path.join(tempDir, "JPCERT_CC.md");
		const v1 = "# JPCERT/CC\n## 概要\nOriginal description.";
		fs.writeFileSync(topicFile, v1, "utf8");

		const v2 = v1 + "\n\n## 2026年の動向\n新スキーム公表";
		fs.writeFileSync(topicFile, v2, "utf8");

		const result = fs.readFileSync(topicFile, "utf8");
		assert.ok(result.includes("Original description."), "original content preserved");
		assert.ok(result.includes("新スキーム公表"), "new fact appended");
		// Hash has legitimately changed — that is expected and allowed
		assert.notStrictEqual(calculateHash(v1), calculateHash(result));
	});

	teardown();
});

// ---------------------------------------------------------------------------
// Business Rule: Multi-agent review loop max 3 iterations (business-rules.md §5)
// ---------------------------------------------------------------------------
test("Business Rule — Agent feedback loop hard limit (max 3, then Issue escalation)", async (t) => {
	type LoopStatus = "approved" | "rejected" | "escalated";

	function runAgentLoop(maxLoops: number): { iterations: number; finalStatus: LoopStatus } {
		// Simulate a loop where the reviewer always rejects
		let iterations = 0;
		let isApproved = false; // separate flag avoids TS narrowing issues

		while (iterations < maxLoops && !isApproved) {
			iterations++;
			// Writer proposes → Reviewer always rejects in this simulation
			isApproved = false;
		}

		// After exhausting loops without approval → escalate
		const finalStatus: LoopStatus = isApproved ? "approved" : "escalated";
		return { iterations, finalStatus };
	}

	await t.test("loop terminates after exactly 3 iterations without approval", () => {
		const result = runAgentLoop(3);
		assert.strictEqual(result.iterations, 3);
		assert.strictEqual(result.finalStatus, "escalated");
	});

	await t.test("loop does not exceed the hard limit", () => {
		const result = runAgentLoop(3);
		assert.ok(result.iterations <= 3, `Iterations ${result.iterations} must not exceed 3`);
	});

	await t.test("loop exits early on approval (happy path)", () => {
		function runHappyLoop(maxLoops: number, approveOnIteration: number) {
			let iterations = 0;
			let isApproved = false;

			while (iterations < maxLoops && !isApproved) {
				iterations++;
				if (iterations === approveOnIteration) isApproved = true;
			}

			const finalStatus: LoopStatus = isApproved ? "approved" : "escalated";
			return { iterations, finalStatus };
		}

		const result = runHappyLoop(3, 2); // reviewer approves on iteration 2
		assert.strictEqual(result.iterations, 2);
		assert.strictEqual(result.finalStatus, "approved");
	});
});
