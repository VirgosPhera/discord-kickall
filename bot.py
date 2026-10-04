#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KickAll — CLI + bot Discord.

Mode:
  python bot.py check                 validasi config.json tanpa login
  python bot.py run                   bot online: !kickall (preview) / !kickall confirm
  python bot.py once <GUILD_ID>       preview satu kali lalu keluar
  python bot.py once <GUILD_ID> --yes eksekusi lalu keluar
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

import discord
from discord.ext import commands

from kickall_core import (
    ConfigError,
    PurgeStats,
    bot_warning,
    format_preview,
    format_progress,
    format_result,
    load_config,
    scan,
)

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
LOG_PATH = BASE_DIR / "kickall.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.FileHandler(LOG_PATH, encoding="utf-8"), logging.StreamHandler()],
)
logging.getLogger("discord").setLevel(logging.WARNING)
log = logging.getLogger("kickall")


def build_intents(*, need_message_content: bool) -> discord.Intents:
    """Intents minimal: members wajib untuk fetch_members; message_content hanya untuk mode run."""
    intents = discord.Intents.default()
    intents.members = True
    intents.message_content = need_message_content
    return intents


def _with_warning(text: str, cfg: dict, execute: bool) -> str:
    """Lampirkan peringatan whitelist kosong — hanya saat preview (sebelum aksi)."""
    if execute:
        return text
    warn = bot_warning(cfg)
    return f"{text}\n\n{warn}" if warn else text


async def _authorize(bot: commands.Bot, ctx: commands.Context) -> bool:
    """Hanya pemilik server ATAU owner aplikasi bot yang boleh menembak."""
    if ctx.author.id == ctx.guild.owner_id:
        return True
    try:
        return await bot.is_owner(ctx.author)
    except discord.ClientException:
        return False


