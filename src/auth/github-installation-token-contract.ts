/**
 * GitHub App installation token exchange boundary.
 *
 * This module intentionally contains only the production-facing contract for a
 * future adapter. Test-local specification oracles may import these types, but
 * the exchange implementation itself must live in a production module before it
 * can be used at runtime.
 */

export interface GitHubInstallationTokenResponse {
	token: string;
	expiresAt: string;
	permissions: Record<string, string>;
	repositorySelection: string;
}

export interface GitHubInstallationTokenExchangeOptions {
	jwt: string;
	installationId: number;
	nowMs: number;
	githubApiBaseUrl?: string;
}

export interface GitHubInstallationTokenFetchResponse {
	ok: boolean;
	status: number;
	statusText: string;
	json: () => Promise<unknown>;
}

export type GitHubInstallationTokenFetch = (
	url: string,
	init: RequestInit,
) => Promise<GitHubInstallationTokenFetchResponse>;
