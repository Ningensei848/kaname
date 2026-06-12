# F002 traceability diff proposal

This document is the parallel-lane output for **P2. F002 traceability diff proposal**. It is a planning artifact only: it does not add production guard logic, does not promote Markdown mutation helpers from `tests/` into `src/`, and does not treat legacy `src` value imports as completed current-phase implementation.

## Reference basis

- Working branch when prepared: `p2-f002-traceability-diff`
- Local baseline used because `origin` / `origin/main` is unavailable in this workspace: `bc504a9cc48def07631b37b76dcd6310e506b2bf`
- Feature spec source: `.spec/features/002-wiki-incremental-update/spec.md`
- Acceptance source: `.spec/features/002-wiki-incremental-update/acceptance.md`
- Content policy source: `.spec/policies/content-integrity-policy.md`
- Current traceability rows: `.spec/traceability.md`
- Current `src/` phase boundary source: `.spec/audits/src-phase-boundary-inventory.md`

## F002 scope recap

F002 covers deterministic content integrity for wiki updates. In the current phase, F002 should be represented through executable schemas, fixtures, test-local oracles, contract tables, and type-only boundaries. Production Writer, Markdown updater, graph scanner, and deterministic guard implementations remain after the implementation gate.

F002 requirements under review:

1. Topic frontmatter schema.
2. Incremental Markdown update.
3. No-overwrite content guard.
4. Orphan note resolution.
5. Report novelty / duplicate suppression.

## Existing executable evidence

| Evidence | Current role | Current-phase interpretation |
| --- | --- | --- |
| `.spec/schemas/topic-frontmatter.schema.json` | Executable topic frontmatter schema | `schema-contract` |
| `.spec/policies/content-integrity-policy.md` | Policy source for immutable/mutable content and deterministic guards | Spec / policy input for `fixture-contract` and `test-model` |
| `tests/fixtures/f002/topics/before/nco.md` | Baseline topic fixture | `fixture-contract` |
| `tests/fixtures/f002/topics/after/nco.incremental.md` | Valid incremental update fixture | `fixture-contract` |
| `tests/fixtures/f002/topics/after/nco.destructive.md` | Destructive update fixture | `fixture-contract` |
| `tests/fixtures/f002/topics/after/nco.broken-link.md` | Broken-link fixture | `fixture-contract` |
| `tests/fixtures/f002/topics/after/nco.double-wrapped.md` | Double-wrapped link fixture | `fixture-contract` |
| `tests/fixtures/f002/topics/after/nco.invalid-frontmatter.md` | Invalid frontmatter fixture | `fixture-contract` |
| `tests/fixtures/f002/reports/valid-delta.md` | Valid report novelty fixture | `fixture-contract` |
| `tests/fixtures/f002/reports/duplicate-without-link.md` | Duplicate / no-link report fixture | `fixture-contract` |
| `tests/f002-content-guards.test.ts` | Test-local executable guard contracts for frontmatter, immutable paths, no-overwrite, internal links, orphan score, novelty, and fixture verdict locking | Mixed `schema-contract`, `fixture-contract`, and `test-model`; intentionally avoids production runtime imports |
| `tests/markdown-updater.test.ts` | Legacy unit tests for Markdown mutation helpers imported from `src/utils/markdown-updater.ts` | `planned-src-unit` or quarantine candidate; not current-phase production evidence |
| `tests/business-rules.test.ts` | Cross-feature BDD tests that import Markdown updater and path/state helpers from `src` | Cross-cutting legacy value-import inventory input; should not grant F002 completion credit by itself |

## `src/` phase-boundary mapping for F002

| `src` file | Boundary classification | F002 relevance | Current-phase traceability treatment |
| --- | --- | --- | --- |
| `src/content/guards/index.ts` | Keep | Type-only guard barrel | Retain as `type-boundary` because it re-exports types only |
| `src/content/guards/types.ts` | Keep | `GuardResult`, `VaultDocument`, `TopicAliasMap` contracts | Retain as `type-boundary` |
| `src/content/guards/internalLinkGuard.ts` | Split | Link alias contract plus runtime internal-link validation | Keep `LinkAliasSource`-style declarations as `type-boundary`; runtime link scanning is `planned-src-unit` |
| `src/content/guards/noOverwriteGuard.ts` | Evacuate | Runtime no-overwrite guard implementation | Do not count as current-phase coverage; fixture/test-local oracle remains authoritative for now |
| `src/content/guards/orphanScoreRegressionGuard.ts` | Evacuate | Runtime orphan-score guard implementation | Do not count as current-phase coverage; score model remains `test-model` until implementation gate |
| `src/content/guards/reportNoveltyGuard.ts` | Split | Report novelty context/options plus runtime duplicate scoring | Keep context/options contracts if split; novelty scoring is `planned-src-unit` |
| `src/utils/markdown-updater.ts` | Evacuate | Markdown append/link mutation helpers | Do not count as current-phase `src-unit`; legacy tests become inventory/quarantine or planned implementation evidence |
| `src/orchestrator.ts` | Split | Future Reviewer merge precondition consumption of F002 verdict artifacts | Treat as `planned-src-integration`; current phase should define artifact/contract shape only |
| `src/mcp/tool-policy.ts` | Split | Future protected merge precondition validation that consumes F002 verdicts | Treat F002 verdict artifact acceptance as contract / `planned-src-integration`, not completed runtime Reviewer behavior |