def build_bot(cfg: dict, *, once: Optional[dict] = None) -> commands.Bot:
    """Bangun bot. `once` diisi dict {guild_id, execute, done} bila mode sekali-jalan."""
    intents = build_intents(need_message_content=once is None)
    bot = commands.Bot(command_prefix=cfg["command_prefix"], intents=intents, help_command=None)

    @bot.event
    async def on_ready() -> None:
        log.info("online sebagai %s (%s)", bot.user, getattr(bot.user, "id", "?"))
        if once is not None and not once.get("done"):
            once["done"] = True
            await _one_shot(bot, cfg, once)

    @bot.event
    async def on_command_error(ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply("Izin bot tidak cukup.", mention_author=False)
            return
        log.error("command error: %s", error)

    @bot.command(name="kickall")
    @commands.guild_only()
    async def kickall(ctx: commands.Context, *, action: str = "preview") -> None:
        allowed = cfg.get("allowed_guilds") or []
        if allowed and ctx.guild.id not in allowed:
            await ctx.reply("Server ini tidak diizinkan (allowed_guilds di config.json).", mention_author=False)
            return
        if not await _authorize(bot, ctx):
            await ctx.reply("Hanya pemilik server atau owner bot yang boleh memakai ini.", mention_author=False)
            return

        mode = action.strip().lower()
        if mode in ("confirm", "ya", "execute"):
            execute = True
        elif mode in ("preview", "dry", "dry-run", "lihat"):
            execute = False
        else:
            await ctx.reply(
                f"Pakai `{cfg['command_prefix']}kickall` untuk preview, lalu "
                f"`{cfg['command_prefix']}kickall confirm` untuk eksekusi.",
                mention_author=False,
            )
            return

        status = await ctx.reply("Mengambil daftar member dari Discord...", mention_author=False)

        async def on_progress(stats: PurgeStats) -> None:
            try:
                await status.edit(content=format_progress(stats))
            except discord.HTTPException:
                pass  # rate limit edit — abaikan, laporan akhir tetap dikirim

        try:
            stats = await scan(ctx.guild, cfg, execute=execute, on_progress=on_progress)
        except ConfigError as exc:
            await status.edit(content=f"GAGAL: {exc}")
            return
        except discord.HTTPException as exc:
            await status.edit(content=f"GAGAL mengambil member: HTTP {exc.status} {exc.text}")
            return

        await status.edit(content=_with_warning(format_result(stats) if execute else format_preview(stats), cfg, execute))
        log.info(
            "guild=%s execute=%s total=%s planned=%s kicked=%s failed=%s skipped=%s",
            ctx.guild.id, execute, stats.total, stats.planned,
            stats.kicked, stats.failed, stats.skipped,
        )

    return bot


async def _one_shot(bot: commands.Bot, cfg: dict, opts: dict) -> None:
    """Mode sekali-jalan: login, kerja, cetak laporan, keluar."""
    try:
        guild = bot.get_guild(opts["guild_id"])
        if guild is None:
            print(f"[!] Bot tidak melihat guild {opts['guild_id']}. Invite bot ke server itu dulu.")
            return
        stats = await scan(guild, cfg, execute=opts["execute"])
        print(_with_warning(
            format_result(stats) if opts["execute"] else format_preview(stats),
            cfg,
            opts["execute"],
        ))
        log.info(
            "one-shot guild=%s execute=%s total=%s planned=%s kicked=%s failed=%s skipped=%s",
            guild.id, opts["execute"], stats.total, stats.planned,
            stats.kicked, stats.failed, stats.skipped,
        )
    except ConfigError as exc:
        print(f"[!] {exc}")
    except discord.HTTPException as exc:
        print(f"[!] Gagal mengambil member: HTTP {exc.status} {exc.text}")
    except Exception as exc:  # noqa: BLE001 — satu-satunya jalan keluar harus tetap menutup koneksi
        log.exception("one-shot gagal")
        print(f"[!] {exc}")
    finally:
        await bot.close()


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="kickall",
        description="Kosongkan member dari server Discord milik sendiri, kecuali whitelist.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check", help="validasi config.json tanpa login")
    sub.add_parser("run", help="jalankan bot: perintah kickall / kickall confirm")
    p_once = sub.add_parser("once", help="sekali jalan lalu keluar")
    p_once.add_argument("guild_id", type=int, help="ID server target")
    p_once.add_argument("--yes", action="store_true", help="langsung eksekusi (tanpa preview)")
    args = parser.parse_args(argv)

    try:
        cfg = load_config(CONFIG_PATH)
    except ConfigError as exc:
        print(f"[!] {exc}")
        return 2

    if args.cmd == "check":
        print("[OK] config.json valid.")
        print(f"     prefix         : {cfg['command_prefix']}")
        print(f"     whitelist bots : {cfg['whitelist_bots'] or '-'}")
        print(f"     keep_all_bots  : {cfg['keep_all_bots']}")
        print(f"     whitelist users: {cfg['whitelist_users'] or '-'}")
        print(f"     whitelist roles: {cfg['whitelist_roles'] or '-'}")
        print(f"     allowed_guilds : {cfg['allowed_guilds'] or '(semua server)'}")
        print(f"     delay per kick : {cfg['delay_per_kick']}s")
        warn = bot_warning(cfg)
        if warn:
            print(f"     [!] {warn}")
        return 0

    once = None
    if args.cmd == "once":
        once = {"guild_id": args.guild_id, "execute": bool(args.yes), "done": False}
        if not args.yes:
            print(f"[i] MODE PREVIEW guild {args.guild_id} — tambah --yes untuk eksekusi.")

    bot = build_bot(cfg, once=once)
    try:
        bot.run(cfg["token"], log_handler=None)
    except discord.LoginFailure as exc:
        print(f"[!] Token ditolak Discord: {exc}")
        print("    Cek config.json -> token (Developer Portal -> Bot -> Copy Token).")
        return 3
    except discord.PrivilegedIntentsRequired:
        print("[!] Privileged Gateway Intent belum diaktifkan di Developer Portal.")
        print("    Aktifkan: Server Members Intent (wajib semua mode)")
        if once is None:
            print("             Message Content Intent (wajib mode 'run')")
        print("    https://discord.com/developers/applications -> Bot -> Privileged Gateway Intents")
        return 4
    except discord.HTTPException as exc:
        print(f"[!] Gagal konek: HTTP {exc.status} {exc.text}")
        return 5
    return 0


if __name__ == "__main__":
    sys.exit(main())
