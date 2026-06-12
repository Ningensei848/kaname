export type GuardStatus = "passed" | "failed";

export interface GuardResult {
	ok: boolean;
	errors: string[];
	passed?: boolean;
	reasons?: string[];
}

export interface VaultDocument {
	title: string;
	path: string;
	markdown: string;
}

export interface TopicAliasTarget {
	resolvedFilePath: string;
	primaryTitle: string;
	aliases?: string[];
}

export type TopicAliasMap = Record<string, TopicAliasTarget | string[]>;

export type ContentGuardVerdict =
	| { guard: string; status: "passed"; reasons?: readonly string[] }
	| { guard: string; status: "failed"; reasons: readonly string[] };