## Proposed `.spec/traceability.md` F002 row changes

The table below is a proposed replacement for the current F002 rows when the serial traceability integration task runs.

| Requirement | Existing / target code | Existing / target tests | Proposed coverage depth | Proposed status | Proposed notes |
| --- | --- | --- | --- | --- | --- |
| Topic frontmatter schema | Schema-owned contract in `.spec/schemas/topic-frontmatter.schema.json`; optional schema-derived type boundary after split | `tests/f002-content-guards.test.ts`; `tests/fixtures/f002/topics/after/nco.invalid-frontmatter.md`; valid topic fixtures | `schema-contract` | partial | Executable schema and fixtures exist. Validation is currently test-local, so this should not be marked `done` production behavior. |
| Incremental Markdown update | Future Writer/updater implementation after the phase gate; `src/utils/markdown-updater.ts` is an evacuation candidate | `tests/markdown-updater.test.ts`; F002 incremental fixture verdicts in `tests/f002-content-guards.test.ts`; cross-feature `tests/business-rules.test.ts` | `planned-src-unit` | planned | The legacy updater tests import runtime helpers from `src`. Current-phase confidence should come from fixture verdicts and no-overwrite contracts, not from promoting the runtime helper. |
| No-overwrite content guard | Test-local oracle plus fixture verdicts; future guard implementation may expose contract-compatible output only after the implementation gate | `tests/f002-content-guards.test.ts`; `tests/fixtures/f002/topics/before/nco.md`; `tests/fixtures/f002/topics/after/nco.incremental.md`; `tests/fixtures/f002/topics/after/nco.destructive.md` | `fixture-contract` | partial | Destructive-change policy is executable through fixtures and local oracle. `src/content/guards/noOverwriteGuard.ts` is an evacuation candidate and should not be counted as current-phase implementation. |
| Orphan note resolution | Test-local graph/orphan score model; future graph scanner and orphan-score implementation after phase gate | `tests/f002-content-guards.test.ts`; link insertion scenarios in `tests/markdown-updater.test.ts` | `test-model` | partial | Orphan score and link resolution are modeled deterministically in tests. Runtime graph scanner / updater work remains planned. |
| Report novelty / duplicate suppression | Test-local novelty / duplicate threshold oracle; future report-generation integration after phase gate | `tests/f002-content-guards.test.ts`; `tests/fixtures/f002/reports/valid-delta.md`; `tests/fixtures/f002/reports/duplicate-without-link.md` | `fixture-contract` | partial | Valid and duplicate report fixtures define the current contract. `src/content/guards/reportNoveltyGuard.ts` may retain context types only after splitting runtime scoring. |

## Value-import follow-up items for P5

The following F002 and cross-cutting imports should be included in `.spec/audits/test-src-value-import-inventory.md`:

| Test file | Imported `src` file | Runtime identifiers requiring classification | Suggested classification |
| --- | --- | --- | --- |
| `tests/markdown-updater.test.ts` | `../src/utils/markdown-updater` | `appendSectionToMarkdown`, `injectInternalLinkToMarkdown` | Legacy production value import; classify as `planned-src-unit` or quarantine until implementation gate |
| `tests/business-rules.test.ts` | `../src/utils/markdown-updater` | `appendSectionToMarkdown`, `injectInternalLinkToMarkdown` | Cross-feature legacy value import; do not use as F002 completion evidence without inventory |
| `tests/business-rules.test.ts` | `../src/crawler/path-resolver` | `resolveTopicPath` | Cross-cutting path resolver value import; outside F002 guard contract and tied to an evacuation candidate |
| `tests/business-rules.test.ts` | `../src/crawler/state` | `calculateHash` | Cross-cutting F001/F002 idempotency helper import; classify outside F002 completion evidence |
| `tests/f002-content-guards.test.ts` | None | N/A | Preferred current-phase pattern: schema/fixture/test-local oracle without production runtime imports |

## Recommended next integration actions

1. During the serial traceability update, replace F002 `prototype` / `src-unit` depth with the proposed current-phase depths above.
2. Preserve `tests/f002-content-guards.test.ts` as the current canonical F002 contract source because it avoids production runtime imports.
3. Treat `tests/markdown-updater.test.ts` and cross-feature `tests/business-rules.test.ts` as legacy value-import inventory inputs, not F002 implementation completion.
4. When the implementation gate opens, extracted `src/content/guards/*` implementations should be verified against the existing fixture verdict contract without changing the oracle.
5. Do not add new production functions, classes, filesystem scanners, Writer integrations, or orchestration logic under `src/` for F002 in the current phase.
