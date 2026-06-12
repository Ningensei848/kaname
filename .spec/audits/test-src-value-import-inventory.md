# `tests/` to `src/` value import inventory

This inventory is the parallel-lane output for **P5. `tests → src` value import inventory**. It is a planning artifact only: it does not change production code, does not rewrite tests, and does not promote runtime imports from `src/` to current-phase completion evidence.

## Reference basis

- Working branch when prepared: `p5-test-src-value-import-inventory`
- Local baseline: `d4b6b52` (`Add F001–F004 traceability diff proposals`)
- Discovery command: `rg -n "^import .* from ['\"]\.\./src|^import \{[\s\S]*?\} from ['\"]\.\./src|from ['\"]\.\./src" tests --glob '*.ts'`
- Boundary source: `.spec/audits/src-phase-boundary-inventory.md`
- Feature diff sources: `.spec/audits/f001-traceability-diff.md`, `.spec/audits/f002-traceability-diff.md`, `.spec/audits/f003-traceability-diff.md`, and `.spec/audits/f004-traceability-diff.md`

## Classification legend

| Column | Meaning |
| --- | --- |
| Type-only? | Whether the import is already type-only or can become type-only after splitting runtime exports away. |
| Contract replacement | Whether the test should prefer fixture, schema, contract table, or test-local oracle coverage in the current phase. |
| Quarantine? | Whether the test currently depends on production runtime implementation and should be moved to a legacy production suite if it remains unchanged. |
| Integration backlog? | Whether the behavior needs live services, OS/process behavior, generated artifacts, or multi-module production orchestration. |

## Inventory

