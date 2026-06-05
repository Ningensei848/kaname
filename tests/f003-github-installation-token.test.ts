/**
 * F003 GitHub App installation token exchange contract tests.
 *
 * These tests use an injectable fetch boundary and synthetic responses so the
 * flow is fully testable without real GitHub access or PATs.
 */

import * as assert from "node:assert";
import * as crypto from "node:crypto";
import { test } from "node:test";
import { generateGitHubAppJwt } from "../src/auth/github-auth";

interface FakeResponse {
	ok: boolean;
	status: number;
	statusText: string;
	json: () => Promise<unknown>;
}

type FetchLike = (url: string, init: RequestInit) => Promise<FakeResponse>;

interface InstallationTokenResult {
	token: string;
	expiresAt: string;
	permissions: Record<string, string>;
	repositorySelection: string;
}

async function exchangeJwtForInstallationToken(
	fetchFn: FetchLike,
	options: {
		jwt: string;
		installationId: number;
		nowMs: number;
		githubApiBaseUrl?: string;
	},
): Promise<InstallationTokenResult> {
	const apiBaseUrl = options.githubApiBaseUrl ?? "https://api.github.com";
	const response = await fetchFn(
		`${apiBaseUrl}/app/installations/${options.installationId}/access_tokens`,
		{
			method: "POST",
			headers: {
				Accept: "application/vnd.github+json",
				Authorization: `Bearer ${options.jwt}`,
				"X-GitHub-Api-Version": "2022-11-28",
			},
		},
	);

	if (!response.ok) {
		throw new Error(
			`GitHub installation token exchange failed: ${response.status} ${response.statusText}`,
		);
	}

	const body = (await response.json()) as Record<string, unknown>;
	if (typeof body.token !== "string" || body.token.length === 0) {
		throw new Error("GitHub installation token response did not contain token");
	}
	if (typeof body.expires_at !== "string") {
		throw new Error(
			"GitHub installation token response did not contain expires_at",
		);
	}

	const expiresAtMs = Date.parse(body.expires_at);
	if (Number.isNaN(expiresAtMs) || expiresAtMs <= options.nowMs) {
		throw new Error(
			"GitHub installation token expires_at is not in the future",
		);
	}
	if (expiresAtMs - options.nowMs > 60 * 60 * 1000) {
		throw new Error("GitHub installation token expiry exceeds one hour");
	}

	return {
		token: body.token,
		expiresAt: body.expires_at,
		permissions: (body.permissions ?? {}) as Record<string, string>,
		repositorySelection: String(body.repository_selection ?? "unknown"),
	};
}

function decodeJwtPayload(jwt: string): Record<string, unknown> {
	const [, payload] = jwt.split(".");
	return JSON.parse(Buffer.from(payload, "base64url").toString("utf8"));
}

test("F003 GitHub App installation token exchange", async (t) => {
	const { privateKey } = crypto.generateKeyPairSync("rsa", {
		modulusLength: 2048,
		privateKeyEncoding: { type: "pkcs8", format: "pem" },
		publicKeyEncoding: { type: "spki", format: "pem" },
	});
	const nowSeconds = 1_779_849_600;
	const nowMs = nowSeconds * 1000;
	const jwt = generateGitHubAppJwt("123456", privateKey, nowSeconds);

	await t.test("JWT used for exchange has a maximum 10 minute lifetime", () => {
		const payload = decodeJwtPayload(jwt);
		assert.strictEqual(payload.iss, "123456");
		assert.strictEqual((payload.exp as number) - (payload.iat as number), 600);
	});

	await t.test(
		"successful exchange uses POST, bearer JWT, GitHub API version, and returns a sub-hour token",
		async () => {
			const calls: Array<{ url: string; init: RequestInit }> = [];
			const fetchFn: FetchLike = async (url, init) => {
				calls.push({ url, init });
				return {
					ok: true,
					status: 201,
					statusText: "Created",
					json: async () => ({
						token: "ghs_installation_token",
						expires_at: new Date(nowMs + 55 * 60 * 1000).toISOString(),
						permissions: { contents: "write", pull_requests: "write" },
						repository_selection: "selected",
					}),
				};
			};

			const result = await exchangeJwtForInstallationToken(fetchFn, {
				jwt,
				installationId: 98765,
				nowMs,
			});

			assert.strictEqual(result.token, "ghs_installation_token");
			assert.strictEqual(result.permissions.contents, "write");
			assert.strictEqual(calls.length, 1);
			assert.strictEqual(
				calls[0].url,
				"https://api.github.com/app/installations/98765/access_tokens",
			);
			assert.strictEqual(calls[0].init.method, "POST");
			assert.deepStrictEqual(calls[0].init.headers, {
				Accept: "application/vnd.github+json",
				Authorization: `Bearer ${jwt}`,
				"X-GitHub-Api-Version": "2022-11-28",
			});
		},
	);

	await t.test(
		"HTTP failures are converted into safe exchange errors without leaking JWT contents",
		async () => {
			const fetchFn: FetchLike = async () => ({
				ok: false,
				status: 403,
				statusText: "Forbidden",
				json: async () => ({ message: "bad credentials" }),
			});

			await assert.rejects(
				() =>
					exchangeJwtForInstallationToken(fetchFn, {
						jwt,
						installationId: 98765,
						nowMs,
					}),
				(error: Error) => {
					assert.match(error.message, /403 Forbidden/);
					assert.ok(!error.message.includes(jwt));
					return true;
				},
			);
		},
	);

	await t.test(
		"tokens expiring after one hour are rejected fail-closed",
		async () => {
			const fetchFn: FetchLike = async () => ({
				ok: true,
				status: 201,
				statusText: "Created",
				json: async () => ({
					token: "ghs_too_long",
					expires_at: new Date(nowMs + 61 * 60 * 1000).toISOString(),
				}),
			});

			await assert.rejects(
				() =>
					exchangeJwtForInstallationToken(fetchFn, {
						jwt,
						installationId: 98765,
						nowMs,
					}),
				/token expiry exceeds one hour/,
			);
		},
	);
});

test.todo(
	"F003 production GitHub auth module exports installation token exchange with injectable fetch",
);
test.todo(
	"F003 MCP launcher passes installation token as GITHUB_TOKEN_FOR_MCP and never uses PAT",
);
