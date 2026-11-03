# discord-admin (Hermes skill)

Gives a Hermes agent the ability to change a Discord **server** — create channels,
categories and roles, set permission overwrites, and diagnose why the bot is refusing.

Hermes's built-in Discord integration is a chat channel: messages in, messages out.
It has no structural tools, so an agent asked to "make a channel" will often answer
that it can't. This skill supplies the missing half: a small REST client plus the
error-code playbook.

## Install

    git clone https://github.com/dank0296/discord-admin-skill.git /opt/hermes/discord-admin
    bash /opt/hermes/discord-admin/install-discord-admin.sh

Installs to `/opt/hermes/data/skills/discord-admin` (override with `HERMES_DATA=`).

## Diagnose first

    docker exec hermes python3 /opt/data/skills/discord-admin/scripts/discord_admin.py \
        diag --guild $DISCORD_GUILD_ID

Output on a healthy bot:

    bot: My Bot (123456789)
    guild: My Server (987654321)
    permissions: ADMINISTRATOR

If it prints `MISSING: MANAGE_CHANNELS`, it also prints the exact re-invite URL.

## What the errors mean

| Code | Cause | Fix |
|---|---|---|
| `50013 Missing Permissions` | Bot invited without Manage Channels | Re-invite with `permissions=8` |
| `50001 Missing Access` | Bot role below the target role/channel | Raise the bot role, or admin invite |
| `1010` everywhere | Missing `User-Agent` (Python urllib) or bad token | Send a UA header; check token |
| `401 Unauthorized` | Wrong token / bot removed | Reset token, update `.env` |

## Commands

    discord_admin.py diag --guild ID
    discord_admin.py list-roles --guild ID
    discord_admin.py list-channels --guild ID
    discord_admin.py create-category "📢 INFO" --guild ID
    discord_admin.py create-channel welcome --guild ID --category CAT_ID
    discord_admin.py create-channel vip --guild ID --category CAT_ID --private-role ROLE_ID
    discord_admin.py overwrite CHANNEL_ID --role ROLE_ID --deny VIEW_CHANNEL
    discord_admin.py create-role Customer --guild ID
    discord_admin.py delete-channel CHANNEL_ID

Token is read from `DISCORD_BOT_TOKEN` (env, or `--env-file`, default
`/opt/hermes/data/.env`). It is never passed on the command line.

## Licence

MIT. No credentials, no server IDs, no personal data in this repo.
