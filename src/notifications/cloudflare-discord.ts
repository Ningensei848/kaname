import {
	malformedResponseToExternalServiceDecision,
	timeoutRejectionToExternalServiceDecision,
	type ExternalServiceDecision,
} from "../external/fail-closed-adapter";

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
export interface ExternalApiFailureDecision
	extends NotificationDecision,
		ExternalServiceDecision {}
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

export async function evaluateDiscordNotification(
	event: CloudflareDeploymentEvent,
	state: NotificationState,
	config: NotificationConfig,
	probeReportUrl: UrlProbe,
): Promise<NotificationDecision | ExternalApiFailureDecision> {
	const deployment = event.deployment;
	if (deployment.status !== "success") {
		return skip("deployment status is not success", false);
	}
	if (deployment.environment !== "production") {
		return skip("deployment is not production", false);
	}
	if (deployment.meta.branch !== "main") {
		return skip("deployment branch is not main", false);
	}
	if (!isHttpsUrl(deployment.url) || !isHttpsUrl(config.publicBaseUrl)) {
		return skip("deployment and public base URLs must be HTTPS", false);
	}
	if (!isHttpsUrl(config.latestReportUrl)) {
		return skip("latest report URL must be HTTPS", false);
	}
	if (normalizeUrl(deployment.url) !== normalizeUrl(config.publicBaseUrl)) {
		return skip("deployment URL does not match public base URL", false);
	}
	if (state.notifiedDeploymentIds.includes(deployment.id)) {
		return skip("deployment id was already notified", false);
	}
	if (state.notifiedCommitHashes.includes(deployment.meta.commit_hash)) {
		return skip("commit hash was already notified", false);
	}

	try {
		const reportProbeDecision = malformedResponseToExternalServiceDecision(
			await probeReportUrl(config.latestReportUrl),
		);
		if (reportProbeDecision.status !== "ready") {
			return externalProbeDecision(
				"latest report URL is not live",
				reportProbeDecision,
			);
		}
	} catch (error) {
		return externalProbeDecision(
			undefined,
			timeoutRejectionToExternalServiceDecision(error),
		);
	}

	return {
		shouldNotify: true,
		reason: "production deployment and report are live",
		reportUrlChecked: true,
	};
}

export function recordNotificationState(
	state: NotificationState,
	event: CloudflareDeploymentEvent,
): NotificationState {
	return {
		notifiedDeploymentIds: unique([
			...state.notifiedDeploymentIds,
			event.deployment.id,
		]),
		notifiedCommitHashes: unique([
			...state.notifiedCommitHashes,
			event.deployment.meta.commit_hash,
		]),
	};
}

export async function evaluateAndPersistNotification(
	event: CloudflareDeploymentEvent,
	backend: NotificationStateBackend,
	config: NotificationConfig,
	probeReportUrl: UrlProbe,
): Promise<PersistedNotificationDecision> {
	const snapshot = await backend.load();
	const decision = await evaluateDiscordNotification(
		event,
		snapshot.state,
		config,
		probeReportUrl,
	);
	if (!decision.shouldNotify) return { ...decision, stateSaved: false };

	try {
		const saveResult = await backend.save(
			recordNotificationState(snapshot.state, event),
			{
				ifGenerationMatch: snapshot.generation,
			},
		);
		if (isNotificationGenerationConflict(saveResult)) {
			return generationConflictDecision(decision.reportUrlChecked);
		}
		return { ...decision, stateSaved: true };
	} catch (error) {
		if ((error as Error).name === "GenerationMismatchError") {
			return generationConflictDecision(decision.reportUrlChecked);
		}
		throw error;
	}
}

export function buildDiscordPayload(input: DiscordPayloadInput): JsonObject {
	const avatarUrl =
		"https://raw.githubusercontent.com/github/spec-kit/main/media/logo_small.webp";
	const reportTitle =
		input.latestReportUrl.split("/").at(-1) ?? input.latestReportUrl;
	return {
		username: "Aegis-Intelligence",
		avatar_url: avatarUrl,
		embeds: [
			{
				title: "🛡️ インテリジェンス更新 ＆ 本番デプロイ成功報告",
				description:
					"提案・査読エージェントによる検証をすべてパスし、最新のサイバーセキュリティインテリジェンスが本番環境へ安全にホスティングされました。",
				url: input.publicBaseUrl,
				color: 3066993,
				fields: [
					{
						name: "📑 更新要約レポート (最新)",
						value: `[${reportTitle}](${input.latestReportUrl})`,
						inline: true,
					},
					{
						name: "🔗 関連トピック解説",
						value: input.relatedTopics
							.map((topic) => `- [[${topic.title}]](${topic.url})`)
							.join("\n"),
						inline: false,
					},
					{
						name: "⚙️ 実行履歴",
						value: `マージコミット: \`${input.deployment.meta.commit_hash.slice(0, 10)}\` by Aegis-Reviewer`,
						inline: false,
					},
				],
				footer: {
					text: "`kaname` • サーバーレス自律監視システム",
					icon_url: avatarUrl,
				},
				timestamp: new Date(input.deployment.modified_on).toISOString(),
			},
		],
	};
}

export async function sendDiscordWithBoundedRetry(
	sendWebhook: () => Promise<{ ok: boolean; status: number }>,
	sleep: (ms: number) => Promise<void>,
	policy: RetryPolicy,
): Promise<DiscordSendResult> {
	for (let attempt = 0; attempt < policy.maxAttempts; attempt += 1) {
		const result = await sendWebhook();
		if (result.ok && result.status >= 200 && result.status < 300) return "sent";
		if (attempt < policy.maxAttempts - 1)
			await sleep(policy.backoffMs[attempt] ?? policy.backoffMs.at(-1) ?? 0);
	}
	return "escalate_issue";
}

export function decideDiscordDeliveryAfterStateSave(
	result:
		| undefined
		| NotificationStateSaveResult
		| NotificationGenerationConflict,
): DiscordDeliveryDecision {
	if (isNotificationGenerationConflict(result))
		return { action: "skip", reason: "notification state generation conflict" };
	return { action: "send", reason: "notification state saved" };
}

function externalProbeDecision(
	reason: string | undefined,
	externalDecision: ExternalServiceDecision,
): ExternalApiFailureDecision {
	return {
		shouldNotify: false,
		reason: reason ?? externalDecision.reason,
		reportUrlChecked: true,
		status: externalDecision.status,
		stateFrozen: externalDecision.stateFrozen,
		retryAttempted: externalDecision.retryAttempted,
	};
}

function skip(reason: string, reportUrlChecked: boolean): NotificationDecision {
	return { shouldNotify: false, reason, reportUrlChecked };
}

function generationConflictDecision(
	reportUrlChecked: boolean,
): PersistedNotificationDecision {
	return {
		shouldNotify: false,
		reason: "notification state generation precondition failed",
		reportUrlChecked,
		stateSaved: false,
	};
}

function isNotificationGenerationConflict(
	result:
		| undefined
		| NotificationStateSaveResult
		| NotificationGenerationConflict,
): result is NotificationGenerationConflict {
	return (
		typeof result === "object" &&
		result !== null &&
		"kind" in result &&
		result.kind === "generation_conflict"
	);
}

function isHttpsUrl(value: string): boolean {
	try {
		return new URL(value).protocol === "https:";
	} catch {
		return false;
	}
}

function normalizeUrl(value: string): string {
	return value.replace(/\/+$/, "");
}

function unique(values: string[]): string[] {
	return Array.from(new Set(values));
}
