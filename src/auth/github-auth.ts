export interface GitHubAppJwtInput {
	readonly appId: string;
	readonly privateKeyPem: string;
	readonly now?: Date;
}

export interface GitHubInstallationTokenExchangeOptions {
	readonly installationId: number;
	readonly jwt: string;
	readonly repositories?: readonly string[];
	readonly nowMs?: number;
}

export type GitHubInstallationTokenRequest =
	GitHubInstallationTokenExchangeOptions;

export interface GitHubInstallationTokenResponse {
	readonly token: string;
	readonly expires_at: string;
	readonly permissions?: Readonly<Record<string, string>>;
	readonly repository_selection?: string;
}

export type GitHubInstallationTokenFetchResponse = {
	readonly ok: boolean;
	readonly status: number;
	readonly statusText?: string;
	readonly json: () => Promise<unknown>;
};

export type GitHubInstallationTokenFetch = (
	url: string,
	init: RequestInit,
) => Promise<GitHubInstallationTokenFetchResponse>;
