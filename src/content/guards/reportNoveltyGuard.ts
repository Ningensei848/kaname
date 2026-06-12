import type { GuardResult, VaultDocument } from "./types";

export type ReportNoveltyContext = string | string[] | VaultDocument[];

export interface ReportNoveltyOptions {
	sentenceSimilarityThreshold?: number;
	nGramSize?: number;
	duplicateThreshold?: number;
}

export interface ReportNoveltyGuardInput {
	reportMarkdown: string;
	contexts: ReportNoveltyContext;
	options?: ReportNoveltyOptions;
}

export type ReportNoveltyGuardResult = GuardResult;

export declare function reportNoveltyGuard(
	reportMarkdown: string,
	contexts: ReportNoveltyContext,
	options?: ReportNoveltyOptions,
): GuardResult;
