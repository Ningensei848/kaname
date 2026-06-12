import type { CrawlerState, SourceState } from "../types";

export interface StateSnapshot<T> {
	state: T;
	generation: string | null;
}

export interface SaveStateOptions {
	expectedGeneration?: string | null;
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

export type StateConflictError = {
	name: "StateConflictError";
	message: string;
	expectedGeneration: string | null;
	currentGeneration: string | null;
	cause?: unknown;
};
