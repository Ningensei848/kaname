export interface AppendSectionRequest {
	markdown: string;
	heading: string;
	content: string;
}

export interface InjectInternalLinkRequest {
	markdown: string;
	targetTitle: string;
	aliases?: string[];
}

export type MarkdownUpdateOperation =
	| { kind: "append_section"; input: AppendSectionRequest }
	| { kind: "inject_internal_link"; input: InjectInternalLinkRequest };

export interface MarkdownUpdateResult {
	markdown: string;
	changed: boolean;
}

export declare function appendSectionToMarkdown(
	markdown: string,
	heading: string,
	content: string,
): string;
export declare function injectInternalLinkToMarkdown(
	markdown: string,
	targetTitle: string,
	aliases?: string[],
): string;
