import type { CrawlerState } from "../../types";
import type { StateBackendAdapter } from "../state";

export type FetchLike = (
	input: string | URL | Request,
	init?: RequestInit,
) => Promise<Response>;

export interface GcsStateBackendOptions {
	bucket: string;
	objectName: string;
	accessToken: string;
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

export interface GcsStateBackend extends StateBackendAdapter<CrawlerState> {
	readonly bucket: string;
	readonly objectName: string;
}
