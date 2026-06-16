export interface StateBackendSnapshot<TState> {
	readonly state: TState;
	readonly generation: string;
}
export interface StateBackendAdapter<TState> {
	load(): Promise<StateBackendSnapshot<TState>>;
	save(
		state: TState,
		options: { ifGenerationMatch: string },
	): Promise<StateBackendSnapshot<TState>>;
}
export interface StateConflictDetails {
	readonly expectedGeneration?: string;
	readonly currentGeneration?: string;
	readonly cause?: unknown;
}
export type StateConflictError = Error & StateConflictDetails;
