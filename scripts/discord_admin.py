#!/usr/bin/env python3
"""Generic Discord server administration over the REST API.

Bots answer messages; they do not manage servers by themselves. This script is
the missing piece: channels, categories, roles, and permission overwrites.

Token: DISCORD_BOT_TOKEN from the environment, else from --env-file (default
/opt/hermes/data/.env). Never pass the token on the command line.

Commands
  diag                                  who the bot is, what it can do here
  list-roles                            roles with id, position, permissions
  list-channels                         channels with id, type, parent
  create-category NAME
  create-channel NAME [--category ID] [--private-role ROLE_ID] [--type 0|2]
  delete-channel CHANNEL_ID
  create-role NAME
  overwrite CHANNEL_ID --role ROLE_ID [--allow "VIEW_CHANNEL,SEND_MESSAGES"]
                                        [--deny "VIEW_CHANNEL"]

Examples
  python3 discord_admin.py diag --guild 1234567890
  python3 discord_admin.py create-channel welcome --category 111 --private-role 222
  python3 discord_admin.py overwrite 333 --role 222 --deny VIEW_CHANNEL

Exit codes: 0 ok, 2 Discord API error (message printed), 3 config/token error.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

BASE = "https://discord.com/api/v10"
UA = "DiscordBot (hermes-discord-admin, 1.0)"  # REQUIRED: missing UA => phantom 1010

PERMS = {
    "VIEW_CHANNEL": 1 << 10,
    "SEND_MESSAGES": 1 << 11,
    "READ_MESSAGE_HISTORY": 1 << 16,
    "MANAGE_CHANNELS": 1 << 4,
    "MANAGE_ROLES": 1 << 28,
    "MANAGE_MESSAGES": 1 << 13,
    "ATTACH_FILES": 1 << 15,
    "EMBED_LINKS": 1 << 14,
    "ADMINISTRATOR": 1 << 3,
}
ADMIN = PERMS["ADMINISTRATOR"]


def load_token(env_file: str | None) -> str:
    tok = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
    if tok:
        return tok
    path = env_file or "/opt/hermes/data/.env"
    try:
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if line.startswith("DISCORD_BOT_TOKEN=") and "=" in line:
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    print(f"ERROR: no DISCORD_BOT_TOKEN in env or {path}", file=sys.stderr)
    sys.exit(3)


def api(token: str, method: str, path: str, payload: dict | None = None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Authorization", f"Bot {token}")
    req.add_header("User-Agent", UA)
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read().decode()
            return (json.loads(body) if body else None), r.status
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            err = json.loads(body)
        except Exception:
            err = {"message": body}
        code = err.get("code")
        msg = err.get("message", "unknown")
        print(f"ERROR {e.code}: {msg} (code {code})", file=sys.stderr)
        hint = {
            50013: "Missing Permissions — re-invite the bot with Manage Channels (or Administrator), permissions=8.",
            50001: "Missing Access — bot role must sit ABOVE the role/channel it manages.",
            1010: "Missing User-Agent or unknown client — this script sets UA; check token validity.",
            401: "Unauthorized — token wrong or bot removed from the server.",
        }.get(code or e.code)
        if hint:
            print(f"       {hint}", file=sys.stderr)
        sys.exit(2)


def bits(names: str) -> int:
    total = 0
    for n in [x.strip().upper() for x in names.split(",") if x.strip()]:
        if n not in PERMS:
            print(f"ERROR: unknown permission {n}. Known: {', '.join(sorted(PERMS))}", file=sys.stderr)
            sys.exit(3)
        total |= PERMS[n]
    return total


def cmd_diag(token: str, guild: str) -> None:
    me, _ = api(token, "GET", "/users/@me")
    print(f"bot: {me['username']} ({me['id']})")
    g, _ = api(token, "GET", f"/guilds/{guild}")
    print(f"guild: {g['name']} ({g['id']})")
    member, _ = api(token, "GET", f"/guilds/{guild}/members/{me['id']}")
    roles, _ = api(token, "GET", f"/guilds/{guild}/roles")
    by_id = {r["id"]: r for r in roles}
    perms = 0
    for rid in member.get("roles", []):
        perms |= int(by_id.get(rid, {}).get("permissions", 0))
    if int(by_id.get(guild, {}).get("permissions", 0)) & ADMIN or perms & ADMIN:
        print("permissions: ADMINISTRATOR")
        return
    have = [n for n, b in PERMS.items() if perms & b and n != "ADMINISTRATOR"]
    missing = [n for n in ("MANAGE_CHANNELS", "MANAGE_ROLES") if not perms & PERMS[n]]
    print(f"permissions: {', '.join(have) or 'none'}")
    if missing:
        print(f"MISSING: {', '.join(missing)} -> re-invite: "
              f"https://discord.com/api/oauth2/authorize?client_id={me['id']}&permissions=8&scope=bot")


def cmd_list_roles(token: str, guild: str) -> None:
    roles, _ = api(token, "GET", f"/guilds/{guild}/roles")
    for r in sorted(roles, key=lambda x: -x["position"]):
        print(f"{r['position']:>3}  {r['id']}  {r['name']}  perms={r['permissions']}")


def cmd_list_channels(token: str, guild: str) -> None:
    chans, _ = api(token, "GET", f"/guilds/{guild}/channels")
    kinds = {0: "text", 2: "voice", 4: "category", 5: "announcement", 15: "forum"}
    for c in sorted(chans, key=lambda x: (x.get("parent_id") or "", x["position"])):
        print(f"{kinds.get(c['type'], c['type']):<10} {c['id']}  "
              f"parent={c.get('parent_id') or '-':<20} {c['name']}")


def cmd_create_category(token: str, guild: str, args) -> None:
    r, _ = api(token, "POST", f"/guilds/{guild}/channels", {"name": args.name, "type": 4})
    print(f"created category: {r['name']} ({r['id']})")


def cmd_create_channel(token: str, guild: str, args) -> None:
    payload = {"name": args.name, "type": int(args.type)}
    if args.category:
        payload["parent_id"] = args.category
    if args.private_role:
        payload["permission_overwrites"] = [
            {"id": guild, "type": 0, "deny": str(PERMS["VIEW_CHANNEL"]), "allow": "0"},
            {"id": args.private_role, "type": 0, "allow": str(PERMS["VIEW_CHANNEL"]), "deny": "0"},
        ]
    r, _ = api(token, "POST", f"/guilds/{guild}/channels", payload)
    print(f"created channel: {r['name']} ({r['id']}) type={r['type']}")


def cmd_delete_channel(token: str, args) -> None:
    api(token, "DELETE", f"/channels/{args.channel_id}")
    print(f"deleted channel {args.channel_id}")


def cmd_create_role(token: str, guild: str, args) -> None:
    r, _ = api(token, "POST", f"/guilds/{guild}/roles", {"name": args.name})
    print(f"created role: {r['name']} ({r['id']}) position={r['position']}")


def cmd_overwrite(token: str, args) -> None:
    ow = {"id": args.role, "type": 0,
          "allow": str(bits(args.allow) if args.allow else 0),
          "deny": str(bits(args.deny) if args.deny else 0)}
    api(token, "PUT", f"/channels/{args.channel_id}/permissions/{args.role}", ow)
    print(f"overwrite set on {args.channel_id} for role {args.role}")


def main() -> int:
    p = argparse.ArgumentParser(description="Discord server administration via REST.")
    p.add_argument("--env-file", default=None)
    p.add_argument("--guild", default=os.environ.get("DISCORD_GUILD_ID", ""))
    # the same flags, accepted after the subcommand too
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--env-file", default=argparse.SUPPRESS)
    common.add_argument("--guild", default=argparse.SUPPRESS)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("diag", parents=[common])
    sub.add_parser("list-roles", parents=[common])
    sub.add_parser("list-channels", parents=[common])
    c = sub.add_parser("create-category", parents=[common]); c.add_argument("name")
    c = sub.add_parser("create-channel", parents=[common])
    c.add_argument("name"); c.add_argument("--category"); c.add_argument("--private-role")
    c.add_argument("--type", default="0")
    c = sub.add_parser("delete-channel", parents=[common]); c.add_argument("channel_id")
    c = sub.add_parser("create-role", parents=[common]); c.add_argument("name")
    c = sub.add_parser("overwrite", parents=[common])
    c.add_argument("channel_id"); c.add_argument("--role", required=True)
    c.add_argument("--allow", default=""); c.add_argument("--deny", default="")

    args = p.parse_args()
    need_guild = args.cmd in {"diag", "list-roles", "list-channels",
                              "create-category", "create-channel", "create-role"}
    if need_guild and not args.guild:
        print("ERROR: pass --guild or set DISCORD_GUILD_ID", file=sys.stderr)
        return 3

    token = load_token(args.env_file)
    if args.cmd == "diag":
        cmd_diag(token, args.guild)
    elif args.cmd == "list-roles":
        cmd_list_roles(token, args.guild)
    elif args.cmd == "list-channels":
        cmd_list_channels(token, args.guild)
    elif args.cmd == "create-category":
        cmd_create_category(token, args.guild, args)
    elif args.cmd == "create-channel":
        cmd_create_channel(token, args.guild, args)
    elif args.cmd == "delete-channel":
        cmd_delete_channel(token, args)
    elif args.cmd == "create-role":
        cmd_create_role(token, args.guild, args)
    elif args.cmd == "overwrite":
        cmd_overwrite(token, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
