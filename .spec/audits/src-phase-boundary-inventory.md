# `src/` current-phase boundary inventory

This inventory classifies the requested `src/` candidates against the current phase rule from `.spec/tasks.md`: production code under `src/` must stay limited to type, interface, contract boundary, literal-union, fixture/schema-derived type, and related contract declarations. Runtime implementations are tracked as evacuation or deletion candidates until Red / contract test / traceability synchronization is complete.

## Classification legend

- **Keep now**: `interface`, `type`, enum-like literal union, or fixture/schema-aligned contract type that may remain in `src/` during the current phase.
- **Evacuate / delete candidate**: `export function`, `export class`, runtime validation logic, network / filesystem / GitHub / Cloudflare / Discord implementation, or orchestration implementation.
- **Recommended action**:
  - **Keep**: file is already contract-only or type-only for the current phase.
  - **Split**: keep contract declarations in `src/`; move runtime exports/implementation to backlog, prototype, or a future implementation branch.
  - **Evacuate**: file is dominated by runtime implementation and should not remain in current-phase `src/` once callers are migrated.

## File inventory

| File | Keep now | Evacuate / delete candidate | Recommended action | Reason |
| --- | --- | --- | --- | --- |
| `src/crawler/fetch.ts` | `FetchResult`, `Fetcher`, `CrawlSourceOptions` | `fetchWithRetry`, `cleanHtml`, `parseRssFeed`, `crawlSource`, helper parsing/CDATA logic, native `fetch` timeout/retry behavior | Split | Contract types can remain, but the exported crawler/fetch/parser logic is runtime networking and text-processing implementation. |
| `src/crawler/parser.ts` | `ParsedSsotYaml`, `SourceCandidate` shape declarations if promoted/exported as schema-derived contracts | `parseSsotYaml`, filesystem read, YAML parsing, root/source runtime validation helpers | Evacuate | The file is dominated by filesystem IO and runtime validation logic rather than exported contract declarations. |
| `src/crawler/path-resolver.ts` | None currently exported as a contract type | `resolveTopicPath`, `sanitizeName`, filesystem directory inspection, path normalization, Windows-name validation | Evacuate | Path resolution is filesystem/path implementation; no current-phase contract export needs to remain in this file. |
| `src/crawler/state.ts` | `StateSnapshot<T>`, `SaveStateOptions`, `StateBackendAdapter<T>` | `createInitialCrawlerState`, `parseCrawlerState`, `calculateHash`, `loadCrawlerState`, `saveCrawlerState`, `updateSourceState` | Split | Backend adapter and snapshot contracts can remain, but state initialization, JSON validation, hashing, filesystem state IO, and mutation helpers are runtime implementation. |
| `src/crawler/state-errors.ts` | None as a type-only contract | `StateConflictError` class | Evacuate | The exported class is runtime error implementation, which is outside the current phase boundary. |
| `src/crawler/state-backends/gcs.ts` | `FetchLike`, `GcsStateBackendOptions` | `GcsStateBackend` class, GCS HTTP load/save, generation precondition handling, response parsing helpers | Split | Options/fetch contracts are useful boundaries, but the class is Cloud Storage network implementation. |
| `src/crawler/state-backends/local.ts` | None currently exported as a type-only contract | `LocalFileStateBackend`, `loadCrawlerStateSnapshotFromFile`, local generation/hash helpers, filesystem state IO | Evacuate | The file is local filesystem implementation and should be removed from current-phase `src/` after test/caller migration. |
| `src/content/guards/index.ts` | Type-only re-exports: `LinkAliasSource`, `ReportNoveltyContext`, `GuardResult`, `TopicAliasMap`, `VaultDocument` | None in this barrel file | Keep | The barrel currently uses `export type` only and is compatible with the current phase. |
| `src/content/guards/types.ts` | `GuardResult`, `VaultDocument`, `TopicAliasMap` | None | Keep | The file is contract-only and contains guard/vault shape declarations. |
| `src/content/guards/internalLinkGuard.ts` | `LinkAliasSource` | `internalLinkGuard`, `collectInternalLinks`, alias collection and malformed-link detection helpers | Split | The alias union can remain, but link analysis is deterministic guard implementation. |
| `src/content/guards/noOverwriteGuard.ts` | None currently exported as a type-only contract | `noOverwriteGuard`, markdown/frontmatter parsing, destructive-change counting helpers | Evacuate | The file is runtime validation/guard logic. |
| `src/content/guards/orphanScoreRegressionGuard.ts` | None currently exported as a type-only contract | `orphanScoreRegressionGuard`, orphan title scoring helper, `collectInternalLinks` dependency | Evacuate | The file is guard/orphan-score runtime validation logic. |
| `src/content/guards/reportNoveltyGuard.ts` | `ReportNoveltyContext`, local `ReportNoveltyOptions` if exported/promoted as policy contract | `reportNoveltyGuard`, duplicate ratio calculation, sentence extraction, item evidence checks, n-gram/Jaccard helpers | Split | Context/options contracts can remain, but novelty scoring is runtime validation logic. |
| `src/orchestrator.ts` | `OrchestratorGateStatus`, `OrchestratorMergePreconditions`, `McpToolCall`, `McpClient`, `ToolMcpClient`, crawler escalation/result interfaces, `DiffResult`, `ReviewResult`, `PRState`, `OrchestrationResult`, `ExecutionStatus`, `OrchestratorDependencies` | `defaultMergePreconditions`, `validateOrchestratorToolPolicy`, `AegisOrchestrator`, `runOrchestration`, `crawlSourcesWithFailureEscalation`, merge-precondition checks, Issue-call builders | Split | This file has many useful orchestration contracts, but also central orchestration, crawling, MCP, and state-conflict runtime implementation. |
| `src/orchestrator/state-machine.ts` | `OrchestratorState`, `OrchestratorEvent`, `OrchestratorAction`, `TransitionContext`, `TransitionResult`, `TransitionRecord` | `transition` | Split | The literal unions and transition record are current-phase contracts; the transition function is orchestration implementation. |
| `src/mcp/tool-policy.ts` | `JsonObject`, `GateStatus`, `MergePreconditions`, `PolicyMcpToolCall`, `ToolName`, `ArgumentTypeName`, `ToolArgumentShape` if exported/promoted as policy contract | `allGreenMergePreconditions`, `validateToolPolicy`, `canMerge`, `validateMergePreconditions`, argument/envelope/path validation helpers | Split | MCP call and gate contracts can remain; policy execution and validation logic are runtime implementation. |
| `src/policies/mcp-write-policy.ts` | `McpWritePolicy`, `McpWriterPath` | None | Keep | The file contains only contract-safe MCP write policy boundary declarations and a string path alias; no runtime policy functions are present. |
| `src/types.ts` | type/interface declarations present in this file | None | Keep | ファイルはインタフェースおよび型定義のみで構成されており、現フェーズの型境界に完全適合するため |
| `src/notifications/cloudflare-discord.ts` | `JsonObject`, `ProbeResult`, `UrlProbe`, `DiscordSendResult`, `CloudflareDeploymentEvent`, `NotificationState`, `NotificationStateSnapshot`, `NotificationStateBackend`, `NotificationConfig`, `NotificationDecision`, `PersistedNotificationDecision`, `DiscordPayloadInput`, `RetryPolicy` | `GenerationMismatchError`, `evaluateDiscordNotification`, `recordNotificationState`, `evaluateAndPersistNotification`, `buildDiscordPayload`, `sendDiscordWithBoundedRetry`, HTTPS/URL normalization helpers | Split | Deployment, state, and payload contracts can remain; Cloudflare/Discord decisioning, persistence, payload building, and retry logic are runtime implementation. |
| `src/auth/github-auth.ts` | `GitHubInstallationTokenResponse`, `GitHubInstallationTokenExchangeOptions`, `GitHubInstallationTokenFetchResponse`, `GitHubInstallationTokenFetch` | `generateGitHubAppJwt`, `exchangeJwtForInstallationToken`, crypto/JWT creation, GitHub API exchange and response validation | Split | Token contracts can remain; GitHub authentication, crypto, network exchange, and validation are runtime implementation. |
| `src/utils/markdown-updater.ts` | None currently exported as a type-only contract | `appendSectionToMarkdown`, `injectInternalLinkToMarkdown`, markdown heading/link helpers | Evacuate | The file is Markdown mutation implementation and does not expose current-phase contract types. |

