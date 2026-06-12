# F004 traceability diff proposal

This document is the parallel-lane output for **P4. F004 traceability diff proposal**. It is a planning artifact only: it does not add production Cloudflare polling, Discord webhook delivery, notification persistence, Quartz build configuration, or retry/escalation logic under `src/`.

## Reference basis

- Working branch when prepared: `p4-f004-traceability-diff`
- Local baseline used because `origin` / `origin/main` is unavailable in this workspace: `4a3e2bf`
- Feature spec source: `.spec/features/004-cloudflare-discord-notification/spec.md`
- Acceptance source: `.spec/features/004-cloudflare-discord-notification/acceptance.md`
- Webhook contract source: `.spec/contracts/webhook-contracts.md`
- Schema sources: `.spec/schemas/cloudflare-pages-deployment.schema.json` and `.spec/schemas/discord-webhook-payload.schema.json`
- Current traceability rows: `.spec/traceability.md`
- Current `src/` phase boundary source: `.spec/audits/src-phase-boundary-inventory.md`

## F004 scope recap

F004 covers deployment-gated Discord notification and public artifact safety. In the current phase, F004 should be represented through Cloudflare/Discord schemas, webhook fixtures, Quartz artifact fixtures, test-local notification oracles, and type-only boundaries. Production Cloudflare API polling, live Discord sending, durable notification-state storage, public build pipeline wiring, and retry/escalation runtime remain after the implementation gate.

F004 requirements under review:

1. Quartz Graph disabled.
2. Cloudflare deployment gate.
3. Discord payload contract.
4. Duplicate notification state.
5. Discord webhook retry / escalation.

## Existing executable evidence

| Evidence | Current role | Current-phase interpretation |
| --- | --- | --- |
| `.spec/contracts/webhook-contracts.md` | Source contract for Cloudflare deployment and Discord webhook payloads | Spec / policy input for `schema-contract` and `fixture-contract` |
| `.spec/schemas/cloudflare-pages-deployment.schema.json` | Executable Cloudflare Pages deployment event schema | `schema-contract` |
| `.spec/schemas/discord-webhook-payload.schema.json` | Executable Discord webhook payload schema | `schema-contract` |
| `tests/fixtures/f004/cloudflare/*.json` | Production success, preview success, failure, pending, and wrong-branch deployment fixtures | `fixture-contract` |
| `tests/fixtures/f004/discord/valid-deployment-payload.json` | Canonical Discord payload fixture | `fixture-contract` |
| `tests/fixtures/f004/state/notification-state.empty.json` | Empty notification state fixture | `fixture-contract` |
| `tests/fixtures/f004/state/notification-state.duplicate.json` | Duplicate notification state fixture | `fixture-contract` |
| `tests/fixtures/f004/quartz-artifacts/graph-disabled.html` | Valid public artifact fixture without graph UI/scripts | `fixture-contract` |
| `tests/fixtures/f004/quartz-artifacts/graph-enabled.html` | Invalid public artifact fixture with graph UI/scripts | `fixture-contract` |
| `tests/f004-cloudflare-discord.test.ts` | F004 schema, fixture, test-local notification gate, idempotency, payload, Quartz artifact, retry, and backend-generation tests | Mixed `schema-contract`, `fixture-contract`, and `test-model`; contains selected legacy `src` value imports that need inventory |
| `tests/integration/f004-quartz-public-artifacts.integration.ts` | Optional public build artifact integration check | `planned-src-integration` / artifact integration; requires prebuilt `public/` and is not default contract evidence |
| `tests/contracts.test.ts` | Cross-feature webhook shape and MCP audit trail checks | Cross-cutting `fixture-contract`; runtime imports belong to separate inventory |

## `src/` phase-boundary mapping for F004

| `src` file | Boundary classification | F004 relevance | Current-phase traceability treatment |
| --- | --- | --- | --- |
| `src/notifications/cloudflare-discord.ts` | Split | Notification contracts plus runtime deployment decisioning, persistence, payload building, and retry behavior | Keep `CloudflareDeploymentEvent`, `NotificationState`, `NotificationStateBackend`, `NotificationConfig`, `NotificationDecision`, `DiscordPayloadInput`, `RetryPolicy`, `UrlProbe`, and result shapes as `type-boundary`; runtime exports are `planned-src-unit` or `planned-src-integration` |
| `src/orchestrator.ts` | Split | Future Issue escalation and notification workflow orchestration | Treat as `planned-src-integration`; F004 current phase should define contracts and fixtures only |
| `src/mcp/tool-policy.ts` | Split | Future GitHub Issue escalation / audit trail tool policy for notification failures | Treat as cross-feature `fixture-contract` / `planned-src-integration`, not completed F004 runtime behavior |
| Quartz config / build output | Not currently represented as a `src` file | Public artifact policy that disables graph UI/scripts | Keep fixture and optional artifact integration evidence separate from production build pipeline completion |

## Proposed `.spec/traceability.md` F004 row changes

The table below is a proposed replacement for the current F004 rows when the serial traceability integration task runs.

