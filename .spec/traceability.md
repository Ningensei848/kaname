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
