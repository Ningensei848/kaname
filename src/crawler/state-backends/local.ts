import type { CrawlerState } from "../../types";
import type { StateBackendAdapter, StateSnapshot } from "../state";

export interface LocalFileStateBackendOptions {
	filePath: string;
}

export interface LocalFileStateBackend
	extends StateBackendAdapter<CrawlerState> {
	readonly filePath: string;
}

export type LocalCrawlerStateSnapshot = StateSnapshot<CrawlerState>;

export type LocalStatePersistenceResult =
	| { ok: true; snapshot: LocalCrawlerStateSnapshot }
	| { ok: false; reason: "not_found" | "invalid_json" | "invalid_shape" };
