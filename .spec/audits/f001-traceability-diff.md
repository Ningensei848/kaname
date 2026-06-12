# F001 traceability diff proposal

This document is the parallel-lane output for **P1. F001 traceability diff proposal**. It is intentionally a planning artifact only: it does not change production code, does not promote `src/` runtime implementation, and does not mark production behavior as complete merely because a test imports runtime values from `src/`.

## Reference basis

- Working branch when prepared: `p1-f001-traceability-diff`
- Local baseline used because `origin` / `origin/main` is unavailable in this workspace: `bc504a9cc48def07631b37b76dcd6310e506b2bf`
- Feature spec source: `.spec/features/001-crawler-idempotency/spec.md`
- Acceptance source: `.spec/features/001-crawler-idempotency/acceptance.md`
- Current traceability rows: `.spec/traceability.md`
- Current `src/` phase boundary source: `.spec/audits/src-phase-boundary-inventory.md`

## F001 scope recap

F001 covers crawler idempotency and external state. The current-phase SDD/TDD boundary means the feature should be tracked as schema, fixture, test-local model, or type-boundary coverage until production implementation work is explicitly opened.

F001 requirements under review:

1. SSoT YAML validation.
2. Fetch retry and conditional GET.
3. `crawler-state.json` idempotency.
4. No LLM / commit on unchanged content.

## Existing executable evidence

| Evidence | Current role | Current-phase interpretation |
| --- | --- | --- |
| `.spec/schemas/ssot.schema.json` | Executable SSoT contract schema | `schema-contract` |
| `.spec/schemas/crawler-state.schema.json` | Executable crawler-state contract schema | `schema-contract` |
| `tests/fixtures/f001/ssot.valid.json` | Valid SSoT fixture | `fixture-contract` |
| `tests/fixtures/f001/ssot.invalid.json` | Invalid SSoT fixture | `fixture-contract` |
| `tests/fixtures/f001/crawler-state.valid.json` | Valid external crawler state fixture | `fixture-contract` |
| `tests/fixtures/f001/crawler-state.invalid.json` | Invalid crawler state fixture | `fixture-contract` |
| `tests/f001-idempotency-contract.test.ts` | F001 acceptance contract tests with local schema validation, fake GCS object store, and unchanged replay/MCP call assertions | Mixed `schema-contract`, `fixture-contract`, and `test-model`; also contains legacy `src` value imports that must be inventoried |
| `tests/f001-crawler-failure-escalation.test.ts` | Retry failure, degraded operation, state backend, and conflict escalation tests | Mostly `test-model` / planned integration behavior; currently imports runtime values from `src` and should not be counted as completed production coverage |
| `tests/parser.test.ts` | Legacy parser unit test | `planned-src-unit` or contract replacement candidate; depends on `src/crawler/parser.ts`, which is an evacuation candidate |
| `tests/fetch.test.ts` | Legacy fetch unit test | `planned-src-unit` or contract replacement candidate; depends on runtime exports from split candidate `src/crawler/fetch.ts` |
| `tests/state.test.ts` | Legacy state unit test | `planned-src-unit` / type-boundary split candidate; runtime state helpers are not current-phase coverage |
| `tests/state-backends-gcs.test.ts` | Legacy GCS backend unit test | `planned-src-unit` / possible integration backlog candidate; class implementation is not current-phase coverage |
| `tests/business-rules.test.ts` | Cross-feature legacy business-rule tests | Needs separate cross-cutting inventory before assigning F001 credit |

## `src/` phase-boundary mapping for F001

| `src` file | Boundary classification | F001 relevance | Current-phase traceability treatment |
| --- | --- | --- | --- |
| `src/crawler/parser.ts` | Evacuate | SSoT parser / malformed source handling | Do not count as `src-unit`; replace with schema/fixture contract or mark as `planned-src-unit` after implementation gate |
| `src/crawler/fetch.ts` | Split | Fetcher type, crawl source options, retry / conditional GET runtime | Keep `Fetcher`, `FetchResult`, and `CrawlSourceOptions` as `type-boundary`; move retry/network behavior to `planned-src-unit` / `planned-src-integration` |
| `src/crawler/state.ts` | Split | State backend adapter, state snapshots, hash/state runtime helpers | Keep adapter/snapshot declarations as `type-boundary`; runtime hashing, parsing, IO, and mutation helpers are `planned-src-unit` |
| `src/crawler/state-errors.ts` | Evacuate | `StateConflictError` runtime class used by current tests | Inventory as legacy value import; do not use as current-phase completion evidence |
| `src/crawler/state-backends/gcs.ts` | Split | GCS backend options/fetch boundary plus Cloud Storage adapter class | Keep options/fetch boundary as `type-boundary`; adapter class/network behavior is `planned-src-integration` |
| `src/crawler/state-backends/local.ts` | Evacuate | Local filesystem state backend | No current F001 completion credit; quarantine or backlog if imported by tests |
| `src/orchestrator.ts` | Split | Unchanged-content skip, failure escalation, state backend DI | Keep dependency/interface declarations as `type-boundary`; orchestration behavior is `planned-src-integration` |

## Proposed `.spec/traceability.md` F001 row changes

The table below is a proposed replacement for the current F001 rows when the serial traceability integration task runs.

