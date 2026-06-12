import type { CrawlerState } from "../../types";
import type {
	SaveStateOptions,
	StateBackendAdapter,
	StateSnapshot,
} from "../state";

export interface LocalFileStateBackendOptions {
	filePath: string;
}

export declare class LocalFileStateBackend
	implements StateBackendAdapter<CrawlerState>
{
	readonly filePath: string;
	constructor(filePathOrOptions: string | LocalFileStateBackendOptions);
	load(): Promise<StateSnapshot<CrawlerState>>;
	save(
		state: CrawlerState,
		options?: SaveStateOptions,
	): Promise<StateSnapshot<CrawlerState>>;
}

export type LocalCrawlerStateSnapshot = StateSnapshot<CrawlerState>;

export type LocalStatePersistenceResult =
	| { ok: true; snapshot: LocalCrawlerStateSnapshot }
	| { ok: false; reason: "not_found" | "invalid_json" | "invalid_shape" };

export declare function loadCrawlerStateSnapshotFromFile(
	filePath: string,
): StateSnapshot<CrawlerState>;
export declare function loadCrawlerStateFromFile(
	filePath: string,
): CrawlerState;
export declare function saveCrawlerStateToFile(
	filePath: string,
	state: CrawlerState,
	options?: SaveStateOptions,
): StateSnapshot<CrawlerState>;
