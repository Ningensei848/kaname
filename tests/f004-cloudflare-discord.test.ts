import assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { test } from "node:test";
import type {
	CloudflareDeploymentEvent,
	DiscordDeliveryDecision,
	DiscordWebhookSendResult,
	NotificationGenerationConflict,
	NotificationState,
	NotificationStateBackend,
	NotificationStateSaveResult,
	NotificationStateSnapshot,
	RetryPolicy,
	UrlProbe,
} from "../src/notifications/cloudflare-discord";
import { assertQuartzGraphDisabledArtifact } from "./helpers/quartz-artifact-contract";
import {
	validateJsonSchema,
	type JsonObject,
	type JsonSchema,
} from "./helpers/schema-validator";

type NotificationConfig = { publicBaseUrl: string; latestReportUrl: string };
type NotificationDecision = {
	shouldNotify: boolean;
	reason: string;
	reportUrlChecked: boolean;
};
type PersistedNotificationDecision = NotificationDecision & {
	stateSaved: boolean;
};
type DiscordSendResult = "sent" | "escalate_issue";

class GenerationMismatchError extends Error {
	constructor() {
		super("notification state generation mismatch");
	}
}

async function evaluateDiscordNotification(
	event: CloudflareDeploymentEvent,
	state: NotificationState,
	config: NotificationConfig,
	probeReportUrl: UrlProbe,
): Promise<NotificationDecision> {
	const deployment = event.deployment;
	if (deployment.status !== "success") {
		return {
			shouldNotify: false,
			reason: "deployment status is not success",
			reportUrlChecked: false,
		};
	}
	if (deployment.environment !== "production") {
		return {
			shouldNotify: false,
			reason: "deployment is not production",
			reportUrlChecked: false,
		};
	}
	if (deployment.meta.branch !== "main") {
		return {
			shouldNotify: false,
			reason: "deployment branch is not main",
			reportUrlChecked: false,
		};
	}
	if (!isHttpsUrl(deployment.url) || !isHttpsUrl(config.publicBaseUrl)) {
		return {
			shouldNotify: false,
			reason: "deployment and public base URLs must be HTTPS",
			reportUrlChecked: false,
		};
	}
	if (!isHttpsUrl(config.latestReportUrl)) {
		return {
			shouldNotify: false,
			reason: "latest report URL must be HTTPS",
			reportUrlChecked: false,
		};
	}
	if (normalizeUrl(deployment.url) !== normalizeUrl(config.publicBaseUrl)) {
		return {
			shouldNotify: false,
			reason: "deployment URL does not match public base URL",
			reportUrlChecked: false,
		};
	}
	if (state.notifiedDeploymentIds.includes(deployment.id)) {
		return {
			shouldNotify: false,
			reason: "deployment id was already notified",
			reportUrlChecked: false,
		};
	}
	if (state.notifiedCommitHashes.includes(deployment.meta.commit_hash)) {
		return {
			shouldNotify: false,
			reason: "commit hash was already notified",
			reportUrlChecked: false,
		};
	}

	const reportProbe = await probeReportUrl(config.latestReportUrl);
	if (
		!reportProbe.ok ||
		reportProbe.status < 200 ||
		reportProbe.status >= 300
	) {
		return {
			shouldNotify: false,
			reason: "latest report URL is not live",
			reportUrlChecked: true,
		};
	}

	return {
		shouldNotify: true,
		reason: "production deployment and report are live",
		reportUrlChecked: true,
	};
}

function recordNotificationState(
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

async function evaluateAndPersistNotification(
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
		await backend.save(recordNotificationState(snapshot.state, event), {
			ifGenerationMatch: snapshot.generation,
		});
		return { ...decision, stateSaved: true };
	} catch (error) {
		if (error instanceof GenerationMismatchError) {
			return {
				shouldNotify: false,
				reason: "notification state generation precondition failed",
				reportUrlChecked: decision.reportUrlChecked,
				stateSaved: false,
			};
		}
		throw error;
	}
}

