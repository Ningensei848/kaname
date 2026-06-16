export interface MarkdownSectionAppendInput {
	readonly markdown: string;
	readonly heading: string;
	readonly content: string;
}
export interface InternalLinkInjectionInput {
	readonly markdown: string;
	readonly targetTitle: string;
	readonly aliases?: readonly string[];
}
export type MarkdownUpdaterResult = string;
