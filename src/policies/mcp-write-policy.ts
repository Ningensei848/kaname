export interface McpWritePolicy {
	readonly allowedPathPrefixes: readonly string[];
	readonly forbiddenPaths: readonly string[];
}
export type McpWriterPath = string;
