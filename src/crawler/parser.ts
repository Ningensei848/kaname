import type { SsotSource } from "../types";

export interface ParsedSsotYaml {
	ssot_sources: SsotSource[];
}

export interface SourceCandidate {
	id?: unknown;
	name?: unknown;
	url?: unknown;
	feed_url?: unknown;
	description?: unknown;
	meta_url?: unknown;
	custom_extraction_instruction?: unknown;
}

export type SsotParseIssue =
	| { kind: "yaml_syntax"; message: string }
	| { kind: "root_shape"; message: string }
	| { kind: "source_shape"; index: number; message: string }
	| { kind: "unknown_key"; path: string; key: string };

export type SsotParseResult =
	| { ok: true; sources: SsotSource[] }
	| { ok: false; issues: SsotParseIssue[] };
