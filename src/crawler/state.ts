import * as crypto from "node:crypto";
import * as fs from "node:fs";
import * as path from "node:path";
import type { CrawlerState } from "../types";

export function calculateHash(content: string): string {
	return crypto.createHash("sha256").update(content, "utf8").digest("hex");
}

export function loadCrawlerState(filePath: string): CrawlerState {
	if (!fs.existsSync(filePath)) {
		// Return a default initial state
		return {
			last_execution: new Date(0).toISOString(),
			sources: {},
		};
	}

	try {
		const raw = fs.readFileSync(filePath, "utf8");
		const parsed = JSON.parse(raw);
		if (
			parsed &&
			typeof parsed === "object" &&
			parsed.sources &&
			typeof parsed.sources === "object"
		) {
			return parsed as CrawlerState;
		}
	} catch (error) {
		console.warn(
			`Failed to parse crawler state file at ${filePath}. Starting with initial state. Error: ${(error as Error).message}`,
		);
	}

	return {
		last_execution: new Date(0).toISOString(),
		sources: {},
	};
}

export function saveCrawlerState(filePath: string, state: CrawlerState): void {
	const dir = path.dirname(filePath);
	if (!fs.existsSync(dir)) {
		fs.mkdirSync(dir, { recursive: true });
	}

	fs.writeFileSync(filePath, JSON.stringify(state, null, 2), "utf8");
}

export function updateSourceState(
	state: CrawlerState,
	sourceId: string,
	contentHash: string,
	lastModifiedHeader: string | null,
): CrawlerState {
	const now = new Date().toISOString();

	const sourcesUpdate = {
		...state.sources,
		[sourceId]: {
			last_checked: now,
			content_hash: contentHash,
			last_modified_header: lastModifiedHeader,
		},
	};

	return {
		last_execution: now,
		sources: sourcesUpdate,
	};
}