## Roll-up

### Current-phase keep list

- Keep as-is: `src/content/guards/index.ts`, `src/content/guards/types.ts`, `src/policies/mcp-write-policy.ts`, `src/types.ts`.
- Keep after splitting runtime exports away: contract declarations from `src/crawler/fetch.ts`, `src/crawler/state.ts`, `src/crawler/state-backends/gcs.ts`, `src/content/guards/internalLinkGuard.ts`, `src/content/guards/reportNoveltyGuard.ts`, `src/orchestrator.ts`, `src/orchestrator/state-machine.ts`, `src/mcp/tool-policy.ts`, `src/notifications/cloudflare-discord.ts`, and `src/auth/github-auth.ts`.

### Current-phase evacuation / deletion candidates

- Evacuate whole file after callers/tests are migrated: `src/crawler/parser.ts`, `src/crawler/path-resolver.ts`, `src/crawler/state-errors.ts`, `src/crawler/state-backends/local.ts`, `src/content/guards/noOverwriteGuard.ts`, `src/content/guards/orphanScoreRegressionGuard.ts`, and `src/utils/markdown-updater.ts`.
- Split and evacuate runtime exports from mixed files: `src/crawler/fetch.ts`, `src/crawler/state.ts`, `src/crawler/state-backends/gcs.ts`, `src/content/guards/internalLinkGuard.ts`, `src/content/guards/reportNoveltyGuard.ts`, `src/orchestrator.ts`, `src/orchestrator/state-machine.ts`, `src/mcp/tool-policy.ts`, `src/notifications/cloudflare-discord.ts`, and `src/auth/github-auth.ts`.
