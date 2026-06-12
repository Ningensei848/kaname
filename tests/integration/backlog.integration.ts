import * as assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { once } from "node:events";
import { test } from "node:test";

function requiredEnv(names: string[]): string | false {
	const missing = names.filter((name) => !process.env[name]);
	return missing.length > 0 ? `missing env: ${missing.join(", ")}` : false;
}

const signalEnvSkip = requiredEnv(["KANAME_RUN_PROCESS_SIGNAL_INTEGRATION"]);

test("F003 integration backlog: real dummy child process handles SIGTERM cleanup", {
	skip: signalEnvSkip,
}, async () => {
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

const externalCloudflareDiscordSkip = requiredEnv([
	"KANAME_RUN_CLOUDFLARE_DISCORD_INTEGRATION",
	"CLOUDFLARE_API_TOKEN",
	"CLOUDFLARE_ACCOUNT_ID",
	"CLOUDFLARE_PAGES_PROJECT",
	"DISCORD_WEBHOOK_URL",
]);

test("F004 integration backlog: real Cloudflare and Discord checks require explicit credentials", {
	skip: externalCloudflareDiscordSkip,
}, () => {
	assert.match(
		process.env.DISCORD_WEBHOOK_URL ?? "",
		/^https:\/\/discord(?:app)?\.com\/api\/webhooks\//,
	);
	assert.ok(
		process.env.CLOUDFLARE_API_TOKEN,
		"Cloudflare API token is required before enabling this external integration scenario",
	);
	assert.fail(
		"Backlog scenario is intentionally red when credentials are explicitly enabled: implement real Cloudflare deployment polling and Discord webhook round trip before removing this failure.",
	);
});
