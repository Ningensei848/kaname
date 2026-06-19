import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import { validateJsonSchema, type JsonSchema } from "./schema-validator";

function readSchema(schemaPath: string): JsonSchema {
	return JSON.parse(fs.readFileSync(schemaPath, "utf8")) as JsonSchema;
}

test("ssot schema validates URI formats deterministically", () => {
	const schema = readSchema(".spec/schemas/ssot.schema.json");
	const validPayload = {
		ssot_sources: [
			{
				id: "cisa_kev",
				name: "CISA KEV",
				url: "https://www.cisa.gov/known-exploited-vulnerabilities-catalog",
				feed_url: "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
				description: "Known exploited vulnerabilities catalog",
				meta_url: "https://www.cisa.gov/known-exploited-vulnerabilities",
			},
		],
	};
	const invalidPayload = {
		...validPayload,
		ssot_sources: [
			{
				...validPayload.ssot_sources[0],
				url: "not a uri",
			},
		],
	};

	assert.deepEqual(validateJsonSchema(schema, validPayload), []);
	assert.deepEqual(validateJsonSchema(schema, invalidPayload), [
		{ path: "$.ssot_sources[0].url", message: "expected URI format" },
	]);
});

test("crawler state schema validates nested source-map additionalProperties", () => {
	const schema = readSchema(".spec/schemas/crawler-state.schema.json");
	const validPayload = {
		last_execution: "2026-06-19T00:00:00.000Z",
		sources: {
			cisa_kev: {
				content_hash:
					"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
				last_checked: "2026-06-19T00:01:00.000Z",
				last_modified_header: null,
				etag_header: '"abc123"',
				last_status: 200,
			},
		},
	};
	const invalidPayload = {
		...validPayload,
		sources: {
			cisa_kev: {
				...validPayload.sources.cisa_kev,
				content_hash: "not-a-sha256",
			},
		},
	};

	assert.deepEqual(validateJsonSchema(schema, validPayload), []);
	assert.deepEqual(validateJsonSchema(schema, invalidPayload), [
		{
			path: "$.sources.cisa_kev.content_hash",
			message: "expected to match ^[0-9a-f]{64}$",
		},
	]);
});

test("topic frontmatter schema validates date format and status enum", () => {
	const schema = readSchema(".spec/schemas/topic-frontmatter.schema.json");
	const validPayload = {
		title: "Network Detection and Response",
		tags: ["detection/network"],
		source_ids: ["cisa_kev"],
		updated: "2026-06-19",
		status: "published",
	};
	const invalidPayload = {
		...validPayload,
		updated: "June 19, 2026",
		status: "released",
	};

	assert.deepEqual(validateJsonSchema(schema, validPayload), []);
	assert.deepEqual(validateJsonSchema(schema, invalidPayload), [
		{ path: "$.updated", message: "expected date format" },
		{ path: "$.status", message: "expected enum value" },
	]);
});

test('discord webhook payload schema rejects username const mismatch for "Aegis-Intelligence"', () => {
	const schema = readSchema(".spec/schemas/discord-webhook-payload.schema.json");
	const validPayload = {
		username: "Aegis-Intelligence",
		avatar_url: "https://example.com/avatar.png",
		embeds: [
			{
				title: "Deployment complete",
				description: "Kaname deployment succeeded.",
				url: "https://example.com/reports/latest",
				color: 65280,
				fields: [
					{ name: "Environment", value: "production", inline: true },
					{ name: "Branch", value: "main", inline: true },
					{ name: "Commit", value: "abc123", inline: false },
				],
				footer: {
					text: "Kaname",
					icon_url: "https://example.com/icon.png",
				},
				timestamp: "2026-06-19T00:00:00.000Z",
			},
		],
	};
	const invalidPayload = {
		...validPayload,
		username: "Kaname",
	};

	assert.deepEqual(validateJsonSchema(schema, validPayload), []);
	assert.deepEqual(validateJsonSchema(schema, invalidPayload), [
		{ path: "$.username", message: "expected const Aegis-Intelligence" },
	]);
});
