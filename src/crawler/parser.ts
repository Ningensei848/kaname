import type { SsotConfig, SsotSource } from "../types";
export type { SsotConfig, SsotSource };
export interface SsotParseError {
	readonly filePath: string;
	readonly message: string;
}
