import { collectInternalLinks } from "./internalLinkGuard";
import type { GuardResult } from "./types";

export function reportNoveltyGuard(
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
