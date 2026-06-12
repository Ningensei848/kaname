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

export declare function fetchWithRetry(
	url: string,
	retries?: number,
	delayMs?: number,
	lastModifiedHeader?: string | null,
	fetcher?: Fetcher,
): Promise<FetchResult>;
export declare function cleanHtml(html: string): string;
export declare function parseRssFeed(xml: string): string;
export declare function crawlSource(
	source: SsotSource,
	lastModifiedHeader?: string | null,
	options?: CrawlSourceOptions,
): Promise<CrawlSourceResult>;
