# Integration backlog environment guard audit

This audit is the parallel-lane output for **P7. integration backlog env guard confirmation**. It is a planning artifact only: it does not change integration scripts, test behavior, production code, or credentials handling.

## Reference basis

- Working branch when prepared: `p7-integration-env-guard-audit`
- Local baseline: `ed5ccbd` (`Add traceability diff proposals and test→src import/schema-helper audits (F001–F004, P5–P6)`)
- Script source: `package.json`
- Classification source: `.spec/testing-todo-classification.md`
- Integration backlog source: `tests/integration/backlog.integration.ts`
- Artifact integration source: `tests/integration/f004-quartz-public-artifacts.integration.ts`

## Current scripts

| Script | Command | Current-phase interpretation |
| --- | --- | --- |
| `test` | `node --import tsx --test tests/**/*.test.ts` | Default contract / legacy test command. It does not match `*.integration.ts`, so integration backlog files are outside the default run. |
| `test:integration:artifacts` | `node --import tsx --test tests/integration/**/*.integration.ts` | Runs both guarded backlog tests and the Quartz public artifact test. The name emphasizes artifacts, but the glob currently includes all integration tests. |

## Integration guard findings

| File | Scenario | Guard / precondition | Default credential or live-service risk | Finding |
| --- | --- | --- | --- | --- |
| `tests/integration/backlog.integration.ts` | F003 real dummy child process / SIGTERM cleanup | Requires `KANAME_RUN_PROCESS_SIGNAL_INTEGRATION` | No default OS-signal execution | Guarded correctly; missing env causes `t.skip`. |
| `tests/integration/backlog.integration.ts` | F004 real Cloudflare deployment polling and Discord webhook check | Requires `KANAME_RUN_CLOUDFLARE_DISCORD_INTEGRATION`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_PAGES_PROJECT`, and `DISCORD_WEBHOOK_URL` | No default Cloudflare / Discord credential use | Guarded correctly; missing env causes `t.skip` before network calls. |
| `tests/integration/f004-quartz-public-artifacts.integration.ts` | F004 generated Quartz `public/` artifact contains no graph view UI/scripts | Requires a prepared `public/` directory with HTML artifacts, but not via env var | No external credential risk; local artifact precondition can fail when `public/` is absent | Not a credential integration test. It is an artifact-precondition integration test and should be documented separately from live Cloudflare / Discord backlog. |

## Alignment with `test.todo` classification

`.spec/testing-todo-classification.md` classifies the real process-signal check as integration backlog guarded by `KANAME_RUN_PROCESS_SIGNAL_INTEGRATION`, and the real Cloudflare / Discord checks as integration backlog guarded by explicit Cloudflare / Discord environment variables. The current `tests/integration/backlog.integration.ts` implementation matches that classification.

The Quartz public artifact check is different: it does not require live credentials, but it does require a generated `public/` tree. It should be treated as an optional artifact contract, not as a default local test and not as a live-service credential backlog.

## Boundary recommendations

1. Keep `pnpm test` scoped to non-`*.integration.ts` tests unless the serial default-test-definition task intentionally changes the suite boundary.
2. Consider splitting the current integration command in a later serial task:
   - `test:integration:backlog`: `node --import tsx --test tests/integration/backlog.integration.ts`
   - `test:integration:artifacts`: `node --import tsx --test tests/integration/f004-quartz-public-artifacts.integration.ts`
3. If the artifact integration remains under a broad `tests/integration/**/*.integration.ts` glob, document that `public/` must be generated before the script runs.
4. Do not add Cloudflare, Discord, GitHub, or OS-signal integration execution to the default `pnpm test` path during the current phase.
5. Keep live Cloudflare / Discord credentials opt-in behind both an explicit run flag and the specific credentials already listed in `tests/integration/backlog.integration.ts`.

## Verification commands for serial integration

Recommended commands when finalizing the serial test-command definition:

```sh
pnpm run test
pnpm typecheck
pnpm lint
node --import tsx --test tests/integration/backlog.integration.ts
```

The Quartz artifact command should be run only after preparing `public/`:

```sh
pnpm run test:integration:artifacts
```
