# Telegram alerts

Run commands from the repository root using `go-task`; see the
[task guide](../README.md#runbook-tasks) for prerequisites, previews and context selection.

Flux forwards informational events and errors from GitRepository, Kustomization, HelmRepository,
HelmChart and HelmRelease objects in `flux-system` to Telegram. These cover
GitOps reconciliation, not PostgreSQL backup execution, stale backups, WAL
archiving or a complete cluster/network outage.

## Set up

1. Open [@BotFather](https://t.me/BotFather), send `/newbot` and follow the
   prompts. Save the token privately.
2. From the repository root, run:

   ```sh
   go-task telegram:setup
   ```

   Enter the token at the hidden prompt. The helper asks you to open your bot
   in Telegram and press **Start**, then automatically discovers the chat ID.
   Confirm the displayed chat, or choose a destination if multiple chats appear.
   For a group destination, add the bot and send a command addressed to it.
   If no chats appear, send a fresh message and press Enter to retry.
3. The helper writes `provider.yaml`, encrypts the token into
   `telegram-token.sops.yaml`, and enables `notifications` in the infrastructure
   Kustomization. Run `go-task telegram:setup -- --replace` to rotate credentials
   or change chats.
   Chat IDs are stored in the Provider as ordinary configuration.

   Use a dedicated bot without an existing webhook or another update consumer.
   For a known destination, `go-task telegram:setup -- --chat-id <ID>` skips discovery; `@channel` is also
   supported for Telegram channels. Personal usernames are not chat IDs.
4. Render the configuration and review the diff before committing/pushing:

   ```sh
   go-task validate
   git status --short
   ```

   Infrastructure uses the existing `flux-system/sops-age` key to decrypt the
   Secret. Until the setup helper runs, notifications are excluded from the
   infrastructure build, so missing credentials cannot block reconciliation.

## Test Telegram delivery

After setup, send one message using the saved Provider and encrypted token:

```sh
go-task telegram:test
```

The task calls the saved test script, decrypts the token in memory, and prints
HTTP status, response headers/body or network error details on failure, with
the token redacted. It exits nonzero on failure and does not retry automatically.
This tests bot credentials and destination permissions independently of Flux.
For a channel destination, make the bot an administrator with Post Messages
permission.

## Verify after deployment

```sh
go-task telegram:status
go-task telegram:logs
```

Check for delivery errors and confirm a real Flux error reaches Telegram.
Provider readiness alone does not prove phone delivery. The `info` severity
includes informational and error events, including successful reconciliations;
repeated identical events are rate limited by Flux. A complete outage needs an
external monitor.

References: [Flux Telegram provider](https://fluxcd.io/flux/components/notification/providers/#telegram),
[Flux Alerts](https://fluxcd.io/flux/components/notification/alerts/),
[Telegram bot setup](https://core.telegram.org/bots/tutorial#obtain-your-bot-token),
[Telegram getUpdates](https://core.telegram.org/bots/api#getupdates).
