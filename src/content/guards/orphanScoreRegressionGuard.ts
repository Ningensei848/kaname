import { collectInternalLinks } from "./internalLinkGuard";
import type { GuardResult, VaultDocument } from "./types";

export function orphanScoreRegressionGuard(
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
