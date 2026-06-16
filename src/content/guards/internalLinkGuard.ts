import type { GuardResult, LinkAliasSource } from "./types";
export interface InternalLinkGuardInput {
	readonly markdown: string;
	readonly knownTopics: readonly string[];
	readonly aliases?: LinkAliasSource;
}
export type InternalLinkGuardResult = GuardResult;
