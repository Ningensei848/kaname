# JSON Schema helper duplication audit

This audit is the parallel-lane output for **P6. JSON Schema helper duplication investigation**. It is a planning artifact only: it does not change test behavior, does not introduce a shared helper yet, and must not move schema validation helpers into `src/`.

## Reference basis

- Working branch when prepared: `p6-schema-helper-duplication-audit`
- Local baseline: `04f1338` (`Add F001–F004 traceability diff proposals and tests→src import inventory`)
- Discovery command: `rg -n "function validateJsonSchema|function matchesType|function matchesSchemaType|type JsonSchema = Record<string, unknown>" tests .spec src`
- Schema keyword survey command: `rg -n '"(type|required|properties|additionalProperties|items|minItems|minLength|pattern|format|enum|const|oneOf|anyOf|allOf|maximum|minimum)"' .spec/schemas/*.json`
- Existing test helper directory: `tests/helpers/`; currently contains `quartz-artifact-contract.ts` only.

## Duplicate helper locations

| File | Feature / scope | Local helper names | Schema inputs covered today | Notes |
| --- | --- | --- | --- | --- |
| `tests/f001-idempotency-contract.test.ts` | F001 SSoT and crawler-state fixtures | `JsonSchema`, `validateJsonSchema`, `matchesType` | `.spec/schemas/ssot.schema.json`, `.spec/schemas/crawler-state.schema.json` | Broadest current helper for F001 because it supports object maps through schema-valued `additionalProperties`. |
| `tests/f002-content-guards.test.ts` | F002 topic frontmatter fixtures | `JsonSchema`, `validateJsonSchema`, `matchesType` | `.spec/schemas/topic-frontmatter.schema.json` | Supports `enum` and `format: date`; does not need schema-valued `additionalProperties`. |
| `tests/f003-mcp-contract-fixtures.test.ts` | F003 MCP JSON-RPC fixtures | `JsonSchema`, `validateJsonSchema`, `matchesSchemaType` | `.spec/schemas/mcp-tool-call.schema.json` | Minimal subset for MCP envelope fixtures; currently narrower than the full schema keyword set. |
| `tests/f004-cloudflare-discord.test.ts` | F004 Cloudflare and Discord fixtures | `JsonSchema`, `validateJsonSchema`, `matchesSchemaType` | `.spec/schemas/cloudflare-pages-deployment.schema.json`, `.spec/schemas/discord-webhook-payload.schema.json` | Supports `format: uri`, `format: date-time`, `enum`, `pattern`, and arrays. |
| `tests/contracts.test.ts` | Cross-feature MCP / webhook contracts | `JsonSchema`, `validateJsonSchema`, `matchesSchemaType` | Cloudflare, Discord, MCP contract fixtures | Similar to the F004 helper; used by cross-contract tests. |

## JSON Schema subset currently needed

The repository schemas currently use this practical subset:

