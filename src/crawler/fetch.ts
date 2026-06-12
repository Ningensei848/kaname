import type { SsotSource } from "../types";

export interface FetchResult {
	content: string;
	lastModifiedHeader: string | null;
}

export type Fetcher = (
	input: string | URL | Request,
	init?: RequestInit,
) => Promise<Response>;

export interface CrawlSourceOptions {
	fetcher?: Fetcher;
	retries?: number;
	delayMs?: number;
}

export interface CrawlSourceResult {
	content: string;
	lastModifiedHeader: string | null;
	isNotModified: boolean;
}

export interface CrawlSourceRequest {
	source: SsotSource;
	lastModifiedHeader?: string | null;
	options?: CrawlSourceOptions;
}
