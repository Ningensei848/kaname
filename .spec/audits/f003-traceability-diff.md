# F003 traceability diff proposal

This document is the parallel-lane output for **P3. F003 traceability diff proposal**. It is a planning artifact only: it does not add production orchestration, MCP process management, GitHub authentication, merge, or child-process cleanup logic under `src/`.

## Reference basis

- Working branch when prepared: `p3-f003-traceability-diff`
- Local baseline used because `origin` / `origin/main` is unavailable in this workspace: `bc504a9cc48def07631b37b76dcd6310e506b2bf`
- Feature spec source: `.spec/features/003-orchestrator-mcp-review-loop/spec.md`
- Acceptance source: `.spec/features/003-orchestrator-mcp-review-loop/acceptance.md`
- MCP contract source: `.spec/contracts/mcp-contracts.md`
- Current traceability rows: `.spec/traceability.md`
- Current `src/` phase boundary source: `.spec/audits/src-phase-boundary-inventory.md`

## F003 scope recap

F003 covers the deterministic orchestrator / MCP review loop. In the current phase, F003 should be represented through explicit transition tables, JSON-RPC fixtures, fail-closed contract tables, test-local lifecycle models, and type-only boundaries. Production orchestration, GitHub App token exchange runtime, MCP stdio process management, Reviewer aggregation, and protected merge execution remain after the implementation gate.

F003 requirements under review:

1. Orchestrator max-3 review loop.
2. MCP process lifecycle cleanup.
3. GitHub App JWT / installation token flow.
4. MCP JSON-RPC contracts.
5. Protected merge preconditions.

## Existing executable evidence

| Evidence | Current role | Current-phase interpretation |
| --- | --- | --- |
| `.spec/contracts/mcp-contracts.md` | Source contract for GitHub MCP JSON-RPC tool envelopes | Spec / policy input for `fixture-contract` |
| `tests/fixtures/f003/mcp/valid/*.json` | Canonical valid MCP tool-call fixtures | `fixture-contract` |
| `tests/fixtures/f003/mcp/invalid/*.json` | Canonical invalid branch/path/merge-gate fixtures | `fixture-contract` |
| `tests/f003-mcp-contract-fixtures.test.ts` | Executable fixture validation and fail-closed MCP policy checks | `fixture-contract`; includes legacy `src` value imports that need inventory |
| `tests/f003-orchestrator-state-table.test.ts` | Explicit transition-table tests for orchestrator state/event/action records | `test-model` plus possible `type-boundary`; imports transition runtime from `src` today |
| `tests/f003-mcp-lifecycle.test.ts` | Deterministic fake child-process lifecycle harness | `test-model`; real OS signal integration remains guarded backlog |
| `tests/f003-github-installation-token.test.ts` | JWT lifetime, installation token exchange, and safe error tests | `planned-src-unit`; currently imports production auth runtime |
| `tests/github-auth.test.ts` | Legacy JWT generation unit tests | `planned-src-unit`; currently imports production crypto/JWT runtime |
| `tests/f003-tool-policy.test.ts` | Tool policy, merge precondition, and orchestrator merge-flow tests | Mixed `fixture-contract`, `test-model`, and legacy production value imports |
| `tests/orchestrator.test.ts` | Transition-sequence contract plus legacy `AegisOrchestrator` integration-flow tests | `test-model` for transition sequences; `planned-src-integration` for runtime orchestrator imports |
| `tests/contracts.test.ts` | Cross-feature MCP / protected merge / Takumi Guard contract tests | Cross-cutting `fixture-contract`; value imports require inventory |

## `src/` phase-boundary mapping for F003

| `src` file | Boundary classification | F003 relevance | Current-phase traceability treatment |
| --- | --- | --- | --- |
| `src/orchestrator.ts` | Split | Orchestrator contracts plus runtime orchestration, crawling, MCP, and state-conflict behavior | Keep exported types/interfaces as `type-boundary`; runtime `AegisOrchestrator`, `runOrchestration`, merge checks, and escalation logic are `planned-src-integration` |
| `src/orchestrator/state-machine.ts` | Split | State/event/action literal unions and transition records plus transition implementation | Keep literal unions and record shapes as `type-boundary`; `transition` behavior is `test-model` now and `planned-src-unit` after the gate |
| `src/mcp/tool-policy.ts` | Split | MCP call, gate, and argument contracts plus policy validation runtime | Keep JSON/tool/gate declarations as `type-boundary`; validation execution is `planned-src-unit` unless expressed via external fixtures |
| `src/policies/mcp-write-policy.ts` | Not listed in the current boundary inventory | Writer path allowlist policy imported by tests | Add to the later `src` boundary inventory before claiming current-phase status; treat current imports as cross-cutting policy inventory inputs |
| `src/auth/github-auth.ts` | Split | GitHub installation-token types plus JWT generation and token exchange runtime | Keep token response/options/fetch contracts as `type-boundary`; crypto and network exchange behavior is `planned-src-unit` |

## Proposed `.spec/traceability.md` F003 row changes

The table below is a proposed replacement for the current F003 rows when the serial traceability integration task runs.

