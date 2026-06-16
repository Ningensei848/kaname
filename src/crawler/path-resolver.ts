export interface TopicPathResolutionInput {
	readonly topicName: string;
	readonly baseDir: string;
	readonly maxDirectories?: number;
}
export interface TopicPathResolution {
	readonly filePath: string;
	readonly sanitizedName: string;
	readonly directoryCount: number;
}
