# Traceability matrix

This matrix maps high-level specifications to feature specs, implementation targets, and current test coverage. Status values are: `done`, `partial`, `missing`, `planned`.

| Requirement | Feature | Existing / target code | Existing / target tests | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| SSoT YAML validation | F001 | `src/crawler/parser.ts` | `tests/parser.test.ts` | partial | Move schema to `.spec/schemas/ssot.schema.json`. |
| Fetch retry and conditional GET | F001 | `src/crawler/fetch.ts` | `tests/fetch.test.ts` | partial | Needs timeout configurability and source-level degraded operation integration. |
| `crawler-state.json` idempotency | F001 | `src/crawler/state.ts` | `tests/state.test.ts` | partial | Backend must move from local file abstraction to Cloud Storage generation-precondition adapter. |
| No LLM / commit on unchanged content | F001 | orchestrator guard target | `tests/business-rules.test.ts` | partial | Needs explicit Writer / MCP invocation spy tests. |
| Topic frontmatter schema | F002 | planned | planned contract tests | missing | Add executable schema. |
| Incremental Markdown update | F002 | `src/utils/markdown-updater.ts` | `tests/markdown-updater.test.ts` | partial | Current utility is local; full-document guard still missing. |
| No-overwrite content guard | F002 | planned | planned diff guard tests | missing | Must be deterministic before Reviewer. |
| Orphan note resolution | F002 | planned graph scanner | planned graph tests | missing | Current tests simulate link insertion only. |
| Report novelty / duplicate suppression | F002 | planned | planned report tests | missing | Needs measurable thresholds. |
| Orchestrator max-3 review loop | F003 | `src/orchestrator.ts` | `tests/orchestrator.test.ts` | partial | Needs explicit state transition table coverage. |
| MCP process lifecycle cleanup | F003 | planned `McpClient` | planned SIGTERM tests | missing | Required by tasks 1.4.1. |
| GitHub App JWT | F003 | `src/auth/github-auth.ts` | `tests/github-auth.test.ts` | partial | Installation token exchange still missing. |
| MCP JSON-RPC contracts | F003 | planned contract builders | planned contract tests | missing | Convert examples in `contracts/mcp-contracts.md` into fixtures. |
| Protected merge preconditions | F003 | planned Reviewer gate | planned gate tests | missing | Must aggregate CI, Takumi Guard, deterministic content gates. |
| Quartz Graph disabled | F004 | planned Quartz config | planned artifact tests | missing | Verify config and build output. |
| Cloudflare deployment gate | F004 | planned notification gate | planned webhook tests | missing | Require success + production + main. |
| Discord embed payload | F004 | planned notification builder | planned schema tests | missing | Convert example to executable fixture. |
| Discord idempotency | F004 | planned notification state | planned duplicate event tests | missing | Store outside Git. |
| Takumi Guard required gate | Cross-cutting | CI / Reviewer gate target | CI and gate tests | planned | Fail closed on unavailable / indeterminate status. |

## Prototype canonical interface catalog

The following test-local prototype functions are the canonical executable interfaces until their production modules exist. New tests should import or extract from the canonical source listed here rather than recreating parallel helpers. When a production `src/` module lands, keep the test signature compatible and delete the listed competing implementations in the same change.

