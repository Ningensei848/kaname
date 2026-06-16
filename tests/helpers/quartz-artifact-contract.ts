export interface QuartzHtmlArtifact {
	path: string;
	html: string;
}

export interface QuartzGraphDisabledArtifact extends QuartzHtmlArtifact {
	expectedGraphDisabled: true;
}

export type QuartzGraphArtifactContract =
	| QuartzHtmlArtifact
	| QuartzGraphDisabledArtifact;

const forbiddenGraphPatterns = [
	/\bGraph View\b/i,
	/\bglobal-graph\b/i,
	/\blocal-graph\b/i,
	/\bgraph\.inline\.js\b/i,
	/data-component=["']Graph["']/i,
];

export function assertQuartzGraphDisabledArtifact(
	artifacts: QuartzGraphArtifactContract[],
): string[] {
	const violations: string[] = [];
	for (const artifact of artifacts) {
		for (const pattern of forbiddenGraphPatterns) {
			if (pattern.test(artifact.html)) {
				violations.push(`${artifact.path} contains ${pattern}`);
			}
		}
	}
	return violations;
}
