/**
 * Feature 002 deterministic content guard executable tests.
 *
 * Scope: test-code-first contracts only. These tests encode the reviewer/CI
 * expectations for destructive Markdown changes, topic frontmatter, link graph
 * quality, orphan-score regression, and report novelty without introducing
 * production guard modules yet.
 *
 * Acceptance source: `.spec/features/002-wiki-incremental-update/*` and
 * `.spec/policies/content-integrity-policy.md`.
 */

import * as assert from "node:assert";
import * as fs from "node:fs";
import * as path from "node:path";
import { test } from "node:test";
import * as YAML from "yaml";

type JsonSchema = Record<string, unknown>;
type JsonObject = Record<string, unknown>;

interface ValidationError {
	path: string;
	message: string;
}

interface MarkdownDocument {
	frontmatter: JsonObject;
	body: string;
}

interface GuardResult {
	ok: boolean;
	errors: string[];
}

interface VaultDocument {
	path: string;
	title: string;
	markdown: string;
}

function fixturePath(...segments: string[]): string {
	return path.join(__dirname, "fixtures", "f002", ...segments);
}

function readFixture(...segments: string[]): string {
	return fs.readFileSync(fixturePath(...segments), "utf8");
}

function readJson(filePath: string): unknown {
	return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function parseMarkdown(markdown: string): MarkdownDocument {
	const match = /^---\n([\s\S]*?)\n---\n?([\s\S]*)$/.exec(markdown);
	if (!match) return { frontmatter: {}, body: markdown };
	return {
		frontmatter: (YAML.parse(match[1]) ?? {}) as JsonObject,
		body: match[2],
	};
}

function validateJsonSchema(
	schema: JsonSchema,
	value: unknown,
	currentPath = "$",
): ValidationError[] {
	const errors: ValidationError[] = [];
	const typeRule = schema.type;

	if (typeRule !== undefined && !matchesType(typeRule, value)) {
		errors.push({
			path: currentPath,
			message: `expected type ${JSON.stringify(typeRule)}`,
		});
		return errors;
	}

	if (
		schema.enum &&
		Array.isArray(schema.enum) &&
		!schema.enum.includes(value)
	) {
		errors.push({ path: currentPath, message: "expected enum value" });
	}

	if (schema.type === "object" && isRecord(value)) {
		const properties = isRecord(schema.properties) ? schema.properties : {};
		const required = Array.isArray(schema.required) ? schema.required : [];

		for (const requiredKey of required) {
			if (typeof requiredKey === "string" && !(requiredKey in value)) {
				errors.push({
					path: currentPath,
					message: `missing required property ${requiredKey}`,
				});
			}
		}

		if (schema.additionalProperties === false) {
			for (const key of Object.keys(value)) {
				if (!(key in properties)) {
					errors.push({
						path: `${currentPath}.${key}`,
						message: "additional property is not allowed",
					});
				}
			}
		}

		for (const [key, propertySchema] of Object.entries(properties)) {
			if (key in value && isRecord(propertySchema)) {
				errors.push(
					...validateJsonSchema(
						propertySchema,
						value[key],
						`${currentPath}.${key}`,
					),
				);
			}
		}
	}

	if (schema.type === "array" && Array.isArray(value)) {
		if (typeof schema.minItems === "number" && value.length < schema.minItems) {
			errors.push({
				path: currentPath,
				message: `expected at least ${schema.minItems} items`,
			});
		}

		if (isRecord(schema.items)) {
			value.forEach((item, index) => {
				errors.push(
					...validateJsonSchema(
						schema.items as JsonSchema,
						item,
						`${currentPath}[${index}]`,
					),
				);
			});
		}
	}

	if (typeof value === "string") {
		if (
			typeof schema.minLength === "number" &&
			value.length < schema.minLength
		) {
			errors.push({
				path: currentPath,
				message: `expected minimum length ${schema.minLength}`,
			});
		}

		if (
			typeof schema.pattern === "string" &&
			!new RegExp(schema.pattern).test(value)
		) {
			errors.push({
				path: currentPath,
				message: `expected to match ${schema.pattern}`,
			});
		}

		if (schema.format === "date" && !/^\d{4}-\d{2}-\d{2}$/.test(value)) {
			errors.push({ path: currentPath, message: "expected date format" });
		}
	}

	return errors;
}

function matchesType(typeRule: unknown, value: unknown): boolean {
	const allowedTypes = Array.isArray(typeRule) ? typeRule : [typeRule];
	return allowedTypes.some((type) => {
		switch (type) {
			case "object":
				return isRecord(value) && !Array.isArray(value);
			case "array":
				return Array.isArray(value);
			case "string":
				return typeof value === "string";
			case "null":
				return value === null;
			default:
				return false;
		}
	});
}

function isRecord(value: unknown): value is JsonObject {
	return value !== null && typeof value === "object" && !Array.isArray(value);
}

function validateTopicFrontmatter(
	markdown: string,
	schema: JsonSchema,
): GuardResult {
	const document = parseMarkdown(markdown);
	const errors = validateJsonSchema(schema, document.frontmatter).map(
		(error) => `${error.path}: ${error.message}`,
	);
	return { ok: errors.length === 0, errors };
}

function immutablePathGuard(
	changedPaths: string[],
	currentRunDate: string,
): GuardResult {
	const errors = changedPaths.filter((changedPath) => {
		if (changedPath === "ssot.yml") return true;
		const reportMatch = /^reports\/(\d{4}-\d{2}-\d{2})_Report\.md$/.exec(
			changedPath,
		);
		return reportMatch ? reportMatch[1] < currentRunDate : false;
	});
	return {
		ok: errors.length === 0,
		errors: errors.map(
			(changedPath) => `${changedPath} is immutable for this run`,
		),
	};
}

function noOverwriteGuard(before: string, after: string): GuardResult {
	const beforeLines = parseMarkdown(before)
		.body.split(/\r?\n/)
		.filter((line) => line.trim().length > 0);
	const afterLines = parseMarkdown(after).body.split(/\r?\n/);
	const errors: string[] = [];
	let searchFrom = 0;

	for (const line of beforeLines) {
		const foundAt = afterLines.findIndex(
			(candidate, index) => index >= searchFrom && candidate === line,
		);
		if (foundAt === -1) {
			errors.push(`existing line was removed or modified: ${line}`);
			continue;
		}
		searchFrom = foundAt + 1;
	}

	return { ok: errors.length === 0, errors };
}

function collectInternalLinks(markdown: string): string[] {
	return [...markdown.matchAll(/\[\[([^\]|]+)(?:\|[^\]]+)?\]\]/g)].map(
		(match) => match[1],
	);
}

