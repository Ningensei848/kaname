import type { GuardResult } from "./types";

export interface NoOverwriteGuardInput {
	beforeMarkdown: string;
	afterMarkdown: string;
}

export type NoOverwriteGuardResult = GuardResult;