| Feature | Test file | Imported `src` file | Runtime identifier(s) imported | Boundary classification | Type-only? | Contract replacement | Quarantine? | Integration backlog? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F001 | `tests/parser.test.ts` | `src/crawler/parser.ts` | `parseSsotYaml` | Evacuate | No | Replace with SSoT schema / fixture contract for current phase | Yes, if retained unchanged | No |
| F001 | `tests/fetch.test.ts` | `src/crawler/fetch.ts` | `fetchWithRetry`, `cleanHtml`, `parseRssFeed` | Split | No; only `Fetcher`/result contracts should remain type boundary | Replace retry / parser expectations with fixture or test-local oracle until implementation gate | Yes, if retained unchanged | Network retry behavior may become planned integration later |
| F001 | `tests/state.test.ts` | `src/crawler/state.ts` | `calculateHash`, `loadCrawlerState`, `saveCrawlerState`, `updateSourceState` | Split | No; adapter/snapshot declarations can become type-only | Replace state shape checks with crawler-state schema / fixtures; keep hash/mutation as planned source unit | Yes, if retained unchanged | Filesystem state IO may move to integration/backlog after gate |
| F001 | `tests/state-backends-gcs.test.ts` | `src/crawler/state.ts` | `StateConflictError` | Split | No | Replace conflict shape with test-local conflict oracle or shared contract type | Yes | GCS adapter behavior is planned integration with fake fetch first |
| F001 | `tests/state-backends-gcs.test.ts` | `src/crawler/state-backends/gcs.ts` | `GcsStateBackend` | Split | No; `FetchLike` is type-only | Keep options/fetch boundary only; move class behavior to planned-src-integration | Yes | Yes, for Cloud Storage adapter semantics |
| F001 | `tests/f001-idempotency-contract.test.ts` | `src/crawler/state-errors.ts` | `StateConflictError` | Evacuate | No | Replace with test-local stale-generation conflict shape | Yes, if retained unchanged | No |
| F001 | `tests/f001-idempotency-contract.test.ts` | `src/crawler/state-backends/gcs.ts` | `GcsStateBackend` | Split | No | Keep fake object-store and schema fixture contract as current evidence | Yes, for production class import | Yes, for external backend implementation |
| F001 | `tests/f001-idempotency-contract.test.ts` | `src/orchestrator.ts` | None; `DiffResult`, `OrchestratorDependencies` are type-only | Split | Already type-only | Retain as type-boundary if `src/orchestrator.ts` is split cleanly | No | No |
| F001 | `tests/f001-idempotency-contract.test.ts` | `src/types.ts` | None; `CrawlerState` is type-only | Keep candidate; file is interface-only | Already type-only | Retain as schema-derived type boundary | No | No |
| F001 | `tests/f001-crawler-failure-escalation.test.ts` | `src/orchestrator.ts` | `crawlSourcesWithFailureEscalation` | Split | No | Replace with test-local failure/escalation oracle for current phase | Yes | Yes, for production orchestration / MCP Issue flow |
| F001 | `tests/f001-crawler-failure-escalation.test.ts` | `src/crawler/fetch.ts` | None; `Fetcher` is type-only | Split | Already type-only | Retain as injected fetch boundary type | No | No |
| F001 | `tests/f001-crawler-failure-escalation.test.ts` | `src/crawler/state.ts` | `StateConflictError` | Split | No | Replace with test-local conflict shape or planned state error boundary | Yes | No |
| F001 | `tests/f001-crawler-failure-escalation.test.ts` | `src/types.ts` | None; `CrawlerState`, `SsotSource` are type-only | Keep candidate; file is interface-only | Already type-only | Retain as schema-derived type boundary | No | No |
| F001/F002 | `tests/business-rules.test.ts` | `src/crawler/state.ts` | `calculateHash` | Split | No | Replace idempotency assertion with test-local hash oracle or schema fixture evidence | Yes | No |
| Cross-cutting/F002 | `tests/business-rules.test.ts` | `src/crawler/path-resolver.ts` | `resolveTopicPath` | Evacuate | No | Replace path rules with fixture table or move to legacy production suite | Yes | Filesystem/path behavior may become integration after gate |
| F002 | `tests/business-rules.test.ts` | `src/utils/markdown-updater.ts` | `appendSectionToMarkdown`, `injectInternalLinkToMarkdown` | Evacuate | No | Prefer F002 fixture verdict contract / test-local oracle | Yes | No |
| F002 | `tests/markdown-updater.test.ts` | `src/utils/markdown-updater.ts` | `appendSectionToMarkdown`, `injectInternalLinkToMarkdown` | Evacuate | No | Convert to fixture/test-local oracle or keep as planned-src-unit | Yes | No |
| Cross-cutting/F001 | `tests/path-resolver.test.ts` | `src/crawler/path-resolver.ts` | `resolveTopicPath`, `sanitizeName` | Evacuate | No | Convert to path contract table / fixture oracle or legacy suite | Yes | Filesystem directory-limit behavior may become integration after gate |
| F003 | `tests/orchestrator.test.ts` | `src/mcp/tool-policy.ts` | `allGreenMergePreconditions` | Split | No | Replace with local all-green gate fixture/table for current phase | Yes | No |
| F003 | `tests/orchestrator.test.ts` | `src/orchestrator.ts` | `AegisOrchestrator`; `DiffResult` is type-only | Split | Mixed; `DiffResult` can remain type-only | Keep transition-sequence oracle; move class integration to planned-src-integration | Yes, for `AegisOrchestrator` | Yes, for production orchestration |
| F003 | `tests/orchestrator.test.ts` | `src/orchestrator/state-machine.ts` | `transition`; state/event/context imports are type-only | Split | Mixed; literal unions/records can remain type-only | Keep explicit transition table as test-model; runtime function is planned-src-unit | Yes, for runtime function import | No |
| F003 | `tests/f003-orchestrator-state-table.test.ts` | `src/orchestrator/state-machine.ts` | `transition`; state/event/context/result imports are type-only | Split | Mixed | Keep table as current test-model; split literal contracts from runtime function | Yes, for runtime function import | No |
| F003 | `tests/f003-github-installation-token.test.ts` | `src/auth/github-auth.ts` | `exchangeJwtForInstallationToken`, `generateGitHubAppJwt`; `GitHubInstallationTokenFetch` is type-only | Split | Mixed | Keep token response/fetch contracts; runtime crypto/network exchange is planned-src-unit | Yes | GitHub App exchange is integration only with explicit fake/live boundary |
| F003 | `tests/github-auth.test.ts` | `src/auth/github-auth.ts` | `generateGitHubAppJwt` | Split | No | Keep JWT shape/lifetime as contract expectation; runtime crypto stays planned-src-unit | Yes | No live GitHub required; live auth remains backlog |
| F003 | `tests/f003-mcp-contract-fixtures.test.ts` | `src/mcp/tool-policy.ts` | `allGreenMergePreconditions`, `validateToolPolicy`; `PolicyMcpToolCall` is type-only | Split | Mixed | External JSON fixtures should remain authoritative; runtime validator is planned-src-unit | Yes, for runtime validator | No |
| F003 | `tests/f003-mcp-contract-fixtures.test.ts` | `src/policies/mcp-write-policy.ts` | `isAllowedMcpWriterPath` | Missing from boundary inventory | No | Add file to boundary inventory; replace with fixture allowlist table if needed | Yes, until classified | No |
| F003 | `tests/f003-tool-policy.test.ts` | `src/mcp/tool-policy.ts` | None; `MergePreconditions`, `PolicyMcpToolCall` are type-only | Split | Already type-only | Retain as type-boundary if runtime imports are not added | No | No |
| F003 | `tests/f003-tool-policy.test.ts` | `src/orchestrator.ts` | None; `DiffResult` is type-only | Split | Already type-only | Retain as type-boundary if source file is split cleanly | No | No |
| F003/Cross-cutting | `tests/contracts.test.ts` | `src/mcp/tool-policy.ts` | `allGreenMergePreconditions`, `validateToolPolicy`; `MergePreconditions` is type-only | Split | Mixed | Prefer MCP fixture contract / fail-closed table in current phase | Yes, for runtime validators | No |
| F003/Cross-cutting | `tests/contracts.test.ts` | `src/policies/mcp-write-policy.ts` | `isAllowedMcpWriterPath` | Missing from boundary inventory | No | Add file to boundary inventory; replace with policy fixture table if needed | Yes, until classified | No |
| F004 | `tests/f004-cloudflare-discord.test.ts` | `src/notifications/cloudflare-discord.ts` | `evaluateAndPersistNotification`, `GenerationMismatchError`; deployment/state/retry/probe imports are type-only | Split | Mixed | Keep Cloudflare/Discord schema fixtures and test-local oracle as current evidence | Yes, for runtime decision/persistence imports | Yes, for real Cloudflare/Discord and durable backend behavior |