function internalLinkGuard(
	markdown: string,
	knownTitles: Set<string>,
): GuardResult {
	const errors: string[] = [];
	if (/\[\[\[\[|\]\]\]\]/.test(markdown)) {
		errors.push("internal link is double-wrapped");
	}

	for (const link of collectInternalLinks(markdown)) {
		if (!knownTitles.has(link)) {
			errors.push(`broken internal link: ${link}`);
		}
	}

	return { ok: errors.length === 0, errors };
}

function orphanScoreRegressionGuard(
	beforeVault: VaultDocument[],
	afterVault: VaultDocument[],
	allowedNewHighSeverityOrphans = 0,
): GuardResult {
	const before = orphanTitles(beforeVault);
	const after = orphanTitles(afterVault);
	const newOrphans = [...after].filter((title) => !before.has(title));
	const errors =
		newOrphans.length > allowedNewHighSeverityOrphans
			? [
					`orphan score regressed: ${newOrphans.length} new orphan(s): ${newOrphans.join(", ")}`,
				]
			: [];
	return { ok: errors.length === 0, errors };
}

function orphanTitles(vault: VaultDocument[]): Set<string> {
	const titles = new Set(vault.map((document) => document.title));
	const degrees = new Map([...titles].map((title) => [title, 0]));

	for (const document of vault) {
		const uniqueLinks = new Set(collectInternalLinks(document.markdown));
		for (const link of uniqueLinks) {
			if (!titles.has(link)) continue;
			degrees.set(document.title, (degrees.get(document.title) ?? 0) + 1);
			degrees.set(link, (degrees.get(link) ?? 0) + 1);
		}
	}

	return new Set(
		[...degrees.entries()]
			.filter(([, degree]) => degree === 0)
			.map(([title]) => title),
	);
}

