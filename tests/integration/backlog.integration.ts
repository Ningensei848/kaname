import * as assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { once } from "node:events";
import { test } from "node:test";

function missingEnv(names: string[]): string[] {
	return names.filter((name) => !process.env[name]);
}

test("F003 integration backlog: real dummy child process handles SIGTERM cleanup", async (t) => {
	const missing = missingEnv(["KANAME_RUN_PROCESS_SIGNAL_INTEGRATION"]);
	if (missing.length > 0) {
		t.skip(`missing env: ${missing.join(", ")}`);
		return;
	}

	const child = spawn(
		process.execPath,
		[
			"-e",
			"process.stdin.resume(); process.on('SIGTERM', () => process.exit(0));",
		],
		{ stdio: ["pipe", "ignore", "ignore"] },
	);

	assert.ok(child.pid, "dummy child process must start");
	child.kill("SIGTERM");
	const [code, signal] = (await once(child, "exit")) as [
		number | null,
		NodeJS.Signals | null,
	];
	assert.strictEqual(code, 0);
	assert.strictEqual(signal, null);
	assert.strictEqual(child.killed, true);
});

test("F004 integration backlog: real Cloudflare deployment polling and Discord webhook require explicit credentials", async (t) => {
	const missing = missingEnv([
		"KANAME_RUN_CLOUDFLARE_DISCORD_INTEGRATION",
		"CLOUDFLARE_API_TOKEN",
		"CLOUDFLARE_ACCOUNT_ID",
		"CLOUDFLARE_PAGES_PROJECT",
		"DISCORD_WEBHOOK_URL",
	]);
	if (missing.length > 0) {
		t.skip(`missing env: ${missing.join(", ")}`);
		return;
	}

	const webhookUrl = process.env.DISCORD_WEBHOOK_URL as string;
	assert.match(webhookUrl, /^https:\/\/discord(?:app)?\.com\/api\/webhooks\//);

	const cloudflareUrl = new URL(
		`https://api.cloudflare.com/client/v4/accounts/${encodeURIComponent(
			process.env.CLOUDFLARE_ACCOUNT_ID as string,
		)}/pages/projects/${encodeURIComponent(
			process.env.CLOUDFLARE_PAGES_PROJECT as string,
		)}/deployments`,
	);
	cloudflareUrl.searchParams.set("per_page", "1");

	const deploymentResponse = await fetch(cloudflareUrl, {
		headers: {
			Authorization: `Bearer ${process.env.CLOUDFLARE_API_TOKEN}`,
		},
	});
	assert.ok(
		deploymentResponse.status >= 200 && deploymentResponse.status < 300,
		`Cloudflare deployment polling returned ${deploymentResponse.status}`,
	);

	const deploymentBody = (await deploymentResponse.json()) as {
		success?: boolean;
		result?: unknown[];
	};
	assert.strictEqual(deploymentBody.success, true);
	assert.ok(
		Array.isArray(deploymentBody.result),
		"Cloudflare deployment polling must return a result array",
	);

	const discordResponse = await fetch(webhookUrl, {
		method: "POST",
		headers: { "content-type": "application/json" },
		body: JSON.stringify({
			username: "kaname-integration-check",
			content:
				"kaname Cloudflare/Discord integration credential check completed.",
		}),
	});
	assert.ok(
		discordResponse.status === 204 ||
			(discordResponse.status >= 200 && discordResponse.status < 300),
		`Discord webhook returned ${discordResponse.status}`,
	);
});
