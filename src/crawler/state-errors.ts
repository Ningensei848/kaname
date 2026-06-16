export interface StateConflictDetails {
	readonly expectedGeneration?: string;
	readonly currentGeneration?: string;
	readonly cause?: unknown;
}
export type StateConflictError = Error & StateConflictDetails;