| Requirement | Existing / target code | Existing / target tests | Proposed coverage depth | Proposed status | Proposed notes |
| --- | --- | --- | --- | --- | --- |
| SSoT YAML validation | Schema-owned contract in `.spec/schemas/ssot.schema.json`; future parser boundary may expose only schema-derived types during current phase | `tests/f001-idempotency-contract.test.ts`; `tests/fixtures/f001/ssot.valid.json`; `tests/fixtures/f001/ssot.invalid.json`; legacy `tests/parser.test.ts` to inventory | `schema-contract` | partial | Executable schema and fixtures exist. `src/crawler/parser.ts` is an evacuation candidate, so parser unit tests must not be counted as current-phase `src-unit` coverage. |
| Fetch retry and conditional GET | Type boundary from `src/crawler/fetch.ts` may remain; runtime fetch/backoff/conditional GET implementation is after the implementation gate | `tests/fetch.test.ts`; retry/degraded-operation model in `tests/f001-crawler-failure-escalation.test.ts` | `planned-src-unit` | planned | Current tests exercise or model runtime fetch behavior, but retry/network implementation belongs after the phase gate. Keep `Fetcher`-style types as boundary only. |
| `crawler-state.json` idempotency | `.spec/schemas/crawler-state.schema.json`; type boundary from `src/crawler/state.ts`; future external backend adapter implementation | `tests/f001-idempotency-contract.test.ts`; `tests/f001-crawler-failure-escalation.test.ts`; `tests/state.test.ts`; `tests/state-backends-gcs.test.ts`; `tests/fixtures/f001/crawler-state.*.json` | `fixture-contract` | partial | Schema fixtures and fake generation-precondition models are valid current-phase evidence. Production GCS adapter/state mutation imports should be treated as legacy or `planned-src-integration`, not `done`. |
| No LLM / commit on unchanged content | Orchestrator dependency/interface boundary may remain; Writer/MCP runtime orchestration is after the implementation gate | `tests/f001-idempotency-contract.test.ts`; cross-feature legacy `tests/business-rules.test.ts` | `test-model` | partial | Unchanged replay assertions and strict MCP spy behavior describe the contract. They should not imply production orchestrator completion while `src/orchestrator.ts` is a split candidate. |

## Value-import follow-up items for P5

The following F001 imports should be included in `.spec/audits/test-src-value-import-inventory.md`:

| Test file | Imported `src` file | Runtime identifiers requiring classification | Suggested classification |
| --- | --- | --- | --- |
| `tests/f001-idempotency-contract.test.ts` | `../src/crawler/state-errors` | `StateConflictError` | Legacy production value import; replace with test-local conflict shape or quarantine until implementation gate |
| `tests/f001-idempotency-contract.test.ts` | `../src/crawler/state-backends/gcs` | `GcsStateBackend` | `planned-src-integration`; keep only type/options boundary in current phase |
| `tests/f001-idempotency-contract.test.ts` | `../src/orchestrator` | `DiffResult`, `OrchestratorDependencies` | Already type-only; retain as `type-boundary` if the source file is split cleanly |
| `tests/f001-idempotency-contract.test.ts` | `../src/types` | `CrawlerState` | Type-only; retain as `type-boundary` if schema-derived type remains allowed |
| `tests/f001-crawler-failure-escalation.test.ts` | `../src/orchestrator` | `crawlSourcesWithFailureEscalation` | Legacy production value import; contract should move to test-local oracle or `planned-src-integration` |
| `tests/f001-crawler-failure-escalation.test.ts` | `../src/crawler/fetch` | `Fetcher` | Type-only import already; retain as `type-boundary` |
| `tests/f001-crawler-failure-escalation.test.ts` | `../src/crawler/state` | `StateConflictError` | Legacy production value import and possibly wrong source of the conflict class; classify with state error handling cleanup |
| `tests/f001-crawler-failure-escalation.test.ts` | `../src/types` | `CrawlerState`, `SsotSource` | Type-only; retain as schema/type boundary if kept contract-only |
| `tests/parser.test.ts` | `../src/crawler/parser` | `parseSsotYaml` | Evacuate dependency; replace with schema fixture contract or mark as `planned-src-unit` |
| `tests/fetch.test.ts` | `../src/crawler/fetch` | `fetchWithRetry`, `cleanHtml`, `parseRssFeed` | Split dependency; runtime behavior becomes `planned-src-unit` |
| `tests/state.test.ts` | `../src/crawler/state` | state initialization, parsing, hashing, load/save, update helpers | Split dependency; retain only adapter/snapshot types as current-phase boundary |
| `tests/state-backends-gcs.test.ts` | `../src/crawler/state`, `../src/crawler/state-backends/gcs` | `StateConflictError`, `GcsStateBackend` | `planned-src-integration` or legacy quarantine; keep fetch/options types only |
| `tests/business-rules.test.ts` | `../src/crawler/state` | `calculateHash` | Cross-cutting legacy production value import; do not assign F001 completion credit without inventory |

## Recommended next integration actions

1. During the serial traceability update, replace F001 `src-unit` / `src-integration` depth with the proposed current-phase depths above.
2. Keep schema and fixture evidence as valid current-phase F001 progress.
3. Treat runtime imports from `src/crawler/*`, `src/orchestrator.ts`, and `src/crawler/state-backends/gcs.ts` as inventory inputs, not as implementation completion.
4. Do not delete or rewrite tests in this P1 lane; leave quarantine / conversion decisions to the later legacy production test handling task.
5. Do not add new production functions or classes under `src/` for F001 until the implementation gate opens.