function reportNoveltyGuard(
	reportMarkdown: string,
	existingTopicMarkdown: string,
	options: { duplicateThreshold: number; createsNewRootTopic?: boolean },
): GuardResult {
	const errors: string[] = [];
	const duplicateRatio = calculateDuplicateRatio(
		reportMarkdown,
		existingTopicMarkdown,
	);
	const hasEvidence =
		/https?:\/\//.test(reportMarkdown) || /根拠\s*[:：]/.test(reportMarkdown);
	const hasInternalLink = collectInternalLinks(reportMarkdown).length > 0;

	if (duplicateRatio > options.duplicateThreshold) {
		errors.push(
			`duplicate report threshold exceeded: ${duplicateRatio.toFixed(2)} > ${options.duplicateThreshold}`,
		);
	}
	if (!hasEvidence) errors.push("report item lacks source evidence");
	if (!options.createsNewRootTopic && !hasInternalLink) {
		errors.push("report item lacks required internal link");
	}

	return { ok: errors.length === 0, errors };
}

function calculateDuplicateRatio(candidate: string, reference: string): number {
	const candidateSentences = normalizeJapaneseSentences(candidate);
	const referenceSentences = new Set(normalizeJapaneseSentences(reference));
	if (candidateSentences.length === 0) return 0;
	const duplicateCount = candidateSentences.filter((sentence) =>
		referenceSentences.has(sentence),
	).length;
	return duplicateCount / candidateSentences.length;
}

