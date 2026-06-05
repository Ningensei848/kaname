import * as fs from "node:fs";
import * as YAML from "yaml";
import type { SsotSource } from "../types";

interface ParsedSsotYaml {
	ssot_sources?: unknown;
}

interface SourceCandidate {
	id?: unknown;
	name?: unknown;
	url?: unknown;
	feed_url?: unknown;
	description?: unknown;
	meta_url?: unknown;
	custom_extraction_instruction?: unknown;
}

export function parseSsotYaml(filePath: string): SsotSource[] {
	if (!fs.existsSync(filePath)) {
		throw new Error(`SSoT configuration file not found at: ${filePath}`);
	}

	const fileContent = fs.readFileSync(filePath, "utf8");
	let parsed: ParsedSsotYaml;
	try {
		parsed = YAML.parse(fileContent) as ParsedSsotYaml;
	} catch (error) {
		throw new Error(
			`Failed to parse SSoT YAML file: ${(error as Error).message}`,
		);
	}

	if (
		!parsed ||
		typeof parsed !== "object" ||
		!Array.isArray(parsed.ssot_sources)
	) {
		throw new Error("Invalid SSoT YAML structure: missing ssot_sources list");
	}

	const validatedSources: SsotSource[] = [];

	for (const source of parsed.ssot_sources) {
		try {
			validateSource(source);
			validatedSources.push(source);
		} catch (validationError) {
			const candidate = isRecord(source) ? source : undefined;
			console.warn(
				`Skipping invalid SSoT source (ID: ${String(candidate?.id || "unknown")}): ${(validationError as Error).message}`,
			);
		}
	}

	return validatedSources;
}

function validateSource(source: unknown): asserts source is SsotSource {
	if (!isRecord(source)) {
		throw new Error("Source is not a valid object");
	}

	const candidate = source as SourceCandidate;
	if (typeof candidate.id !== "string") {
		throw new Error("Missing or invalid required parameter: id");
	}
	if (!/^[a-z0-9_]+$/.test(candidate.id)) {
		throw new Error(`ID "${candidate.id}" does not match pattern ^[a-z0-9_]+$`);
	}
	if (typeof candidate.name !== "string" || candidate.name.trim() === "") {
		throw new Error("Missing or invalid required parameter: name");
	}
	if (typeof candidate.url !== "string" || !isValidUri(candidate.url)) {
		throw new Error("Missing or invalid required parameter: url");
	}
	if (
		typeof candidate.description !== "string" ||
		candidate.description.trim() === ""
	) {
		throw new Error("Missing or invalid required parameter: description");
	}

	if (
		candidate.feed_url !== undefined &&
		(typeof candidate.feed_url !== "string" || !isValidUri(candidate.feed_url))
	) {
		throw new Error("Invalid optional parameter: feed_url");
	}
	if (
		candidate.meta_url !== undefined &&
		(typeof candidate.meta_url !== "string" || !isValidUri(candidate.meta_url))
	) {
		throw new Error("Invalid optional parameter: meta_url");
	}
	if (
		candidate.custom_extraction_instruction !== undefined &&
		typeof candidate.custom_extraction_instruction !== "string"
	) {
		throw new Error(
			"Invalid optional parameter: custom_extraction_instruction",
		);
	}
}

function isRecord(value: unknown): value is Record<string, unknown> {
	return value !== null && typeof value === "object";
}

function isValidUri(val: string): boolean {
	try {
		new URL(val);
		return true;
	} catch {
		return false;
	}
}
