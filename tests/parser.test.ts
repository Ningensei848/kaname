import { test } from "node:test";
import * as assert from "node:assert";
import * as fs from "node:fs";
import * as path from "node:path";
import { parseSsotYaml } from "../src/crawler/parser";

const tempDir = path.join(__dirname, "temp");

test("SSoT Parser Tests", async (t) => {
	if (!fs.existsSync(tempDir)) {
		fs.mkdirSync(tempDir, { recursive: true });
	}

	await t.test("should parse valid SSoT YAML correctly", () => {
		const yamlPath = path.join(tempDir, "valid_ssot.yml");
		const yamlContent = `
ssot_sources:
  - id: jpcert
    name: JPCERT/CC
    url: https://www.jpcert.or.jp/
    description: Security alerts and incidents
    feed_url: https://www.jpcert.or.jp/rss/jpcert.rdf
    custom_extraction_instruction: Extract latest alerts
`;
		fs.writeFileSync(yamlPath, yamlContent, "utf8");

		const sources = parseSsotYaml(yamlPath);
		assert.strictEqual(sources.length, 1);
		assert.strictEqual(sources[0].id, "jpcert");
		assert.strictEqual(sources[0].name, "JPCERT/CC");
		assert.strictEqual(sources[0].url, "https://www.jpcert.or.jp/");
		assert.strictEqual(sources[0].description, "Security alerts and incidents");
		assert.strictEqual(
			sources[0].feed_url,
			"https://www.jpcert.or.jp/rss/jpcert.rdf",
		);
		assert.strictEqual(
			sources[0].custom_extraction_instruction,
			"Extract latest alerts",
		);

		fs.unlinkSync(yamlPath);
	});

	await t.test(
		"should skip invalid sources and transition to degraded operation",
		() => {
			const yamlPath = path.join(tempDir, "invalid_ssot.yml");
			const yamlContent = `
ssot_sources:
  - id: valid_one
    name: Valid Source
    url: https://example.com
    description: A valid source
  - id: invalid-id
    name: Source with bad ID pattern
    url: https://example.com
    description: Bad ID
  - id: missing_name
    url: https://example.com
    description: Missing name
  - id: invalid_url
    name: Bad URL
    url: not-a-url
    description: Bad URL
`;
			fs.writeFileSync(yamlPath, yamlContent, "utf8");

			const sources = parseSsotYaml(yamlPath);
			assert.strictEqual(sources.length, 1);
			assert.strictEqual(sources[0].id, "valid_one");

			fs.unlinkSync(yamlPath);
		},
	);

	await t.test("should throw error when ssot_sources list is missing", () => {
		const yamlPath = path.join(tempDir, "missing_list.yml");
		const yamlContent = `
wrong_root:
  - id: one
    name: One
    url: https://example.com
    description: One
`;
		fs.writeFileSync(yamlPath, yamlContent, "utf8");

		assert.throws(() => {
			parseSsotYaml(yamlPath);
		}, /missing ssot_sources list/);

		fs.unlinkSync(yamlPath);
	});

	await t.test("should throw error when file does not exist", () => {
		assert.throws(() => {
			parseSsotYaml(path.join(tempDir, "non_existent.yml"));
		}, /SSoT configuration file not found/);
	});

	// Clean up
	if (fs.existsSync(tempDir)) {
		fs.rmdirSync(tempDir);
	}
});
