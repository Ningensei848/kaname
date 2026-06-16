export interface GitHubAppJwtInput {
	readonly appId: string;
	readonly privateKeyPem: string;
	readonly now?: Date;
}
export interface GitHubInstallationTokenRequest {
	readonly installationId: number;
	readonly jwt: string;
	readonly repositories?: readonly string[];
}
export interface GitHubInstallationTokenResponse {
	readonly token: string;
	readonly expires_at: string;
}
export type GitHubInstallationTokenFetchResponse = {
	readonly ok: boolean;
	readonly status: number;
	readonly json: () => Promise<unknown>;
};
