/**
 * Phase 2 implementation backlog captured as executable TODO tests.
 *
 * These TODOs intentionally do not implement production code. They translate
 * reviewer feedback into a precise, test-visible backlog for the implementation
 * agent while preserving the architecture rule that `src/` stays limited to
 * type and contract definitions. Concrete guard behavior belongs in test
 * harnesses, fixtures, schemas, or a future separate runtime package.
 */

import { test } from "node:test";

test.todo(
	"F002 guards are promoted from test prototypes into contract-backed harnesses or a future guard package with identical fixture verdicts",
);

test.todo(
	"F002 Aegis-Reviewer merge preconditions consume deterministic content guard verdicts before merge_pull_request",
);

test.todo(
	"F001 crawler state uses a StateBackendAdapter abstraction rather than direct filesystem coupling",
);

test.todo(
	"F001 GCS backend contract rejects stale generation writes and maps conflicts to safe escalation or retry policy",
);

test.todo(
	"F003 GitHub App JWT is exchanged for an installation access token via an injectable fetch boundary",
);

test.todo(
	"F003 installation token exchange failures produce safe degraded operation metadata for Issue escalation",
);
