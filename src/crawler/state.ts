import type { CrawlerState, SourceState } from "../types";

export interface StateSnapshot<T> {
	state: T;
	generation: string | null;
}

export interface SaveStateOptions {
	expectedGeneration?: string | null;
	ifGenerationMatch?: string | null;
}

export interface StateBackendAdapter<T> {
	load(): Promise<StateSnapshot<T>>;
	save(state: T, options?: SaveStateOptions): Promise<StateSnapshot<T>>;
}

export interface CrawlerStateUpdateInput {
	state: CrawlerState;
	sourceId: string;
	content: string;
	lastModifiedHeader: string | null;
	checkedAt: string;
}

export interface CrawlerSourceStateUpdate {
	sourceId: string;
	state: SourceState;
}

export type CrawlerStateParseResult =
	| { ok: true; state: CrawlerState }
	| { ok: false; reason: "invalid_json" | "invalid_shape" };

export declare class StateConflictError extends Error {
	readonly expectedGeneration: string | null;
	readonly currentGeneration: string | null;
	readonly cause: unknown;
	constructor(
		message: string,
		options: {
			expectedGeneration: string | null;
			currentGeneration?: string | null;
			cause?: unknown;
		},
	);
}

export declare function createInitialCrawlerState(): CrawlerState;
export declare function parseCrawlerState(raw: string): CrawlerState | null;
export declare function calculateHash(content: string): string;
export declare function loadCrawlerState(filePath: string): CrawlerState;
export declare function saveCrawlerState(
	filePath: string,
	state: CrawlerState,
): void;
export declare function updateSourceState(
	state: CrawlerState,
	sourceId: string,
	content: string,
	lastModifiedHeader: string | null,
): CrawlerState;