| Keyword / feature | Needed by | Current helper coverage |
| --- | --- | --- |
| `type` including union arrays such as `["string", "null"]` | F001 crawler state and all object schemas | Covered by all duplicated helpers. |
| `required` | All object schemas | Covered by all duplicated helpers. |
| `properties` | All object schemas | Covered by all duplicated helpers. |
| `additionalProperties: false` | Most object schemas | Covered by all duplicated helpers. |
| schema-valued `additionalProperties` | F001 `crawler-state.schema.json` source-state map | Covered by F001 helper; not consistently present in narrower helpers. |
| `additionalProperties: true` | F003 `mcp-tool-call.schema.json` arguments object | Should be accepted by a shared helper as pass-through. |
| `items` | F001, F002, F004, Discord payload arrays | Covered by relevant duplicated helpers. |
| `minItems` | F001, F002, F004, Discord payload arrays | Covered by F001/F002/F004/cross-contract helpers; verify F003 helper before unification. |
| `minLength` | SSoT, topic frontmatter, Cloudflare, Discord, MCP owner/repo | Covered by most helpers; verify F003 helper before unification. |
| `pattern` | SSoT IDs, state hashes, topic tags/source IDs, commit hashes | Covered by F001/F002/F004/cross-contract helpers; verify F003 helper before unification. |
| `format: uri` | SSoT URLs, Cloudflare URL, Discord URL fields | Covered by F001/F004/cross-contract helpers; F002 only needs date. |
| `format: date-time` | crawler state and Cloudflare/Discord timestamps | Covered by F001/F004/cross-contract helpers. |
| `format: date` | topic frontmatter `updated` | Covered by F002 helper only. |
| `enum` | topic status, Cloudflare status/environment, MCP tool name | Covered by F002/F003/F004/cross-contract helpers; verify F001 helper before unification if reused broadly. |
| `const` | Discord username, MCP JSON-RPC method/version | Present in schemas; shared helper should add explicit support because local helpers currently focus on enum/pattern/format subsets. |
| `integer` | Discord color and MCP JSON-RPC ID | Covered by `matchesSchemaType`/`matchesType` where integer support exists; verify all local variants before extraction. |
| `minimum` | Discord color | Shared helper should support numeric lower bounds if it validates the Discord schema. |

No current schema requires `oneOf`, `anyOf`, `allOf`, `maximum`, `$ref`, or remote schema resolution. A shared test helper should fail closed or explicitly report unsupported keywords if those appear later.

## Proposed shared test-only helper

A future serial/refactor task may add `tests/helpers/schema-validator.ts`. The helper should remain under `tests/` and **must not** be moved to `src/` during the current phase.

Recommended API:

```ts
export type JsonSchema = Record<string, unknown>;

export interface ValidationError {
	path: string;
	message: string;
}

export function validateJsonSchema(
	schema: JsonSchema,
	value: unknown,
	currentPath?: string,
): ValidationError[];
```

Recommended common subset:

- `type`, including union arrays and `integer`.
- `const` and `enum`.
- object `required`, `properties`, `additionalProperties: false`, `additionalProperties: true`, and schema-valued `additionalProperties`.
- array `items` and `minItems`.
- string `minLength`, `pattern`, `format: uri`, `format: date`, and `format: date-time`.
- numeric `minimum` for the Discord embed color field.
- deterministic unsupported-keyword errors for schema features not in the agreed subset.

## Affected feature tests

| Feature / scope | Affected tests | Migration note |
| --- | --- | --- |
| F001 | `tests/f001-idempotency-contract.test.ts` | Must preserve schema-valued `additionalProperties` for crawler-state source maps. |
| F002 | `tests/f002-content-guards.test.ts` | Must preserve `format: date`, `enum`, frontmatter fixture error paths, and YAML/frontmatter parsing stays local to the test. |
| F003 | `tests/f003-mcp-contract-fixtures.test.ts` | Must preserve MCP envelope fixture validation and allow `additionalProperties: true` for tool arguments. |
| F004 | `tests/f004-cloudflare-discord.test.ts` | Must preserve Cloudflare/Discord `uri`, `date-time`, `pattern`, `minItems`, and Discord payload checks. |
| Cross-cutting | `tests/contracts.test.ts` | Should reuse the same helper after feature tests are migrated, avoiding a sixth validator copy. |

## Recommended next actions

1. Add `tests/helpers/schema-validator.ts` in a later refactor PR, not in this audit PR.
2. Migrate one feature test at a time to avoid changing schema error expectations across all features at once.
3. Add helper self-tests under `tests/helpers/` or a dedicated contract test before deleting local validator copies.
4. Keep the helper test-only; do not import it from `src/` and do not move it into production code.
5. After migration, rerun `rg "function validateJsonSchema|function matchesType|function matchesSchemaType|type JsonSchema = Record<string, unknown>" tests .spec src` to verify only the shared helper and intentional type exports remain.
