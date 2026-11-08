# Telegram alerts

Flux sends informational and error events to Telegram, including successful
reconciliations. PostgreSQL alerts use [Alertmanager](backup-alerts.md) separately.

## Setup or rotate

Create a bot through [@BotFather](https://t.me/BotFather), then run:

```sh
go-task telegram:setup
```

Enter the token at the hidden prompt. Open the bot, press **Start** and send a
fresh message for chat discovery. For groups, add the bot and send a command
addressed to it. Use a bot without another update consumer or webhook.

For a known destination:

```sh
go-task telegram:setup -- --chat-id <ID>
```

Channels accept `@channel`; personal usernames are not chat IDs. A channel bot
must be an administrator with **Post Messages** permission.

To replace credentials or change destinations:

```sh
go-task telegram:setup -- --replace
go-task monitoring:credentials
```

The second command refreshes Alertmanager's separate encrypted configuration.
Flux's Provider stores the destination as ordinary configuration; the bot token
is SOPS-encrypted. Alertmanager requires a numeric destination ID.

## Verify

```sh
go-task validate
go-task telegram:test       # sends one real message
go-task telegram:status
go-task telegram:logs
```

Deploy through Git/Flux before checking controller delivery. The direct test
prints redacted request errors and exits nonzero on failure. Verify an actual
Flux notification on the phone; Provider readiness alone is insufficient.

[Flux provider reference](https://fluxcd.io/flux/components/notification/providers/#telegram).