| Prototype function | Canonical source test file | Future `src/` module path | Input type | Output type | Sync / async | Dependency injection boundary | Duplicate / deprecated competing implementation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `shouldNotifyDiscord` | `tests/f004-cloudflare-discord.test.ts` | `src/notifications/cloudflare-discord.ts` | `(event: CloudflareDeploymentEvent, state: NotificationState, config: NotificationConfig, probeReportUrl: UrlProbe)` | `Promise<NotificationDecision>` | async | Inject `UrlProbe` for latest-report reachability; inject external notification state via caller-owned `NotificationState`. | `tests/contracts.test.ts` has an older boolean-only helper; migrate or delete it after the PR conflict is resolved, and do not expand commit-hash-only state or non-HTTPS URL checks there. |
| `buildDiscordPayload` | `tests/f004-cloudflare-discord.test.ts` | `src/notifications/cloudflare-discord.ts` | `DiscordPayloadInput` (`deployment`, `publicBaseUrl`, `latestReportUrl`, `relatedTopics`) | `JsonObject` Discord webhook payload | sync | No network DI; all dynamic values arrive in `DiscordPayloadInput`, while schema/policy validation remains separate. | `tests/contracts.test.ts` has a fixed fixture builder; migrate or delete it after the PR conflict is resolved, and make future contract coverage call the canonical builder or schema fixtures. |
| `recordNotifiedDeployment` | `tests/f004-cloudflare-discord.test.ts` | `src/notifications/cloudflare-discord.ts` | `(state: NotificationState, event: CloudflareDeploymentEvent)` | `NotificationState` | sync | Pure state transition; storage/generation precondition is outside the function in `NotificationStateBackend.save`. | None currently; avoid duplicating idempotency updates inside backend adapters. |
| `sendDiscordWithBoundedRetry` | `tests/f004-cloudflare-discord.test.ts` | `src/notifications/discord-webhook.ts` | `(sendWebhook: () => Promise<{ ok: boolean; status: number }>, sleep: (ms: number) => Promise<void>, policy: RetryPolicy)` | `Promise<DiscordSendResult>` (`"sent" \| "escalate_issue"`) | async | Inject webhook sender and sleeper/timer; production owns HTTP client, secret URL, and clock. | None currently; avoid embedding retry loops in orchestration code. |
| `transition` | `tests/f003-orchestrator-state-table.test.ts` | `src/orchestrator/state-machine.ts` | `(state: State, event: Event, context: TransitionContext)` | `TransitionResult` | sync | Pure function; external effects are action names consumed by orchestrator adapters. | State branching inside `src/orchestrator.ts` should be migrated to this table-driven module when implemented. |
| `validateToolPolicy` | `tests/f003-mcp-contract-fixtures.test.ts` | `src/mcp/tool-policy.ts` | `(call: McpToolCall, preconditions?: MergePreconditions)` | `string[]` validation errors | sync | Pure validation; schema loading and gate evidence are caller-provided or module-local constants until extracted. | `assertValidMcpCall` in `tests/contracts.test.ts` is deprecated broad contract coverage and should be replaced by this validator. |
| `isAllowedWriterPath` | `tests/f003-mcp-contract-fixtures.test.ts` | `src/mcp/tool-policy.ts` | `filePath: string` | `boolean` | sync | Pure path predicate; no filesystem access. | `isAllowedContentPath` in `tests/contracts.test.ts` is deprecated because it permits broader topic paths than the canonical F003 fixture policy. |
| `noOverwriteGuard` | `tests/f002-content-guards.test.ts` | `src/content/guards/no-overwrite.ts` | `(before: string, after: string)` | `GuardResult` | sync | Pure Markdown text comparison; parsing remains deterministic and local. | None currently; keep production Writer/Reviewer checks from adding alternate destructive-change logic. |
| `internalLinkGuard` | `tests/f002-content-guards.test.ts` | `src/content/guards/internal-links.ts` | `(markdown: string, knownTitles: Set<string>)` | `GuardResult` | sync | Inject known title index; do not read the vault from inside the guard. | None currently; graph scanners should feed `knownTitles` rather than revalidating links differently. |
| `orphanScoreRegressionGuard` | `tests/f002-content-guards.test.ts` | `src/content/guards/orphan-score.ts` | `(beforeVault: VaultDocument[], afterVault: VaultDocument[], allowedNewHighSeverityOrphans?: number)` | `GuardResult` | sync | Inject before/after vault snapshots; filesystem and graph collection stay outside the guard. | None currently; future graph module should expose snapshots compatible with `VaultDocument[]`. |
| `reportNoveltyGuard` | `tests/f002-content-guards.test.ts` | `src/content/guards/report-novelty.ts` | `(reportMarkdown: string, existingTopicMarkdown: string, options: { duplicateThreshold: number; createsNewRootTopic?: boolean })` | `GuardResult` | sync | Pure text comparison with threshold options injected by policy. | None currently; avoid one-off duplicate suppression checks in report generation. |
