---
name: discord-admin
description: "Use when a Discord bot must change the server itself — create or delete channels, categories and roles, fix permission overwrites, or diagnose 403/50013/50001/1010."
version: 1.0.0
author: Partner Kit
license: MIT
metadata:
  hermes:
    tags: [discord, admin, channels, roles, permissions, rest-api]
    related_skills: [discord-server, telegram-interaction]
---

# Discord server administration

Hermes's Discord integration is a **chat channel** — it receives messages and posts
replies. It has no tool for creating channels, roles or permission overwrites, and the
model will correctly say it "can't" if you only look at the tool list.

You can. The bot token has whatever permissions the bot was invited with, and the REST
API is reachable from the terminal. That is the whole trick.

## First, diagnose — never guess

```bash
python3 scripts/discord_admin.py diag --guild $DISCORD_GUILD_ID
```

It prints the bot identity, the guild, and the permissions the bot actually holds,
plus the re-invite URL when `MANAGE_CHANNELS` or `MANAGE_ROLES` is missing.

## Error codes: what they actually mean

| Symptom | Cause | Fix |
|---|---|---|
| `50013 Missing Permissions` | Bot was invited without **Manage Channels** (or Manage Roles) | Re-invite with `permissions=8`, or a bitset including 16 + 268435456 |
| `50001 Missing Access` | Bot's role sits **below** the role/channel it is editing | Drag the bot role above the target in Server Settings → Roles, or use the admin invite |
| `1010` on every endpoint | Missing `User-Agent` header (Python `urllib`) — or invalid token | Always send a UA: `DiscordBot (name, 1.0)`; `curl` masks the bug by sending its own |
| `401 Unauthorized` | Wrong token, or bot kicked from the server | Reset token in Developer Portal, update `.env`, restart |
| Works with `curl`, fails in code | The UA case above, or the token is read from the wrong line of `.env` | Use the script — it reads `DISCORD_BOT_TOKEN=` properly |

Re-invite with Administrator (simplest, and what small private servers should use):

```
https://discord.com/api/oauth2/authorize?client_id=<BOT_CLIENT_ID>&permissions=8&scope=bot
```

A bot cannot grant a permission it does not hold, and cannot act on a role at or above
its own position. Both errors look identical from the agent's side — the code tells them apart.

## Common operations

```bash
# categories and channels
python3 scripts/discord_admin.py create-category "📢 INFO"
python3 scripts/discord_admin.py create-channel welcome --category <CATEGORY_ID>
python3 scripts/discord_admin.py create-channel vip-lounge --category <CAT_ID> --private-role <ROLE_ID>
python3 scripts/discord_admin.py list-channels
python3 scripts/discord_admin.py delete-channel <CHANNEL_ID>

# roles and overwrites
python3 scripts/discord_admin.py create-role "Customer"
python3 scripts/discord_admin.py overwrite <CHANNEL_ID> --role <ROLE_ID> --allow "VIEW_CHANNEL,SEND_MESSAGES"
python3 scripts/discord_admin.py overwrite <CHANNEL_ID> --role <GUILD_ID> --deny "VIEW_CHANNEL"
```

`--role <GUILD_ID>` targets `@everyone` (the guild id doubles as the everyone role id).

## House rules

1. **Diagnose before acting.** `diag` costs one request and prevents a dozen wrong guesses.
2. **Never paste a token into chat, a log, or a skill.** It lives in `.env` only.
3. **One bot, one running gateway.** Two processes on the same token fight over the socket.
4. **Administrator for private servers, narrow bitsets for public ones.** A bot in a
   public server with `permissions=8` is a liability.
5. **Verify after writing.** Re-run `list-channels` / `list-roles` and read the result
   back — a 200 is not proof the structure is what you intended.

## Setup checklist (new bot)

1. discord.com/developers → New Application → Bot → Reset Token
2. Privileged Gateway Intents: **Message Content** + **Server Members**
3. OAuth2 URL Generator: scope `bot`; permissions per the table above
4. Invite to the server; in `.env`: `DISCORD_BOT_TOKEN=...` and `DISCORD_GUILD_ID=...`
5. `python3 scripts/discord_admin.py diag --guild $DISCORD_GUILD_ID` → expect ADMINISTRATOR
   or a permissions list containing MANAGE_CHANNELS
