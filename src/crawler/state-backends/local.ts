import type { StateBackendAdapter } from "../state";
import type { CrawlerState } from "../../types";
export interface LocalFileStateBackendOptions {
	readonly filePath: string;
}
export type LocalFileStateBackend = StateBackendAdapter<CrawlerState>;
