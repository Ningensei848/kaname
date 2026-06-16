export type GuardSeverity = "error" | "warning" | "info";

export type ContentGuardName =
	| "topic-frontmatter"
	| "immutable-path"
	| "no-overwrite"
	| "internal-link"
	| "orphan-score-regression"
	| "report-novelty";

export interface GuardViolation {
	guard: ContentGuardName;
	severity: GuardSeverity;
	message: string;
	path?: string;
	line?: number;
	code?: string;
}

export interface GuardResult {
	ok: boolean;
	errors: string[];
	violations?: GuardViolation[];
}

export interface VaultDocument {
	path: string;
	title: string;
	markdown: string;
}

export interface ContentGuardContext {
	currentRunDate: string;
	changedPaths: string[];
	beforeVault: VaultDocument[];
	afterVault: VaultDocument[];
	knownTitles: ReadonlySet<string>;
	aliases?: TopicAliasMap;
}

export interface TopicAliasMap {
	[keywordAlias: string]: {
		resolvedFilePath: string;
		primaryTitle: string;
	};
}
