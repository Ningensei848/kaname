export type Fetcher = (url: string, init?: RequestInit) => Promise<Response>;
export interface CrawlSourceResult {
	sourceId: string;
	content: string;
	lastModifiedHeader: string | null;
	isNotModified: boolean;
}
export interface FetchRetryOptions {
	readonly maxAttempts?: number;
	readonly timeoutMs?: number;
	readonly retryDelayMs?: number;
}