| Requirement | Existing / target code | Existing / target tests | Proposed coverage depth | Proposed status | Proposed notes |
| --- | --- | --- | --- | --- | --- |
| Quartz Graph disabled | Fixture-level artifact contract and optional public build artifact integration; future Quartz config/build gate after implementation gate | `tests/f004-cloudflare-discord.test.ts`; `tests/integration/f004-quartz-public-artifacts.integration.ts`; `tests/fixtures/f004/quartz-artifacts/*.html` | `fixture-contract` | partial | Fixture coverage is valid current-phase evidence. The integration artifact test requires a prepared `public/` directory and should not be treated as default CI coverage unless its preconditions are explicitly wired. |
| Cloudflare deployment gate | Schema/fixture contract and test-local notification decision model; type boundary from `src/notifications/cloudflare-discord.ts` after split | `tests/f004-cloudflare-discord.test.ts`; `tests/fixtures/f004/cloudflare/*.json`; legacy shape checks in `tests/contracts.test.ts` | `fixture-contract` | partial | Production-success gating behavior is executable via fixtures and a test-local oracle. Runtime `evaluate*` imports from `src` should be inventoried as planned implementation, not counted as `src-unit`. |
| Discord payload contract | Discord payload schema and canonical fixture; optional type boundary for payload input/result shapes | `tests/f004-cloudflare-discord.test.ts`; `.spec/schemas/discord-webhook-payload.schema.json`; `tests/fixtures/f004/discord/valid-deployment-payload.json` | `schema-contract` | partial | Schema and canonical fixture define the payload contract. Production payload builder behavior remains planned while `src/notifications/cloudflare-discord.ts` is a split candidate. |
| Duplicate notification state | Notification-state fixtures and test-local idempotency/backend-generation model; future external backend implementation after gate | `tests/f004-cloudflare-discord.test.ts`; `tests/fixtures/f004/state/*.json` | `test-model` | partial | Duplicate deployment / commit-hash rules are modeled deterministically, but durable external notification state storage is not implemented in the current phase. |
| Discord webhook retry / escalation | Test-local bounded retry model and future Issue escalation contract | `tests/f004-cloudflare-discord.test.ts`; cross-feature MCP Issue contracts in `tests/contracts.test.ts` | `test-model` | partial | Retry and escalation invariants are executable as local models. Real Discord webhook delivery, sleeper/timer integration, and GitHub Issue escalation are `planned-src-integration`. |

## Value-import follow-up items for P5

The following F004 and cross-cutting imports should be included in `.spec/audits/test-src-value-import-inventory.md`:

| Test file | Imported `src` file | Runtime identifiers requiring classification | Suggested classification |
| --- | --- | --- | --- |
| `tests/f004-cloudflare-discord.test.ts` | `../src/notifications/cloudflare-discord` | `evaluateAndPersistNotification` | Legacy production value import; classify as `planned-src-integration` or quarantine until implementation gate |
| `tests/f004-cloudflare-discord.test.ts` | `../src/notifications/cloudflare-discord` | `GenerationMismatchError` | Runtime error class import; classify with notification backend conflict handling cleanup |
| `tests/f004-cloudflare-discord.test.ts` | `../src/notifications/cloudflare-discord` | `CloudflareDeploymentEvent`, `JsonObject`, `NotificationState`, `NotificationStateBackend`, `NotificationStateSnapshot`, `RetryPolicy`, `UrlProbe` | Type-only import; retain as `type-boundary` if the source file is split cleanly |
| `tests/contracts.test.ts` | `../src/mcp/tool-policy` | merge/tool policy helpers used by cross-feature contract checks | Cross-cutting fixture-contract plus legacy runtime import; inventory before assigning F004 completion credit |
| `tests/contracts.test.ts` | `../src/policies/mcp-write-policy` | `isAllowedMcpWriterPath` | Cross-cutting policy runtime import; classify after the policy file is added to boundary inventory |
| `tests/integration/f004-quartz-public-artifacts.integration.ts` | None from `src` | N/A | Optional artifact integration; document `public/` precondition and keep outside default contract evidence unless explicitly gated |

## Recommended next integration actions

1. During the serial traceability update, replace F004 `src-unit` depth with the proposed current-phase `schema-contract`, `fixture-contract`, and `test-model` depths above.
2. Preserve Cloudflare, Discord, notification-state, and Quartz artifact fixtures as valid current-phase contract evidence.
3. Treat `evaluateAndPersistNotification`, `GenerationMismatchError`, payload builder, retry, and notification persistence behavior in `src/notifications/cloudflare-discord.ts` as planned runtime work until the split is complete.
4. Keep real Cloudflare / Discord credential use in integration backlog behind explicit environment guards, and document the `public/` precondition for the Quartz artifact integration test separately from default `pnpm test`.
5. Do not add production Cloudflare API calls, Discord webhook sends, external notification-state backend implementations, Quartz build pipeline changes, or retry/escalation orchestration under `src/` for F004 in the current phase.
