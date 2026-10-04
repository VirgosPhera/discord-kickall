#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inti logika KickAll: config, keputusan kick, eksekusi, laporan.

Modul ini murni logika — tanpa parsing CLI, tanpa event bot.
Semua keputusan kick ada di `evaluate_member` (pure function, diuji test_core.py).
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable, List, Optional

import discord

log = logging.getLogger("kickall")

DEFAULTS = {
    "whitelist_bots": [],
    "whitelist_users": [],
    "whitelist_roles": [],
    "keep_all_bots": False,
    "delay_per_kick": 0.5,
    "progress_every": 10,
    "reason": "KickAll: cleanup server",
    "command_prefix": "!",
    "allowed_guilds": [],
}


class ConfigError(Exception):
    """Konfigurasi tidak valid / prerequisite tidak terpenuhi."""


def load_config(path: Path) -> dict:
    """Baca + validasi config.json. Melempar ConfigError bila tidak valid."""
    if not path.exists():
        raise ConfigError(f"config tidak ditemukan: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"config JSON rusak: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError("config harus berupa object JSON")

    cfg = {**DEFAULTS, **raw}

    token = cfg.get("token")
    if not isinstance(token, str) or not token.strip() or token.strip().upper().startswith("TOKEN_"):
        raise ConfigError("token bot belum diisi -> edit config.json, isi field 'token'")

    for key in ("whitelist_bots", "whitelist_users", "whitelist_roles", "allowed_guilds"):
        value = cfg.get(key)
        if not isinstance(value, list) or not all(isinstance(x, int) and not isinstance(x, bool) for x in value):
            raise ConfigError(f"{key} harus list ID Discord berupa angka, contoh: [111111111, 222222222]")

    delay = cfg.get("delay_per_kick")
    if isinstance(delay, bool) or not isinstance(delay, (int, float)) or not 0.1 <= float(delay) <= 10:
        raise ConfigError("delay_per_kick harus angka antara 0.1 - 10 (detik)")

    every = cfg.get("progress_every")
    if not isinstance(every, int) or isinstance(every, bool) or every < 1:
        raise ConfigError("progress_every harus integer >= 1")

    if not isinstance(cfg.get("keep_all_bots"), bool):
        raise ConfigError("keep_all_bots harus true atau false")
    if not isinstance(cfg.get("reason"), str) or not cfg["reason"].strip():
        raise ConfigError("reason harus teks (tercatat di audit log Discord)")

    cfg["token"] = token.strip()
    cfg["delay_per_kick"] = float(cfg["delay_per_kick"])
    return cfg


@dataclass(frozen=True)
class Decision:
    """Hasil evaluasi satu member."""

    kick: bool
    reason: str


def evaluate_member(member, *, me, owner_id: Optional[int], cfg: dict) -> Decision:
    """Pure function: bolehkah `member` di-kick?

    Urutan aturan: proteksi (whitelist) dulu, baru hierarchy role.
    `member` / `me` cukup punya: .id, .bot, .roles, .top_role (duck-typed agar testable).
    """
    me_id = getattr(me, "id", None)

    if member.id == me_id:
        return Decision(False, "bot itu sendiri")
    if owner_id is not None and member.id == owner_id:
        return Decision(False, "pemilik server")
    if member.id in cfg["whitelist_users"]:
        return Decision(False, "whitelist user")

    if member.bot and (cfg["keep_all_bots"] or member.id in cfg["whitelist_bots"]):
        return Decision(False, "bot dilindungi")

    if any(getattr(role, "id", None) in cfg["whitelist_roles"] for role in member.roles):
        return Decision(False, "whitelist role")

    # Discord menolak kick bila role top target >= role top bot (hierarchy).
    if member.top_role >= me.top_role:
        return Decision(False, "hierarchy: role target >= role bot")

    return Decision(True, "ok")


@dataclass
class PurgeStats:
    """Akumulasi hasil scan/eksekusi satu guild."""

    total: int = 0
    planned: int = 0
    kicked: int = 0
    failed: int = 0
    skipped: int = 0
    attempted: int = 0
    sample_kick: List[str] = field(default_factory=list)
    sample_keep: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    sample_limit: int = 12


ProgressCb = Callable[[PurgeStats], Awaitable[None]]


def label(member) -> str:
    """Label pendek member untuk laporan: 'nama (id)'."""
    name = getattr(member, "name", None) or getattr(member, "display_name", "?")
    return f"{name} ({getattr(member, 'id', '?')})"


async def scan(guild, cfg: dict, *, execute: bool, on_progress: Optional[ProgressCb] = None) -> PurgeStats:
    """Iterasi seluruh member guild (REST, bukan cache).

    execute=False -> preview murni, tidak ada yang di-kick.
    execute=True   -> kick real-time dengan jeda `delay_per_kick` antar attempt.
    """
    me = guild.me
    if me is None:
        raise ConfigError("bot belum siap di guild ini (guild.me kosong)")
    if not me.guild_permissions.kick_members:
        raise ConfigError("bot tidak punya izin Kick Members di server ini")

    if execute:
        warn = bot_warning(cfg)
        if warn:
            log.warning("%s", warn)

    stats = PurgeStats()
    fire: Optional[ProgressCb] = on_progress if execute else None

    async for member in guild.fetch_members(limit=None):
        stats.total += 1
        verdict = evaluate_member(member, me=me, owner_id=guild.owner_id, cfg=cfg)

        if not verdict.kick:
            stats.skipped += 1
            if len(stats.sample_keep) < stats.sample_limit:
                stats.sample_keep.append(f"{label(member)} - {verdict.reason}")
            continue

        stats.planned += 1
        if len(stats.sample_kick) < stats.sample_limit:
            stats.sample_kick.append(label(member))
        if not execute:
            continue

        stats.attempted += 1
        try:
            await member.kick(reason=cfg["reason"])
            stats.kicked += 1
        except discord.Forbidden:
            stats.failed += 1
            stats.errors.append(f"{label(member)} -> Forbidden (hierarchy/izin)")
            log.warning("gagal kick %s: Forbidden", label(member))
        except discord.HTTPException as exc:
            stats.failed += 1
            stats.errors.append(f"{label(member)} -> HTTP {exc.status}: {exc.text}")
            log.warning("gagal kick %s: HTTP %s", label(member), exc.status)

        if fire is not None and stats.attempted % cfg["progress_every"] == 0:
            await fire(stats)
        await asyncio.sleep(cfg["delay_per_kick"])

    if fire is not None:
        await fire(stats)
    return stats


def _lines_for(title: str, items: List[str], empty: str) -> List[str]:
    if not items:
        return [f"{title}:", f"  {empty}"]
    return [f"{title}:"] + [f"  - {item}" for item in items]


def bot_warning(cfg: dict) -> Optional[str]:
    """Peringatan bila tidak ada proteksi bot sama sekali (whitelist kosong)."""
    if cfg.get("keep_all_bots") or cfg.get("whitelist_bots"):
        return None
    return (
        "PERINGATAN: whitelist_bots kosong dan keep_all_bots=false — "
        "SEMUA bot termasuk bot tools kamu AKAN ikut di-kick. "
        "Isi whitelist_bots / set keep_all_bots=true kalau tidak mau itu terjadi."
    )


def format_preview(stats: PurgeStats) -> str:
    """Laporan mode preview (tidak ada yang di-kick)."""
    lines = [
        "**PREVIEW — belum ada yang di-kick**",
        f"Total member : {stats.total}",
        f"Akan di-kick  : {stats.planned}",
        f"Dilindungi    : {stats.skipped}",
        "",
        *_lines_for("Contoh target kick", stats.sample_kick, "(tidak ada)"),
        "",
        *_lines_for("Contoh yang dilindungi", stats.sample_keep, "(tidak ada)"),
        "",
        "Untuk eksekusi: `kickall confirm`",
    ]
    return "\n".join(lines)


def format_result(stats: PurgeStats) -> str:
    """Laporan mode eksekusi."""
    lines = [
        "**EKSEKUSI SELESAI**",
        f"Total member : {stats.total}",
        f"Berhasil kick: {stats.kicked}",
        f"Gagal        : {stats.failed}",
        f"Dilindungi   : {stats.skipped}",
        "",
        *_lines_for("Contoh yang dilindungi", stats.sample_keep, "(tidak ada)"),
    ]
    if stats.errors:
        lines += ["", *_lines_for("Kegagalan (maks 10)", stats.errors[:10], "(tidak ada)")]
    return "\n".join(lines)


def format_progress(stats: PurgeStats) -> str:
    """Laporan progres selama eksekusi berjalan."""
    return (
        "**KickAll berjalan...**\n"
        f"Proses : {stats.attempted}/{stats.planned}\n"
        f"Kick   : {stats.kicked} sukses, {stats.failed} gagal\n"
        f"Sisa   : {max(stats.planned - stats.attempted, 0)}"
    )
