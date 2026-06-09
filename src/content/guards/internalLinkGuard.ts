import type { GuardResult } from "./types";

export function internalLinkGuard(
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

export function collectInternalLinks(markdown: string): string[] {
	return [...markdown.matchAll(/\[\[([^\]|]+)(?:\|[^\]]+)?\]\]/g)].map(
		(match) => match[1],
	);
}
