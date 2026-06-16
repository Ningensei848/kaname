export type JsonObject = Record<string, unknown>;
export type ProbeResult = { ok: boolean; status: number };
export type UrlProbe = (url: string) => Promise<ProbeResult>;
export type DiscordSendResult = "sent" | "escalate_issue";
export interface NotificationStateSaveResult {
	saved: boolean;
	generation: number;
}
export interface NotificationGenerationConflict {
	kind: "generation_conflict";
	expectedGeneration: number;
	actualGeneration?: number;
}
export interface DiscordDeliveryDecision {
	action: "send" | "skip" | "escalate";
	reason: string;
}
export interface DiscordWebhookSendResult {
	status: "sent" | "failed" | "escalate_issue";
	statusCode?: number;
	attempts: number;
}
export interface CloudflareDeploymentEvent {
	id: string;
	project_name: string;
	deployment: {
		id: string;
		url: string;
		environment: "production" | "preview";
		status: "success" | "failure" | "pending" | "skipped" | "canceled";
		created_on: string;
		modified_on: string;
		meta: { branch: string; commit_hash: string; commit_message: string };
	};
}
export interface NotificationState {
	notifiedDeploymentIds: string[];
	notifiedCommitHashes: string[];
}
export interface NotificationStateSnapshot {
	state: NotificationState;
	generation: number;
}
export interface NotificationStateBackend {
	load(): Promise<NotificationStateSnapshot>;
	save(
		nextState: NotificationState,
		options: { ifGenerationMatch: number },
	): Promise<
		undefined | NotificationStateSaveResult | NotificationGenerationConflict
	>;
}
export interface NotificationConfig {
	publicBaseUrl: string;
	latestReportUrl: string;
}
export interface NotificationDecision {
	shouldNotify: boolean;
	reason: string;
	reportUrlChecked: boolean;
}
export interface PersistedNotificationDecision extends NotificationDecision {
	stateSaved: boolean;
}
export interface DiscordPayloadInput {
	deployment: CloudflareDeploymentEvent["deployment"];
	publicBaseUrl: string;
	latestReportUrl: string;
	relatedTopics: Array<{ title: string; url: string }>;
}
export interface RetryPolicy {
	maxAttempts: number;
	backoffMs: number[];
}
export interface GenerationMismatchError extends Error {
	readonly name: "GenerationMismatchError";
}
