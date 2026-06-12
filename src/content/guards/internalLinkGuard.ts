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
