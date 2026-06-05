import * as crypto from "node:crypto";

function base64UrlJson(value: unknown): string {
	return Buffer.from(JSON.stringify(value), "utf8").toString("base64url");
}

export function generateGitHubAppJwt(
	appId: string,
	privateKeyPem: string,
	nowSeconds = Math.floor(Date.now() / 1000),
): string {
	const header = { alg: "RS256", typ: "JWT" };
	const payload = {
		iss: appId,
		iat: nowSeconds,
		exp: nowSeconds + 600,
	};

	const encodedHeader = base64UrlJson(header);
	const encodedPayload = base64UrlJson(payload);
	const tokenData = `${encodedHeader}.${encodedPayload}`;

	try {
		const signer = crypto.createSign("SHA256");
		signer.update(tokenData);
		signer.end();
		const signature = signer.sign(privateKeyPem).toString("base64url");
		return `${tokenData}.${signature}`;
	} catch (error) {
		throw new Error(
			`Invalid GitHub App private key: ${(error as Error).message}`,
		);
	}
}
