export type JsonObject = Record<string, unknown>;

export type CloudflareEnvironment = "production" | "preview";
export type CloudflareDeploymentStatus =
	| "success"
	| "failure"
	| "pending"
	| "skipped"
	| "canceled";

export type ProbeResult = { ok: boolean; status: number };
export type UrlProbe = (url: string) => Promise<ProbeResult>;
export type DiscordSendResult = "sent" | "escalate_issue";

export interface CloudflareDeploymentEvent {
	id: string;
	project_name: string;
	deployment: CloudflareDeployment;
}

export interface CloudflareDeployment {
	id: string;
	url: string;
	environment: CloudflareEnvironment;
	status: CloudflareDeploymentStatus;
	created_on: string;
	modified_on: string;
	meta: {
		branch: string;
		commit_hash: string;
		commit_message: string;
	};
}

export interface NotificationState {
	notifiedDeploymentIds: string[];
	notifiedCommitHashes: string[];
	lastNotificationAt?: string;
}

export interface NotificationStateSnapshot {
	state: NotificationState;
	generation: number | string | null;
}

export interface NotificationStateBackend {
	load(): Promise<NotificationStateSnapshot>;
	save(
		state: NotificationState,
		options: { ifGenerationMatch: number },
	): Promise<void>;
}

export interface NotificationConfig {
	publicBaseUrl: string;
	latestReportUrl: string;
	requiredBranch?: string;
}

export type NotificationDecisionKind =
	| "send_discord"
	| "ignore_duplicate"
	| "ignore_non_production"
	| "ignore_wrong_branch"
	| "wait_for_success"
	| "escalate_issue";

export interface NotificationDecision {
	kind?: NotificationDecisionKind;
	deploymentId?: string;
	reasons?: string[];
	payload?: JsonObject;
	shouldNotify?: boolean;
	reason?: string;
	reportUrlChecked?: boolean;
	stateSaved?: boolean;
}

export interface PersistedNotificationDecision extends NotificationDecision {
	state?: NotificationState;
	generation?: number | string | null;
}

export interface DiscordPayloadInput {
	event?: CloudflareDeploymentEvent;
	deployment?: CloudflareDeployment;
	publicBaseUrl: string;
	latestReportUrl: string;
	relatedTopics?: Array<{ title: string; url: string }>;
}

export interface DiscordWebhookPayload {
	username: "Aegis-Intelligence";
	avatar_url: string;
	embeds: [DiscordEmbed];
}

export interface DiscordEmbed {
	title: string;
	description: string;
	url: string;
	color: number;
	fields: DiscordEmbedField[];
	footer: {
		text: string;
		icon_url: string;
	};
	timestamp: string;
}

export interface DiscordEmbedField {
	name: string;
	value: string;
	inline: boolean;
}

export interface RetryPolicy {
	maxAttempts: number;
	baseDelayMs?: number;
	backoffMs?: number[];
}

export declare class GenerationMismatchError extends Error {
	constructor(message?: string);
}

export type NotificationPersistenceResult =
	| { ok: true; snapshot: NotificationStateSnapshot }
	| { ok: false; error: GenerationMismatchError };

export declare function evaluateDiscordNotification(
	event: CloudflareDeploymentEvent,
	state: NotificationState,
	config: NotificationConfig,
	probe: UrlProbe,
): Promise<NotificationDecision>;
export declare function recordNotificationState(
	state: NotificationState,
	event: CloudflareDeploymentEvent,
): NotificationState;
export declare function evaluateAndPersistNotification(
	event: CloudflareDeploymentEvent,
	backend: NotificationStateBackend,
	config: NotificationConfig,
	probe: UrlProbe,
): Promise<PersistedNotificationDecision>;
export declare function buildDiscordPayload(
	input: DiscordPayloadInput,
): JsonObject;
export declare function sendDiscordWithBoundedRetry(
	send: () => Promise<ProbeResult>,
	sleep: (ms: number) => Promise<void>,
	policy: RetryPolicy,
): Promise<DiscordSendResult>;
