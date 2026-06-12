import type { GuardResult, TopicAliasMap, VaultDocument } from "./types";

export type LinkAliasSource = string[] | TopicAliasMap;

export interface InternalLinkGuardInput {
	beforeMarkdown: string;
	afterMarkdown: string;
	vault: VaultDocument[];
	aliases?: LinkAliasSource;
}

export type InternalLinkGuardResult = GuardResult;

export interface InternalLinkCollection {
	links: string[];
	malformed: boolean;
}

export declare function internalLinkGuard(
	markdown: string,
	knownTitles: Iterable<string>,
	aliases?: TopicAliasMap,
): GuardResult;
export declare function collectInternalLinks(markdown: string): string[];