function normalizeJapaneseSentences(markdown: string): string[] {
	return markdown
		.replace(/^---[\s\S]*?---/m, "")
		.replace(/\[\[([^\]|]+)(?:\|[^\]]+)?\]\]/g, "$1")
		.split(/[。\n]/)
		.map((sentence) => sentence.replace(/^[-*#\s]+/, "").trim())
		.filter(
			(sentence) =>
				sentence.length >= 12 && !/^title:|^tags:|^source_ids:/.test(sentence),
		);
}

test("F002 topic frontmatter schema guard", async (t) => {
	const schema = readJson(
		".spec/schemas/topic-frontmatter.schema.json",
	) as JsonSchema;

	await t.test(
		"valid topic frontmatter satisfies the executable schema",
		() => {
			const result = validateTopicFrontmatter(
				readFixture("topics", "before", "nco.md"),
				schema,
			);
			assert.deepStrictEqual(result, { ok: true, errors: [] });
		},
	);

	await t.test(
		"invalid topic frontmatter rejects empty titles, bad tags, empty sources, bad dates, and unknown keys",
		() => {
			const result = validateTopicFrontmatter(
				readFixture("topics", "after", "nco.invalid-frontmatter.md"),
				schema,
			);
			assert.strictEqual(result.ok, false);
			assert.ok(result.errors.some((error) => error.startsWith("$.title")));
			assert.ok(result.errors.some((error) => error.startsWith("$.tags[0]")));
			assert.ok(
				result.errors.some((error) => error.startsWith("$.source_ids")),
			);
			assert.ok(result.errors.some((error) => error.startsWith("$.updated")));
			assert.ok(
				result.errors.some((error) => error.startsWith("$.unexpected")),
			);
		},
	);
});

test("F002 immutable path and no-overwrite guards", async (t) => {
	await t.test(
		"immutable files and past reports are blocked while current report and topics are mutable",
		() => {
			const result = immutablePathGuard(
				[
					"ssot.yml",
					"reports/2026-05-26_Report.md",
					"reports/2026-05-27_Report.md",
					"topics/gov-agencies/NCO.md",
				],
				"2026-05-27",
			);
			assert.strictEqual(result.ok, false);
			assert.deepStrictEqual(result.errors, [
				"ssot.yml is immutable for this run",
				"reports/2026-05-26_Report.md is immutable for this run",
			]);
		},
	);

	await t.test(
		"incremental topic update preserves every existing body line in order",
		() => {
			const result = noOverwriteGuard(
				readFixture("topics", "before", "nco.md"),
				readFixture("topics", "after", "nco.incremental.md"),
			);
			assert.deepStrictEqual(result, { ok: true, errors: [] });
		},
	);

	await t.test(
		"destructive rewrite is rejected because existing facts disappear",
		() => {
			const result = noOverwriteGuard(
				readFixture("topics", "before", "nco.md"),
				readFixture("topics", "after", "nco.destructive.md"),
			);
			assert.strictEqual(result.ok, false);
			assert.ok(
				result.errors.some((error) => error.includes("政府は官民連携")),
			);
		},
	);
});

test("F002 internal link graph guard", async (t) => {
	const knownTitles = new Set([
		"能動的サイバー防御",
		"JPCERT_CC",
		"サイバー演習CYDER",
	]);

	await t.test(
		"valid incremental links resolve against the known vault title set",
		() => {
			const result = internalLinkGuard(
				readFixture("topics", "after", "nco.incremental.md"),
				knownTitles,
			);
			assert.deepStrictEqual(result, { ok: true, errors: [] });
		},
	);

	await t.test(
		"broken links fail deterministic validation before Reviewer approval",
		() => {
			const result = internalLinkGuard(
				readFixture("topics", "after", "nco.broken-link.md"),
				knownTitles,
			);
			assert.strictEqual(result.ok, false);
			assert.ok(
				result.errors.includes("broken internal link: 存在しないトピック"),
			);
		},
	);

	await t.test("double-wrapped Obsidian links are rejected", () => {
		const result = internalLinkGuard(
			readFixture("topics", "after", "nco.double-wrapped.md"),
			knownTitles,
		);
		assert.strictEqual(result.ok, false);
		assert.ok(result.errors.includes("internal link is double-wrapped"));
	});
});

test("F002 orphan score regression guard", async (t) => {
	const beforeVault: VaultDocument[] = [
		{
			path: "topics/NCO.md",
			title: "能動的サイバー防御",
			markdown: "# 能動的サイバー防御\n[[JPCERT_CC]] と連携する。",
		},
		{
			path: "topics/JPCERT_CC.md",
			title: "JPCERT_CC",
			markdown: "# JPCERT_CC\n[[能動的サイバー防御]] を支援する。",
		},
	];

	await t.test(
		"connected updates do not increase high-severity orphan count",
		() => {
			const afterVault = [
				...beforeVault,
				{
					path: "topics/CYDER.md",
					title: "サイバー演習CYDER",
					markdown: "# サイバー演習CYDER\n[[JPCERT_CC]] と訓練面で関連する。",
				},
			];
			const result = orphanScoreRegressionGuard(beforeVault, afterVault);
			assert.deepStrictEqual(result, { ok: true, errors: [] });
		},
	);

	await t.test("new high-severity orphan growth fails CI", () => {
		const afterVault = [
			...beforeVault,
			{
				path: "topics/Isolated.md",
				title: "孤立新規トピック",
				markdown: "# 孤立新規トピック\nどの既存トピックにも接続していない。",
			},
		];
		const result = orphanScoreRegressionGuard(beforeVault, afterVault);
		assert.strictEqual(result.ok, false);
		assert.ok(result.errors[0].includes("孤立新規トピック"));
	});
});

test("F002 report novelty and duplicate suppression guard", async (t) => {
	const existingTopic = readFixture("topics", "before", "nco.md");

	await t.test(
		"valid delta report has source evidence and an internal link while staying below duplicate threshold",
		() => {
			const result = reportNoveltyGuard(
				readFixture("reports", "valid-delta.md"),
				existingTopic,
				{ duplicateThreshold: 0.4 },
			);
			assert.deepStrictEqual(result, { ok: true, errors: [] });
		},
	);

	await t.test(
		"duplicated explanation without internal links is rejected",
		() => {
			const result = reportNoveltyGuard(
				readFixture("reports", "duplicate-without-link.md"),
				existingTopic,
				{ duplicateThreshold: 0.2 },
			);
			assert.strictEqual(result.ok, false);
			assert.ok(
				result.errors.some((error) =>
					error.startsWith("duplicate report threshold exceeded"),
				),
			);
			assert.ok(
				result.errors.includes("report item lacks required internal link"),
			);
		},
	);
});

test.todo(
	"F002 production deterministic guard module exports the same verdicts as these executable fixtures",
);
test.todo(
	"F002 CI wires no-overwrite, frontmatter, link graph, orphan, and duplicate guards before Reviewer approval",
);
