import * as fs from 'fs';
import * as YAML from 'yaml';
import { SsotConfig, SsotSource } from '../types';

export function parseSsotYaml(filePath: string): SsotSource[] {
  if (!fs.existsSync(filePath)) {
    throw new Error(`SSoT configuration file not found at: ${filePath}`);
  }

  const fileContent = fs.readFileSync(filePath, 'utf8');
  let parsed: any;
  try {
    parsed = YAML.parse(fileContent);
  } catch (error) {
    throw new Error(`Failed to parse SSoT YAML file: ${(error as Error).message}`);
  }

  if (!parsed || typeof parsed !== 'object' || !Array.isArray(parsed.ssot_sources)) {
    throw new Error('Invalid SSoT YAML structure: missing ssot_sources list');
  }

  const validatedSources: SsotSource[] = [];

  for (const source of parsed.ssot_sources) {
    try {
      validateSource(source);
      validatedSources.push(source as SsotSource);
    } catch (validationError) {
      // Degraded operation: log warning and skip the malformed source
      console.warn(
        `Skipping invalid SSoT source (ID: ${source?.id || 'unknown'}): ${(validationError as Error).message}`
      );
    }
  }

  return validatedSources;
}

function validateSource(source: any): void {
  if (!source || typeof source !== 'object') {
    throw new Error('Source is not a valid object');
  }

  // Check required parameters
  if (typeof source.id !== 'string') {
    throw new Error('Missing or invalid required parameter: id');
  }
  if (!/^[a-z0-9_]+$/.test(source.id)) {
    throw new Error(`ID "${source.id}" does not match pattern ^[a-z0-9_]+$`);
  }
  if (typeof source.name !== 'string' || source.name.trim() === '') {
    throw new Error('Missing or invalid required parameter: name');
  }
  if (typeof source.url !== 'string' || !isValidUri(source.url)) {
    throw new Error('Missing or invalid required parameter: url');
  }
  if (typeof source.description !== 'string' || source.description.trim() === '') {
    throw new Error('Missing or invalid required parameter: description');
  }

  // Check optional parameters if they exist
  if (source.feed_url !== undefined && (typeof source.feed_url !== 'string' || !isValidUri(source.feed_url))) {
    throw new Error('Invalid optional parameter: feed_url');
  }
  if (source.meta_url !== undefined && (typeof source.meta_url !== 'string' || !isValidUri(source.meta_url))) {
    throw new Error('Invalid optional parameter: meta_url');
  }
  if (source.custom_extraction_instruction !== undefined && typeof source.custom_extraction_instruction !== 'string') {
    throw new Error('Invalid optional parameter: custom_extraction_instruction');
  }
}

function isValidUri(val: string): boolean {
  try {
    new URL(val);
    return true;
  } catch {
    return false;
  }
}
