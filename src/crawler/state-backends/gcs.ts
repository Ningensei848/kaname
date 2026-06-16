import type { StateBackendAdapter } from "../state";
import type { CrawlerState } from "../../types";
export type FetchLike = (url: string, init?: RequestInit) => Promise<Response>;
export interface GcsStateBackendOptions {
	readonly bucket: string;
	readonly objectName?: string;
	readonly fetch?: FetchLike;
	readonly accessToken?: string;
}
export type GcsCrawlerStateBackend = StateBackendAdapter<CrawlerState>;
