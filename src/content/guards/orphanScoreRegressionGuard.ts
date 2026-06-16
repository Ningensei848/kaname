import type { GuardResult, VaultDocument } from "./types";
export interface OrphanScoreRegressionGuardInput {
	readonly before: readonly VaultDocument[];
	readonly after: readonly VaultDocument[];
}
export type OrphanScoreRegressionGuardResult = GuardResult;
