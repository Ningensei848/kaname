export type ExternalServiceStatus = "ready" | "pending" | "error";

export interface ExternalServiceDecision {
	status: ExternalServiceStatus;
	stateFrozen: boolean;
	retryAttempted: boolean;
	reason: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
	return typeof value === "object" && value !== null;
}

function hasFiniteStatus(value: unknown): value is { status: number } {
	return (
		isRecord(value) &&
		typeof value.status === "number" &&
		Number.isFinite(value.status)
	);
}

export function readyExternalServiceDecision(
	reason = "external service response is ready",
): ExternalServiceDecision {
	return {
		status: "ready",
		stateFrozen: false,
		retryAttempted: false,
		reason,
	};
}

export function timeoutRejectionToExternalServiceDecision(
	error: unknown,
): ExternalServiceDecision {
	const message = error instanceof Error ? error.message : String(error);
	const timeoutLike =
		/(?:timeout|timed out|abort|deadline|econnreset|etimedout)/i.test(message);

	return {
		status: timeoutLike ? "pending" : "error",
		stateFrozen: true,
		retryAttempted: false,
		reason: timeoutLike
			? `external service pending after timeout-like rejection: ${message}`
			: `external service error: ${message}`,
	};
}

export function malformedResponseToExternalServiceDecision(
	response: unknown,
): ExternalServiceDecision {
	if (!isRecord(response)) {
		return {
			status: "error",
			stateFrozen: true,
			retryAttempted: false,
			reason: "external service returned malformed response: not an object",
		};
	}

	if (typeof response.ok !== "boolean" || !hasFiniteStatus(response)) {
		return {
			status: "error",
			stateFrozen: true,
			retryAttempted: false,
			reason:
				"external service returned malformed response: missing boolean ok or numeric status",
		};
	}

	const probeResponse = response as { ok: boolean; status: number };
	if (
		!probeResponse.ok ||
		probeResponse.status < 200 ||
		probeResponse.status >= 300
	) {
		return {
			status: "pending",
			stateFrozen: true,
			retryAttempted: false,
			reason: `external service pending/error response: status ${probeResponse.status}`,
		};
	}

	return readyExternalServiceDecision("external service response is ready");
}
