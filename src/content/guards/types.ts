export interface GuardResult {
	ok: boolean;
	errors: string[];
}
export interface VaultDocument {
	title: string;
	links: string[];
}
export type TopicAliasMap =
	| Map<string, string>
	| Record<string, string>
	| Iterable<string>;
export type LinkAliasSource = TopicAliasMap | undefined;
