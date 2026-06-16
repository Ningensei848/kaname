# Feature 004: Cloudflare deployment gated Discord notification

## Goal

Discord 通知を main merge ではなく、Cloudflare Pages の production deployment success に厳格にバインドする。

## Requirements

### F004-R1: Notification gate

Discord notification MUST be sent only when all are true:

- `deployment.status === "success"`
- `deployment.environment === "production"`
- `deployment.meta.branch === "main"`
- deployment URL matches configured public base URL
- latest report URL is live
- commit hash has not already been notified

### F004-R2: Idempotency

Notification state SHOULD be stored outside Git, using the same Cloud Storage backend family as crawler state unless a separate ADR says otherwise. Notification idempotency MUST be persisted in a dedicated `notification-state.json` object, separate from `crawler-state.json` and vault metadata state, so deployment notification history cannot conflict with crawler source hashes or taxonomy metadata writes.


Recommended object layout:

```text
gs://<KANAME_STATE_BUCKET>/<environment>/notification-state.json
```

The executable schema is `.spec/schemas/notification-state.schema.json`; it records `notified_deployment_ids`, `notified_commit_hashes`, `last_successful_notification_at`, and `last_failed_notification_at`.

### F004-R3: Failure handling

Discord webhook failures SHOULD retry with bounded backoff. Repeated failures create a GitHub Issue; they must not re-run content generation.

## Acceptance scenarios

- Preview deployments do not notify.
- Failed or pending deployments do not notify.
- Duplicate commit hash does not notify twice.
- Production success with live report URL produces a valid Discord embed.
