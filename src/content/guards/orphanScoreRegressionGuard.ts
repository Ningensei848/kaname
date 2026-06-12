import type { GuardResult, VaultDocument } from "./types";

export interface OrphanScoreRegressionGuardInput {
	beforeVault: VaultDocument[];
	afterVault: VaultDocument[];
}

export type OrphanScoreRegressionGuardResult = GuardResult;

export declare function orphanScoreRegressionGuard(
	beforeVault: VaultDocument[],
	afterVault: VaultDocument[],
): GuardResult;
