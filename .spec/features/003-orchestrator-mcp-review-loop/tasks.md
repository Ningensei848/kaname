# Tasks: Feature 003

- [ ] F003-T001: Add state transition table tests.
- [ ] F003-T002: Implement MCP process lifecycle and SIGTERM cleanup tests.
- [ ] F003-T003: Implement GitHub App installation token exchange.
- [ ] F003-T004: Add MCP contract builders and schema tests.
- [ ] F003-T005: Add merge precondition tests covering CI, security, content, and branch policy.
- [ ] F003-T006: Add Issue rate-limit / error fingerprint policy.
- [ ] F003-T007: Define the MCP launcher contract that maps the GitHub App installation token to `GITHUB_TOKEN_FOR_MCP` and forbids PAT fallback.
- [ ] F003-T008: Define safe degraded-operation metadata for GitHub App installation-token exchange failures so Issue escalation can report the failure without leaking JWT or credential material.
- [ ] F003-T009: Define the production MCP child-process lifecycle adapter boundary that maps DONE/MERGED/ESCALATED/FAILED/SIGTERM/TIMEOUT outcomes to exactly-once cleanup.
- [ ] F003-T010: Consume deterministic content guard verdicts as merge preconditions before `merge_pull_request`, including the cross-feature artifact contract owned by F002.