| Requirement | Existing / target code | Existing / target tests | Proposed coverage depth | Proposed status | Proposed notes |
| --- | --- | --- | --- | --- | --- |
| Orchestrator max-3 review loop | Transition table contract from `.spec/features/003-orchestrator-mcp-review-loop/spec.md`; type boundary from `src/orchestrator/state-machine.ts`; runtime orchestrator after gate | `tests/f003-orchestrator-state-table.test.ts`; transition-sequence portions of `tests/orchestrator.test.ts` | `test-model` | partial | Explicit state/event/action behavior is modeled, but `src/orchestrator.ts` runtime orchestration is a split candidate and must not be counted as completed `src-unit`. |
| MCP process lifecycle cleanup | Test-local lifecycle model now; future `McpClient` / child-process adapter boundary after gate | `tests/f003-mcp-lifecycle.test.ts`; guarded OS signal backlog in `tests/integration/backlog.integration.ts` | `test-model` | partial | Fake child-process lifecycle coverage is deterministic. Real SIGTERM / stdio resource cleanup belongs to explicit integration backlog and production implementation later. |
| GitHub App JWT / installation token flow | Type boundary from `src/auth/github-auth.ts`; MCP launcher env mapping contract still pending | `tests/github-auth.test.ts`; `tests/f003-github-installation-token.test.ts` | `planned-src-unit` | planned | Tests import crypto/network auth runtime from `src`. Current-phase credit should be limited to token contract types and red/contract expectations; MCP launcher `GITHUB_TOKEN_FOR_MCP` wiring is still spec backlog. |
| MCP JSON-RPC contracts | External JSON-RPC fixtures from `.spec/contracts/mcp-contracts.md`; type boundary from `src/mcp/tool-policy.ts` after split | `tests/f003-mcp-contract-fixtures.test.ts`; `tests/contracts.test.ts`; valid/invalid fixtures under `tests/fixtures/f003/mcp/` | `fixture-contract` | partial | External fixtures and fail-closed tables are valid current-phase coverage. Production builders/validators should remain planned until runtime exports are split. |
| Protected merge preconditions | Fixture-level merge gate evidence and cross-feature F002 verdict artifact contract; production Reviewer aggregation after gate | `tests/f003-mcp-contract-fixtures.test.ts`; `tests/f003-tool-policy.test.ts`; `tests/contracts.test.ts` | `fixture-contract` | partial | Merge calls fail closed in fixture/policy tests, but protected branch operations, CI/Takumi/content aggregation, and Reviewer execution remain `planned-src-integration`. |

## Value-import follow-up items for P5

The following F003 and cross-cutting imports should be included in `.spec/audits/test-src-value-import-inventory.md`:

| Test file | Imported `src` file | Runtime identifiers requiring classification | Suggested classification |
| --- | --- | --- | --- |
| `tests/orchestrator.test.ts` | `../src/orchestrator` | `AegisOrchestrator` | Legacy production value import; classify as `planned-src-integration` or quarantine until implementation gate |
| `tests/orchestrator.test.ts` | `../src/orchestrator` | `DiffResult` | Type-only; retain as `type-boundary` if source file is split cleanly |
| `tests/orchestrator.test.ts` | `../src/orchestrator/state-machine` | `transition`, transition record helpers/types | Runtime `transition` is `planned-src-unit`; literal unions/records can remain `type-boundary` |
| `tests/orchestrator.test.ts` | `../src/mcp/tool-policy` | `allGreenMergePreconditions` | Legacy value import; classify as `planned-src-unit` unless replaced by fixture/table oracle |
| `tests/f003-orchestrator-state-table.test.ts` | `../src/orchestrator/state-machine` | `transition` and state-machine contracts | Split runtime function from type/literal boundary; keep table as `test-model` |
| `tests/f003-mcp-contract-fixtures.test.ts` | `../src/mcp/tool-policy` | `validateToolPolicy`, merge/policy validators | Fixture contract plus legacy value import; keep external fixtures authoritative and classify runtime validator as `planned-src-unit` |
| `tests/f003-mcp-contract-fixtures.test.ts` | `../src/policies/mcp-write-policy` | `isAllowedMcpWriterPath` | Add file to boundary inventory; classify as cross-cutting policy runtime import until reviewed |
| `tests/f003-tool-policy.test.ts` | `../src/mcp/tool-policy` | `validateToolPolicy`, merge precondition helpers | Legacy production value import; convert to contract table or mark `planned-src-unit` |
| `tests/f003-tool-policy.test.ts` | `../src/orchestrator` | `DiffResult` | Type-only; retain as boundary after split |
| `tests/f003-github-installation-token.test.ts` | `../src/auth/github-auth` | `generateGitHubAppJwt`, `exchangeJwtForInstallationToken` and related runtime errors | `planned-src-unit`; keep token response/options/fetch types as boundary only |
| `tests/github-auth.test.ts` | `../src/auth/github-auth` | `generateGitHubAppJwt` | Legacy production value import; classify as `planned-src-unit` |
| `tests/contracts.test.ts` | `../src/mcp/tool-policy` | merge/tool policy helpers | Cross-cutting fixture-contract plus legacy runtime import; inventory before assigning F003 completion credit |
| `tests/contracts.test.ts` | `../src/policies/mcp-write-policy` | `isAllowedMcpWriterPath` | Add to boundary inventory and classify policy import separately |

## Recommended next integration actions

1. During the serial traceability update, replace F003 `src-unit` / `prototype` depth with the proposed current-phase depths above.
2. Keep external MCP fixtures and explicit transition tables as valid current-phase evidence, but avoid treating imported runtime validators/orchestrators as production completion.
3. Add `src/policies/mcp-write-policy.ts` to the `src` phase-boundary inventory before the final traceability integration, because F003 and cross-cutting tests import it today.
4. Keep real OS signal / child-process cleanup in the integration backlog behind explicit environment guards.
5. Do not add production orchestration, GitHub network/auth, MCP stdio, protected-merge, or child-process lifecycle implementation under `src/` for F003 in the current phase.
