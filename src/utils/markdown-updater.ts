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
