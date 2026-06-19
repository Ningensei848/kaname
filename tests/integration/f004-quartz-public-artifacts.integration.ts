import assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { test } from "node:test";
import { assertQuartzGraphDisabledArtifact } from "../helpers/quartz-artifact-contract";

const repoRoot = process.cwd();
const publicDir = path.join(repoRoot, "public");

function missingEnv(names: string[]): string[] {
	return names.filter((name) => !process.env[name]);
}

function listHtmlFiles(rootDir: string): string[] {
	const entries = fs.readdirSync(rootDir, { withFileTypes: true });
	return entries.flatMap((entry) => {
		const absolutePath = path.join(rootDir, entry.name);
		if (entry.isDirectory()) return listHtmlFiles(absolutePath);
		return entry.isFile() && entry.name.endsWith(".html") ? [absolutePath] : [];
	});
}

test("F004 production Quartz public artifacts contain no graph view UI or scripts", (t) => {
	const missing = missingEnv(["KANAME_RUN_QUARTZ_ARTIFACT_INTEGRATION"]);
	if (missing.length > 0) {
		t.skip(`missing env: ${missing.join(", ")}`);
		return;
	}

	if (!fs.existsSync(publicDir)) {
		t.skip("Missing localized public artifacts directory (public/). Skipping integration check.");
		return;
	}

	const htmlArtifacts = listHtmlFiles(publicDir);
	if (htmlArtifacts.length === 0) {
		t.skip("public/ directory exists but contains zero HTML artifacts. Skipping.");
		return;
	}

	assert.deepStrictEqual(
		assertQuartzGraphDisabledArtifact(
			htmlArtifacts.map((absolutePath) => ({
				path: path.relative(repoRoot, absolutePath),
				html: fs.readFileSync(absolutePath, "utf8"),
			})),
		),
		[],
	);
});
