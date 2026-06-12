import type { GuardResult, VaultDocument } from "./types";

export interface OrphanScoreRegressionGuardInput {
	beforeVault: VaultDocument[];
	afterVault: VaultDocument[];
}

export type OrphanScoreRegressionGuardResult = GuardResult;
