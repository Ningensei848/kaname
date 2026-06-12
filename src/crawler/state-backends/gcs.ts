import type { CrawlerState } from "../../types";
import type { SaveStateOptions, StateBackendAdapter } from "../state";

export type FetchLike = (
	input: string | URL | Request,
	init?: RequestInit,
) => Promise<Response>;

export interface GcsStateBackendOptions {
	bucket: string;
	objectName?: string;
	accessToken?: string;
	fetch?: FetchLike;
	fetchFn?: FetchLike;
	apiBaseUrl?: string;
}

export interface GcsObjectMetadata {
	generation: string | null;
	contentType?: string;
	updated?: string;
}

export interface GcsStateSnapshot {
	state: CrawlerState;
	generation: string | null;
	metadata?: GcsObjectMetadata;
}

export declare class GcsStateBackend
	implements StateBackendAdapter<CrawlerState>
{
	readonly bucket: string;
	readonly objectName: string;
	constructor(options: GcsStateBackendOptions);
	load(): Promise<GcsStateSnapshot>;
	save(
		state: CrawlerState,
		options?: SaveStateOptions,
	): Promise<GcsStateSnapshot>;
}
