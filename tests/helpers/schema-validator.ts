export type JsonObject = Record<string, unknown>;
export type JsonSchema = Record<string, unknown>;

export interface ValidationError {
	path: string;
	message: string;
}

export function validateJsonSchema(
	schema: JsonSchema,
	value: unknown,
	currentPath = "$",
): ValidationError[] {
	const errors: ValidationError[] = [];

	if (schema.type !== undefined && !matchesSchemaType(schema.type, value)) {
		return [
			{
				path: currentPath,
				message: `expected type ${JSON.stringify(schema.type)}`,
			},
		];
	}

	if (schema.const !== undefined && value !== schema.const) {
		errors.push({
			path: currentPath,
			message: `expected const ${schema.const}`,
		});
	}

	if (Array.isArray(schema.enum) && !schema.enum.includes(value)) {
		errors.push({ path: currentPath, message: "expected enum value" });
	}

	if (
		typeof value === "number" &&
		typeof schema.minimum === "number" &&
		value < schema.minimum
	) {
		errors.push({
			path: currentPath,
			message: `expected minimum ${schema.minimum}`,
		});
	}

	if (schema.type === "object" && isRecord(value)) {
		const properties = isRecord(schema.properties) ? schema.properties : {};
		const required = Array.isArray(schema.required) ? schema.required : [];

		for (const requiredKey of required) {
			if (typeof requiredKey === "string" && !(requiredKey in value)) {
				errors.push({
					path: currentPath,
					message: `missing required property ${requiredKey}`,
				});
			}
		}

		if (schema.additionalProperties === false) {
			for (const key of Object.keys(value)) {
				if (!(key in properties)) {
					errors.push({
						path: `${currentPath}.${key}`,
						message: "additional property is not allowed",
					});
				}
			}
		}

		for (const [key, propertySchema] of Object.entries(properties)) {
			if (key in value && isRecord(propertySchema)) {
				errors.push(
					...validateJsonSchema(
						propertySchema,
						value[key],
						`${currentPath}.${key}`,
					),
				);
			}
		}

		if (isRecord(schema.additionalProperties)) {
			for (const [key, childValue] of Object.entries(value)) {
				if (!(key in properties)) {
					errors.push(
						...validateJsonSchema(
							schema.additionalProperties,
							childValue,
							`${currentPath}.${key}`,
						),
					);
				}
			}
		}
	}

	if (schema.type === "array" && Array.isArray(value)) {
		if (typeof schema.minItems === "number" && value.length < schema.minItems) {
			errors.push({
				path: currentPath,
				message: `expected at least ${schema.minItems} items`,
			});
		}
		if (isRecord(schema.items)) {
			value.forEach((item, index) => {
				errors.push(
					...validateJsonSchema(
						schema.items as JsonSchema,
						item,
						`${currentPath}[${index}]`,
					),
				);
			});
		}
	}

	if (typeof value === "string") {
		if (
			typeof schema.minLength === "number" &&
			value.length < schema.minLength
		) {
			errors.push({
				path: currentPath,
				message: `expected minimum length ${schema.minLength}`,
			});
		}
		if (
			typeof schema.pattern === "string" &&
			!new RegExp(schema.pattern).test(value)
		) {
			errors.push({
				path: currentPath,
				message: `expected to match ${schema.pattern}`,
			});
		}
		if (schema.format === "uri" && !isValidUri(value)) {
			errors.push({ path: currentPath, message: "expected URI format" });
		}
		if (schema.format === "date" && !isValidDate(value)) {
			errors.push({ path: currentPath, message: "expected date format" });
		}
		if (schema.format === "date-time" && !isValidDateTime(value)) {
			errors.push({ path: currentPath, message: "expected date-time format" });
		}
	}

	return errors;
}

export function assertValidJsonSchema(
	schema: JsonSchema,
	value: unknown,
	message = "JSON schema validation failed",
): void {
	const errors = validateJsonSchema(schema, value);
	if (errors.length === 0) return;

	const error = new Error(
		`${message}: ${errors
			.map(({ path, message }) => `${path} ${message}`)
			.join("; ")}`,
	) as Error & { validationErrors: ValidationError[] };
	error.validationErrors = errors;
	throw error;
}

function matchesSchemaType(typeRule: unknown, value: unknown): boolean {
	const allowedTypes = Array.isArray(typeRule) ? typeRule : [typeRule];
	return allowedTypes.some((type) => {
		switch (type) {
			case "object":
				return isRecord(value);
			case "array":
				return Array.isArray(value);
			case "string":
				return typeof value === "string";
			case "integer":
				return Number.isInteger(value);
			case "number":
				return typeof value === "number";
			case "boolean":
				return typeof value === "boolean";
			case "null":
				return value === null;
			default:
				return false;
		}
	});
}

function isRecord(value: unknown): value is JsonObject {
	return value !== null && typeof value === "object" && !Array.isArray(value);
}

function isValidUri(value: string): boolean {
	try {
		new URL(value);
		return true;
	} catch {
		return false;
	}
}
function isValidDate(value: string): boolean {
	return (
		/^\d{4}-\d{2}-\d{2}$/.test(value) &&
		!Number.isNaN(Date.parse(`${value}T00:00:00.000Z`))
	);
}
function isValidDateTime(value: string): boolean {
	return !Number.isNaN(Date.parse(value)) && /T/.test(value);
}
