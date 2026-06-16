import type { GuardResult } from "./types";
export interface NoOverwriteGuardInput {
	readonly before: string;
	readonly after: string;
}
export type NoOverwriteGuardResult = GuardResult;
