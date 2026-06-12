export interface GitHubAppJwtHeader {
	alg: "RS256";
	typ: "JWT";
}

export interface GitHubAppJwtPayload {
	iss: string;
	iat: number;
	exp: number;
}

export interface GitHubAppJwtRequest {
	appId: string;
	privateKeyPem: string;
	nowSeconds?: number;
}

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

export type GitHubInstallationTokenExchangeResult =
	| { ok: true; token: GitHubInstallationTokenResponse }
	| {
			ok: false;
			reason:
				| "http_error"
				| "missing_token"
				| "missing_expiry"
				| "expired"
				| "expiry_too_long";
			status?: number;
			statusText?: string;
	  };
