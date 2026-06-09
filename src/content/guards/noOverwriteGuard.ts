import type { GuardResult } from "./types";

export function noOverwriteGuard(before: string, after: string): GuardResult {
	const beforeLines = parseMarkdownBody(before)
		.split(/\r?\n/)
		.filter((line) => line.trim().length > 0);
	const afterLines = parseMarkdownBody(after).split(/\r?\n/);
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

function parseMarkdownBody(markdown: string): string {
	const match = /^---\n([\s\S]*?)\n---\n?([\s\S]*)$/.exec(markdown);
	return match ? match[2] : markdown;
}
