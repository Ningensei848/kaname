# `test.todo` Classification Rule

Residual `test.todo` entries are not allowed to remain in feature test files without being moved into one of the destinations below.

## Classification destinations

1. **Red contract test**
   - Use when the expectation is deterministic and can be expressed with local fixtures, schemas, injected fakes, or exact expected values.
   - Replace the `test.todo` with an executable `node:test` test in the owning feature test file.
   - The test must not require real OS signals, cloud credentials, GitHub / Discord / Cloudflare access, or nondeterministic network calls.

2. **Integration backlog**
   - Use when the expectation requires real OS signal handling, external credentials, live Cloudflare / Discord / GitHub connectivity, or pre-built artifacts that are absent from default local and CI runs.
   - Move it under `tests/integration/`.
   - Add an explicit environment-variable guard so default local and CI test runs do not hit external services or artifact preconditions accidentally.
   - Artifact-precondition integration guards are distinct from live credential guards; for example, Quartz `public/` artifact assertions require `KANAME_RUN_QUARTZ_ARTIFACT_INTEGRATION`, but no Cloudflare or Discord credentials.

3. **Spec backlog**
   - Use when the behavior is still too ambiguous to make a red contract test without inventing implementation details.
   - Move it to the owning `.spec/features/*/tasks.md` file, or to `.spec/traceability.md` when the item spans multiple features.
   - The task text must preserve the intended safety invariant and name the missing design decision.

## Classification of the removed residual TODOs

| Source TODO | Classification | Destination |
| --- | --- | --- |
| F002 guards are extracted from test prototypes into pure `src/guards` functions with identical fixture verdicts | Spec backlog | `.spec/features/002-wiki-incremental-update/tasks.md`; current tests lock fixture verdicts without production value imports |
| F002 Aegis-Reviewer merge preconditions consume deterministic content guard verdicts before `merge_pull_request` | Spec backlog | `.spec/features/002-wiki-incremental-update/tasks.md` and `.spec/features/003-orchestrator-mcp-review-loop/tasks.md` |
| F001 crawler state uses a `StateBackendAdapter` abstraction rather than direct filesystem coupling | Red contract test | Existing F001 state backend tests and traceability entry |
| F001 GCS backend contract rejects stale generation writes and maps conflicts to safe escalation or retry policy | Red contract test | `tests/f001-idempotency-contract.test.ts` GCS conflict test |
| F003 GitHub App JWT is exchanged for an installation access token via an injectable fetch boundary | Red contract test | `tests/f003-github-installation-token.test.ts` exchange tests |
| F003 installation token exchange failures produce safe degraded operation metadata for Issue escalation | Spec backlog | `.spec/features/003-orchestrator-mcp-review-loop/tasks.md` |
| F001 Cloud Storage production adapter maps generation-precondition failures to safe degraded operation | Red contract test | `tests/f001-idempotency-contract.test.ts` GCS conflict test |
| F001 unchanged source guard records zero `create_or_update_file` and zero `create_pull_request` MCP calls in replay fixtures | Red contract test | `tests/f001-idempotency-contract.test.ts` unchanged replay MCP-call test |
| F002 production deterministic guard module exports the same verdicts as executable fixtures | Spec backlog | `.spec/features/002-wiki-incremental-update/tasks.md`; current tests lock executable fixture verdicts only |
| F002 CI wires no-overwrite, frontmatter, link graph, orphan, and duplicate guards before Reviewer approval | Spec backlog | `.spec/features/002-wiki-incremental-update/tasks.md` |
| F003 MCP launcher passes installation token as `GITHUB_TOKEN_FOR_MCP` and never uses PAT | Spec backlog | `.spec/features/003-orchestrator-mcp-review-loop/tasks.md` |
| F003 production MCP client loads and validates external fixtures before real tool calls | Red contract test | `tests/f003-mcp-contract-fixtures.test.ts` production MCP policy fixture test |
| F003 Writer path policy adds generated index paths only after the feature plan explicitly lists their exact locations | Red contract test | `tests/f003-mcp-contract-fixtures.test.ts` generated-index rejection test |
| F003 AegisOrchestrator wires real MCP child cleanup to DONE/MERGED/ESCALATED/FAILED/SIGTERM/TIMEOUT | Spec backlog | `.spec/features/003-orchestrator-mcp-review-loop/tasks.md` |
| F003 integration test spawns a real dummy child process and verifies `process.on('SIGTERM')` cleanup over actual OS signals and stdio resources | Integration backlog | `tests/integration/backlog.integration.ts` guarded by `KANAME_RUN_PROCESS_SIGNAL_INTEGRATION` |
| F004 production notification module uses external state backend family, not Git, for duplicate deployment notification state | Red contract test | `tests/f004-cloudflare-discord.test.ts` injected notification backend tests |
| F004 integration tests live under `tests/integration/` and may use real Cloudflare/Discord only behind explicit credentials | Integration backlog | `tests/integration/backlog.integration.ts` guarded by Cloudflare / Discord environment variables |

## Production migration TODO policy after Phase 2

Phase 2 completion means the contract evidence is complete; it is not a declaration that Phase 3 production runtime work is complete. TODOs that migrate contract evidence into runtime code must be written at the production boundary where the next implementer can start immediately.

### Required production migration TODO granularity

- **Runtime schema validation:** name the exact external input, canonical `.spec/schemas/*` schema, production `src/` boundary, and fail-closed result expected before downstream logic consumes data.
- **MCP call validation:** name the exact MCP tool-call shape/policy invariant, the production client or adapter boundary that must enforce it, and the side effect that must be blocked before validation passes.
- **External API adapters:** name the external service, injected dependency boundary, timeout/malformed/non-2xx behavior, retry or escalation policy, and idempotency/state backend expectation.
- **Live/integration checks:** keep real credentials, OS signals, and pre-built artifact checks under guarded `tests/integration/` entries with explicit `KANAME_RUN_*` flags.

### Separate coverage-threshold task

Coverage threshold enforcement must remain a separate PR/task from the production bridge TODOs. Do not use coverage thresholds as a substitute for moving fixture contracts into production validation/adapters; add thresholds only after those production modules exist and traceability can distinguish measured runtime coverage from Phase 2 fixture-contract evidence.