function buildDiscordPayload(input: {
	deployment: CloudflareDeploymentEvent["deployment"];
	publicBaseUrl: string;
	latestReportUrl: string;
	relatedTopics: Array<{ title: string; url: string }>;
}): JsonObject {
	const avatarUrl =
		"https://raw.githubusercontent.com/github/spec-kit/main/media/logo_small.webp";
	const reportTitle = path.basename(input.latestReportUrl);
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

async function sendDiscordWithBoundedRetry(
	sendWebhook: () => Promise<{ ok: boolean; status: number }>,
	sleep: (ms: number) => Promise<void>,
	policy: RetryPolicy,
): Promise<DiscordSendResult> {
	for (let attempt = 0; attempt < policy.maxAttempts; attempt += 1) {
		const result = await sendWebhook();
		if (result.ok && result.status >= 200 && result.status < 300) {
			return "sent";
		}
		if (attempt < policy.maxAttempts - 1) {
			await sleep(policy.backoffMs[attempt] ?? policy.backoffMs.at(-1) ?? 0);
		}
	}
	return "escalate_issue";
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

const repoRoot = process.cwd();
const publicBaseUrl = "https://osint-kaname.pages.dev";
const latestReportUrl = `${publicBaseUrl}/reports/2026-05-27_Report`;

function readJson(relativePath: string): unknown {
	return JSON.parse(fs.readFileSync(path.join(repoRoot, relativePath), "utf8"));
}

function readFixture<T>(...segments: string[]): T {
	return readJson(path.join("tests", "fixtures", "f004", ...segments)) as T;
}

function validateWithSchema(schemaPath: string, value: unknown): string[] {
	const schema = readJson(schemaPath) as JsonSchema;
	return validateJsonSchema(schema, value).map(
		(error) => `${error.path}: ${error.message}`,
	);
}

function assertDiscordPayloadPolicy(payload: JsonObject): string[] {
	const errors = validateWithSchema(
		".spec/schemas/discord-webhook-payload.schema.json",
		payload,
	);
	const embed = Array.isArray(payload.embeds)
		? (payload.embeds[0] as JsonObject)
		: undefined;
	if (!embed) return [...errors, "embed is required"];
	const fields = Array.isArray(embed.fields)
		? (embed.fields as JsonObject[])
		: [];
	const reportField = fields.find((field) =>
		String(field.name).includes("更新要約レポート"),
	);
	if (!reportField || !String(reportField.value).includes("/reports/")) {
		errors.push("latest report field must link to the published report URL");
	}
	if (String(embed.url) !== publicBaseUrl) {
		errors.push("embed URL must be the public production base URL");
	}
	if (!fields.some((field) => String(field.name).includes("実行履歴"))) {
		errors.push("execution history field is required");
	}
	return errors;
}

class FakeExternalNotificationStateBackend implements NotificationStateBackend {
	loadCalls = 0;
	saveCalls = 0;
	saveGenerations: number[] = [];
	onBeforeSave?: () => void;

	constructor(
		private state: NotificationState,
		private generation: number,
	) {}

	async load(): Promise<NotificationStateSnapshot> {
		this.loadCalls += 1;
		return { state: cloneState(this.state), generation: this.generation };
	}

	async save(
		nextState: NotificationState,
		options: { ifGenerationMatch: number },
	): Promise<undefined> {
		this.saveCalls += 1;
		this.saveGenerations.push(options.ifGenerationMatch);
		this.onBeforeSave?.();
		if (options.ifGenerationMatch !== this.generation) {
			throw new GenerationMismatchError();
		}
		this.state = cloneState(nextState);
		this.generation += 1;
		return undefined;
	}

	simulateConcurrentWrite(
		mutator: (state: NotificationState) => NotificationState,
	) {
		this.state = cloneState(mutator(this.state));
		this.generation += 1;
	}
}

function cloneState(state: NotificationState): NotificationState {
	return {
		notifiedDeploymentIds: [...state.notifiedDeploymentIds],
		notifiedCommitHashes: [...state.notifiedCommitHashes],
	};
}

// Fixture builder only: this URL probe simulates report reachability for tests.
function buildFixtureLiveReportProbe(
	liveUrls: Set<string>,
	checkedUrls: string[],
): UrlProbe {
	return async (url) => {
		checkedUrls.push(url);
		return liveUrls.has(url)
			? { ok: true, status: 200 }
			: { ok: false, status: 404 };
	};
}

function decideDiscordDeliveryAfterStateSave(
	result:
		| undefined
		| NotificationStateSaveResult
		| NotificationGenerationConflict,
): DiscordDeliveryDecision {
	if (isNotificationGenerationConflict(result)) {
		return {
			action: "skip",
			reason: "notification state generation conflict",
		};
	}
	return { action: "send", reason: "notification state saved" };
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

test("F004 notification type shells model safe delivery boundaries", () => {
	const saveResult: NotificationStateSaveResult = {
		saved: true,
		generation: 42,
	};
	const conflict: NotificationGenerationConflict = {
		kind: "generation_conflict",
		expectedGeneration: 41,
		actualGeneration: 42,
	};
	const sentResult: DiscordWebhookSendResult = {
		status: "sent",
		statusCode: 204,
		attempts: 1,
	};

	assert.deepStrictEqual(decideDiscordDeliveryAfterStateSave(saveResult), {
		action: "send",
		reason: "notification state saved",
	});
	assert.deepStrictEqual(decideDiscordDeliveryAfterStateSave(conflict), {
		action: "skip",
		reason: "notification state generation conflict",
	});
	assert.deepStrictEqual(sentResult, {
		status: "sent",
		statusCode: 204,
		attempts: 1,
	});
});

test("F004 Cloudflare deployment fixtures match the webhook schema", async (t) => {
	for (const fixtureName of [
		"production-success.json",
		"preview-success.json",
		"production-failure.json",
		"production-pending.json",
		"production-wrong-branch.json",
	]) {
		await t.test(
			`${fixtureName} is structurally valid Cloudflare event JSON`,
			() => {
				const event = readFixture<CloudflareDeploymentEvent>(
					"cloudflare",
					fixtureName,
				);
				assert.deepStrictEqual(
					validateWithSchema(
						".spec/schemas/cloudflare-pages-deployment.schema.json",
						event,
					),
					[],
				);
			},
		);
	}
});

test("F004 production notification gate permits generic schema URI while business gate requires HTTPS", async () => {
	const event = readFixture<CloudflareDeploymentEvent>(
		"cloudflare",
		"production-success.json",
	);
	const httpEvent: CloudflareDeploymentEvent = {
		...event,
		deployment: {
			...event.deployment,
			url: "http://osint-kaname.pages.dev",
		},
	};
	assert.deepStrictEqual(
		validateWithSchema(
			".spec/schemas/cloudflare-pages-deployment.schema.json",
			httpEvent,
		),
		[],
	);

	const decision = await evaluateDiscordNotification(
		httpEvent,
		readFixture<NotificationState>("state", "notification-state.empty.json"),
		{
			publicBaseUrl: "http://osint-kaname.pages.dev",
			latestReportUrl:
				"https://osint-kaname.pages.dev/reports/2026-05-27_Report",
		},
		buildFixtureLiveReportProbe(new Set([latestReportUrl]), []),
	);
	assert.deepStrictEqual(decision, {
		shouldNotify: false,
		reason: "deployment and public base URLs must be HTTPS",
		reportUrlChecked: false,
	});
});

test("F004 production notification gate is impossible before production success", async (t) => {
	const emptyState = readFixture<NotificationState>(
		"state",
		"notification-state.empty.json",
	);
	const config = { publicBaseUrl, latestReportUrl };
	const cases: Array<[string, string]> = [
		["preview-success.json", "deployment is not production"],
		["production-failure.json", "deployment status is not success"],
		["production-pending.json", "deployment status is not success"],
		["production-wrong-branch.json", "deployment branch is not main"],
	];

	for (const [fixtureName, reason] of cases) {
		await t.test(
			`${fixtureName} does not notify and does not probe report URL`,
			async () => {
				const checkedUrls: string[] = [];
				const decision = await evaluateDiscordNotification(
					readFixture<CloudflareDeploymentEvent>("cloudflare", fixtureName),
					emptyState,
					config,
					buildFixtureLiveReportProbe(new Set([latestReportUrl]), checkedUrls),
				);

				assert.deepStrictEqual(decision, {
					shouldNotify: false,
					reason,
					reportUrlChecked: false,
				});
				assert.deepStrictEqual(checkedUrls, []);
			},
		);
	}

	await t.test(
		"wrong deployment URL blocks notification before report probing",
		async () => {
			const checkedUrls: string[] = [];
			const event = readFixture<CloudflareDeploymentEvent>(
				"cloudflare",
				"production-success.json",
			);
			const decision = await evaluateDiscordNotification(
				{
					...event,
					deployment: {
						...event.deployment,
						url: "https://evil.example.invalid",
					},
				},
				emptyState,
				config,
				buildFixtureLiveReportProbe(new Set([latestReportUrl]), checkedUrls),
			);

			assert.deepStrictEqual(decision, {
				shouldNotify: false,
				reason: "deployment URL does not match public base URL",
				reportUrlChecked: false,
			});
			assert.deepStrictEqual(checkedUrls, []);
		},
	);
});

test("F004 production notification gate requires mocked live report URL before Discord send", async (t) => {
	const event = readFixture<CloudflareDeploymentEvent>(
		"cloudflare",
		"production-success.json",
	);
	const emptyState = readFixture<NotificationState>(
		"state",
		"notification-state.empty.json",
	);
	const config = { publicBaseUrl, latestReportUrl };

	await t.test(
		"production success is still blocked when the latest report URL is not live",
		async () => {
			const checkedUrls: string[] = [];
			const decision = await evaluateDiscordNotification(
				event,
				emptyState,
				config,
				buildFixtureLiveReportProbe(new Set(), checkedUrls),
			);

			assert.deepStrictEqual(decision, {
				shouldNotify: false,
				reason: "latest report URL is not live",
				reportUrlChecked: true,
			});
			assert.deepStrictEqual(checkedUrls, [latestReportUrl]);
		},
	);

	await t.test(
		"production success with a live latest report URL can notify",
		async () => {
			const checkedUrls: string[] = [];
			const decision = await evaluateDiscordNotification(
				event,
				emptyState,
				config,
				buildFixtureLiveReportProbe(new Set([latestReportUrl]), checkedUrls),
			);

			assert.deepStrictEqual(decision, {
				shouldNotify: true,
				reason: "production deployment and report are live",
				reportUrlChecked: true,
			});
			assert.deepStrictEqual(checkedUrls, [latestReportUrl]);
		},
	);
});

test("F004 production idempotency state blocks repeated events", async (t) => {
	const event = readFixture<CloudflareDeploymentEvent>(
		"cloudflare",
		"production-success.json",
	);
	const config = { publicBaseUrl, latestReportUrl };

	await t.test("recording notification state is append-only and unique", () => {
		const emptyState = readFixture<NotificationState>(
			"state",
			"notification-state.empty.json",
		);
		assert.deepStrictEqual(recordNotificationState(emptyState, event), {
			notifiedDeploymentIds: [event.deployment.id],
			notifiedCommitHashes: [event.deployment.meta.commit_hash],
		});
	});

	await t.test("duplicate deployment id does not notify twice", async () => {
		const duplicateState = readFixture<NotificationState>(
			"state",
			"notification-state.duplicate.json",
		);
		const checkedUrls: string[] = [];
		const decision = await evaluateDiscordNotification(
			event,
			duplicateState,
			config,
			buildFixtureLiveReportProbe(new Set([latestReportUrl]), checkedUrls),
		);

		assert.deepStrictEqual(decision, {
			shouldNotify: false,
			reason: "deployment id was already notified",
			reportUrlChecked: false,
		});
		assert.deepStrictEqual(checkedUrls, []);
	});

	await t.test(
		"duplicate commit hash remains idempotent across deployment ids",
		async () => {
			const state: NotificationState = {
				notifiedDeploymentIds: [],
				notifiedCommitHashes: [event.deployment.meta.commit_hash],
			};
			const checkedUrls: string[] = [];
			const replayWithNewDeploymentId: CloudflareDeploymentEvent = {
				...event,
				deployment: { ...event.deployment, id: "deploy_replayed_different_id" },
			};

			const decision = await evaluateDiscordNotification(
				replayWithNewDeploymentId,
				state,
				config,
				buildFixtureLiveReportProbe(new Set([latestReportUrl]), checkedUrls),
			);

			assert.deepStrictEqual(decision, {
				shouldNotify: false,
				reason: "commit hash was already notified",
				reportUrlChecked: false,
			});
			assert.deepStrictEqual(checkedUrls, []);
		},
	);

	await t.test(
		"external notification state backend is loaded and saved with generation precondition",
		async () => {
			const backend = new FakeExternalNotificationStateBackend(
				readFixture<NotificationState>(
					"state",
					"notification-state.empty.json",
				),
				41,
			);
			const checkedUrls: string[] = [];
			const decision = await evaluateAndPersistNotification(
				event,
				backend,
				config,
				buildFixtureLiveReportProbe(new Set([latestReportUrl]), checkedUrls),
			);

			assert.deepStrictEqual(decision, {
				shouldNotify: true,
				reason: "production deployment and report are live",
				reportUrlChecked: true,
				stateSaved: true,
			});
			assert.strictEqual(backend.loadCalls, 1);
			assert.strictEqual(backend.saveCalls, 1);
			assert.deepStrictEqual(backend.saveGenerations, [41]);
			assert.deepStrictEqual(checkedUrls, [latestReportUrl]);
		},
	);

	await t.test(
		"generation mismatch fails closed before a duplicate Discord send can be committed",
		async () => {
			const backend = new FakeExternalNotificationStateBackend(
				readFixture<NotificationState>(
					"state",
					"notification-state.empty.json",
				),
				7,
			);
			backend.onBeforeSave = () =>
				backend.simulateConcurrentWrite((current) =>
					recordNotificationState(current, event),
				);
			const decision = await evaluateAndPersistNotification(
				event,
				backend,
				config,
				buildFixtureLiveReportProbe(new Set([latestReportUrl]), []),
			);

			assert.deepStrictEqual(decision, {
				shouldNotify: false,
				reason: "notification state generation precondition failed",
				reportUrlChecked: true,
				stateSaved: false,
			});
			assert.strictEqual(backend.loadCalls, 1);
			assert.strictEqual(backend.saveCalls, 1);
			assert.deepStrictEqual(backend.saveGenerations, [7]);
		},
	);
});

test("F004 Discord payload builder satisfies executable schema policy", async (t) => {
	await t.test("canonical fixture satisfies schema and policy checks", () => {
		const payload = readFixture<JsonObject>(
			"discord",
			"valid-deployment-payload.json",
		);
		assert.deepStrictEqual(assertDiscordPayloadPolicy(payload), []);
	});

	await t.test(
		"payload builder emits the same contract shape after the gate is green",
		() => {
			const event = readFixture<CloudflareDeploymentEvent>(
				"cloudflare",
				"production-success.json",
			);
			const payload = buildDiscordPayload({
				deployment: event.deployment,
				publicBaseUrl,
				latestReportUrl,
				relatedTopics: [
					{
						title: "能動的サイバー防御",
						url: `${publicBaseUrl}/topics/gov-agencies/NCO`,
					},
					{
						title: "サイバー演習CYDER",
						url: `${publicBaseUrl}/topics/cyber-exercises/CYDER`,
					},
				],
			});

			assert.deepStrictEqual(assertDiscordPayloadPolicy(payload), []);
		},
	);
});

test("F004 Quartz Graph disabled artifact contract", async (t) => {
	await t.test(
		"graph-disabled fixture contains no graph view UI or scripts",
		() => {
			const fixturePath =
				"tests/fixtures/f004/quartz-artifacts/graph-disabled.html";
			assert.deepStrictEqual(
				assertQuartzGraphDisabledArtifact([
					{
						path: fixturePath,
						html: fs.readFileSync(path.join(repoRoot, fixturePath), "utf8"),
					},
				]),
				[],
			);
		},
	);

	await t.test("graph-enabled fixture is rejected deterministically", () => {
		const fixturePath =
			"tests/fixtures/f004/quartz-artifacts/graph-enabled.html";
		assert.match(
			assertQuartzGraphDisabledArtifact([
				{
					path: fixturePath,
					html: fs.readFileSync(path.join(repoRoot, fixturePath), "utf8"),
				},
			]).join("\n"),
			/Graph View|global-graph|graph\.inline\.js|data-component=\["'\]Graph/,
		);
	});
});

test("F004 production Discord webhook retry is bounded and escalates safely", async (t) => {
	const retryPolicy: RetryPolicy = { maxAttempts: 3, backoffMs: [100, 500] };

	await t.test(
		"transient webhook failure retries without exceeding the bounded policy",
		async () => {
			let attempts = 0;
			const sleeps: number[] = [];
			const result = await sendDiscordWithBoundedRetry(
				async () => {
					attempts += 1;
					return attempts === 2
						? { ok: true, status: 204 }
						: { ok: false, status: 502 };
				},
				async (ms) => {
					sleeps.push(ms);
				},
				retryPolicy,
			);

			assert.strictEqual(result, "sent");
			assert.strictEqual(attempts, 2);
			assert.deepStrictEqual(sleeps, [100]);
		},
	);

	await t.test(
		"repeated webhook failure escalates to GitHub Issue without unbounded retry",
		async () => {
			let attempts = 0;
			const sleeps: number[] = [];
			const result = await sendDiscordWithBoundedRetry(
				async () => {
					attempts += 1;
					return { ok: false, status: 500 };
				},
				async (ms) => {
					sleeps.push(ms);
				},
				retryPolicy,
			);

			assert.strictEqual(result, "escalate_issue");
			assert.strictEqual(attempts, 3);
			assert.deepStrictEqual(sleeps, [100, 500]);
		},
	);
});

test("F004 production notification state persists through injected external backend", async () => {
	const event = readFixture(
		"cloudflare",
		"production-success.json",
	) as CloudflareDeploymentEvent;
	const saved: Array<{ state: NotificationState; ifGenerationMatch: number }> =
		[];
	const backend: NotificationStateBackend = {
		load: async () => ({
			state: { notifiedDeploymentIds: [], notifiedCommitHashes: [] },
			generation: 7,
		}),
		save: async (nextState, options) => {
			saved.push({
				state: nextState,
				ifGenerationMatch: options.ifGenerationMatch,
			});
			return undefined;
		},
	};

	const decision = await evaluateAndPersistNotification(
		event,
		backend,
		{
			publicBaseUrl: "https://osint-kaname.pages.dev",
			latestReportUrl: "https://osint-kaname.pages.dev/reports/latest",
		},
		async () => ({ ok: true, status: 200 }),
	);

	assert.deepStrictEqual(decision, {
		shouldNotify: true,
		reason: "production deployment and report are live",
		reportUrlChecked: true,
		stateSaved: true,
	});
	assert.deepStrictEqual(saved, [
		{
			state: {
				notifiedDeploymentIds: [event.deployment.id],
				notifiedCommitHashes: [event.deployment.meta.commit_hash],
			},
			ifGenerationMatch: 7,
		},
	]);
});

test("F004 production notification state fails closed on backend generation mismatch", async () => {
	const event = readFixture(
		"cloudflare",
		"production-success.json",
	) as CloudflareDeploymentEvent;
	const backend: NotificationStateBackend = {
		load: async () => ({
			state: { notifiedDeploymentIds: [], notifiedCommitHashes: [] },
			generation: 8,
		}),
		save: async () => {
			throw new GenerationMismatchError();
		},
	};

	const decision = await evaluateAndPersistNotification(
		event,
		backend,
		{
			publicBaseUrl: "https://osint-kaname.pages.dev",
			latestReportUrl: "https://osint-kaname.pages.dev/reports/latest",
		},
		async () => ({ ok: true, status: 200 }),
	);

	assert.deepStrictEqual(decision, {
		shouldNotify: false,
		reason: "notification state generation precondition failed",
		reportUrlChecked: true,
		stateSaved: false,
	});
});