## Feature roll-up

| Feature | Current-phase safe imports | Runtime imports requiring action | Primary destination |
| --- | --- | --- | --- |
| F001 | `Fetcher`, `CrawlerState`, `SsotSource`, `DiffResult`, `OrchestratorDependencies` if kept type-only | Parser, fetch runtime, state hash/IO/mutation, GCS class, conflict error classes, crawler orchestration | Schema/fixture contracts now; legacy quarantine or planned-src-unit/integration later |
| F002 | None from production runtime in `tests/f002-content-guards.test.ts`; this is the preferred pattern | Markdown updater helpers, path resolver, hash helper in cross-feature tests | Fixture verdict contract / test-local oracle now; quarantine updater/path tests if unchanged |
| F003 | State-machine literal/types, orchestrator/tool-policy types | Orchestrator class, transition function, tool-policy validators, GitHub auth runtime, MCP writer path policy | Fixture tables / test-model now; planned-src-unit/integration later |
| F004 | Cloudflare/notification/retry/probe types if split cleanly | Notification decision/persistence runtime and generation mismatch class | Schema/fixture/test-model now; live Cloudflare/Discord/backend integration later |
| Cross-cutting | Type-only contracts after source splitting | `src/policies/mcp-write-policy.ts` is not yet in the source boundary inventory | Add to boundary inventory before final traceability integration |

## Immediate follow-up recommendations

1. Add `src/types.ts` and `src/policies/mcp-write-policy.ts` to `.spec/audits/src-phase-boundary-inventory.md` during the serial boundary/traceability integration.
2. Treat all rows marked `Quarantine? = Yes` as candidates for `tests/legacy-production/` unless they are rewritten to schema, fixture, contract-table, or test-local oracle coverage first.
3. Keep already type-only imports only if their source files are split so importing the type does not imply runtime implementation ownership.
4. Keep `tests/f002-content-guards.test.ts` as the preferred current-phase pattern because it encodes fixtures and local oracles without production runtime imports.
5. Do not add new production functions/classes or network/filesystem/GitHub/Cloudflare/Discord/orchestration implementations under `src/` to satisfy any inventory row in the current phase.
