import type { GuardResult } from "./types";
export type ReportNoveltyContext = readonly string[];
export interface ReportNoveltyGuardInput {
	readonly candidate: string;
	readonly references: ReportNoveltyContext;
	readonly maxDuplicateRatio?: number;
}
export type ReportNoveltyGuardResult = GuardResult;
