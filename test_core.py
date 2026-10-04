#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Uji logika inti KickAll — tanpa jaringan, tanpa login Discord.

Jalankan:  ./.venv/Scripts/python.exe test_core.py
"""
from __future__ import annotations

import asyncio
import json
import tempfile
import traceback
from pathlib import Path

import discord

from kickall_core import (
    ConfigError,
    bot_warning,
    evaluate_member,
    format_preview,
    format_result,
    load_config,
    scan,
)

TESTS = []


def test(fn):
    TESTS.append(fn)
    return fn


# ---------------------------------------------------------------- stub Discord

EVERYONE_ID = 777
ROLE_MEMBER = 200   # posisi 1
ROLE_MOD = 300      # posisi 2
ROLE_ADMIN = 400    # posisi 3
ROLE_HI = 500       # posisi 4 (di atas bot)


class StubRole:
    """Semantik perbandingan sama dengan discord.Role: posisi lalu id."""

    def __init__(self, id: int, position: int):
        self.id = id
        self.position = position

    def __repr__(self) -> str:
        return f"<StubRole {self.id} pos={self.position}>"

    def __lt__(self, other):
        if self.position != other.position:
            return self.position < other.position
        return self.id > other.id

    def __ge__(self, other) -> bool:
        return not self.__lt__(other)


class StubPerms:
    def __init__(self, kick: bool = True):
        self.kick_members = kick


class StubMember:
    def __init__(self, id, name, *, bot=False, roles=None, top_role=None, error=None, kick_perms=True):
        self.id = id
        self.name = name
        self.bot = bot
        self.roles = list(roles) if roles else []
        if top_role is None:
            top_role = self.roles[-1] if self.roles else StubRole(EVERYONE_ID, 0)
        self.top_role = top_role
        self.error = error
        self.kicked = False
        self.kick_reason = None
        self.guild_permissions = StubPerms(kick_perms)

    async def kick(self, *, reason=None):
        if self.error is not None:
            raise self.error
        self.kicked = True
        self.kick_reason = reason

    def __repr__(self) -> str:
        return f"<StubMember {self.name} bot={self.bot}>"


class StubGuild:
    def __init__(self, *, owner_id, members, me):
        self.owner_id = owner_id
        self.me = me
        self._members = list(members)

    async def fetch_members(self, *, limit=None, after=None):
        for member in self._members:
            yield member


class FakeResponse:
    status = 403
    reason = "Forbidden"


def forbidden():
    return discord.Forbidden(FakeResponse(), {"message": "Missing Permissions", "code": 50013})


def make_cfg(**over) -> dict:
    cfg = {
        "token": "uji-token",
        "whitelist_bots": [9001],
        "whitelist_users": [],
        "whitelist_roles": [],
        "keep_all_bots": False,
        "delay_per_kick": 0.1,
        "progress_every": 1,
        "reason": "uji",
        "command_prefix": "!",
        "allowed_guilds": [],
    }
    cfg.update(over)
    return cfg


def write_cfg(directory: str, payload) -> Path:
    path = Path(directory) / "config.json"
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload), encoding="utf-8")
    return path


# ---------------------------------------------------------------- config

@test
def test_config_valid():
    with tempfile.TemporaryDirectory() as tmp:
        cfg = load_config(write_cfg(tmp, {"token": "abc", "whitelist_bots": [1]}))
        assert cfg["allowed_guilds"] == []
        assert cfg["delay_per_kick"] == 0.1 or isinstance(cfg["delay_per_kick"], float)
        assert cfg["keep_all_bots"] is False


@test
def test_config_rejects_bad_input():
    cases = [
        {"token": "TOKEN_DISINI", "whitelist_bots": []},      # placeholder
        {"token": "", "whitelist_bots": []},                  # kosong
        {"token": "abc", "whitelist_bots": ["123"]},          # string bukan int
        {"token": "abc", "whitelist_bots": [True]},           # bool bukan id
        {"token": "abc", "delay_per_kick": 0.05},             # terlalu cepat
        {"token": "abc", "progress_every": 0},                # nol
        {"token": "abc", "keep_all_bots": "yes"},             # bukan bool
        {"token": "abc", "allowed_guilds": [True]},           # bool bukan id
    ]
    with tempfile.TemporaryDirectory() as tmp:
        for payload in cases:
            try:
                load_config(write_cfg(tmp, payload))
            except ConfigError:
                continue
            raise AssertionError(f"harusnya ConfigError: {payload}")
        try:
            load_config(Path(tmp) / "hilang.json")
        except ConfigError:
            pass
        else:
            raise AssertionError("file hilang harus ConfigError")
        try:
            load_config(write_cfg(tmp, "{rusak"))
        except ConfigError:
            pass
        else:
            raise AssertionError("JSON rusak harus ConfigError")


# ---------------------------------------------------------------- keputusan kick

ME = StubMember(1, "kickbot", bot=True, top_role=StubRole(ROLE_ADMIN, 3))
OWNER = StubMember(2, "owner", top_role=StubRole(ROLE_MOD, 2))
TOOLS = StubMember(9001, "toolsbot", bot=True, top_role=StubRole(ROLE_MEMBER, 1))


def check(member, cfg, owner_id=2, me=ME):
    return evaluate_member(member, me=me, owner_id=owner_id, cfg=cfg)


@test
def test_decide_protections():
    cfg = make_cfg(whitelist_users=[42], whitelist_roles=[31337])
    cases = [
        (ME, False, "bot itu sendiri"),
        (OWNER, False, "pemilik server"),
        (StubMember(42, "vip", top_role=StubRole(ROLE_MEMBER, 1)), False, "whitelist user"),
        (TOOLS, False, "bot dilindungi"),
        (StubMember(50, "mod-role", roles=[StubRole(31337, 1)]), False, "whitelist role"),
    ]
    for member, expect_kick, expect_reason in cases:
        verdict = check(member, cfg)
        assert verdict.kick is expect_kick, f"{member!r} -> {verdict}"
        assert verdict.reason == expect_reason, f"{member!r} -> {verdict}"


@test
def test_decide_hierarchy_and_normal():
    cfg = make_cfg()
    assert check(StubMember(60, "biasa", roles=[StubRole(ROLE_MEMBER, 1)]), cfg).kick is True
    assert check(StubMember(61, "everybody"), cfg).kick is True
    high = check(StubMember(62, "lebih-tinggi", top_role=StubRole(ROLE_HI, 4)), cfg)
    assert high.kick is False and "hierarchy" in high.reason
    same = check(StubMember(63, "sama-role", top_role=StubRole(ROLE_ADMIN, 3)), cfg)
    assert same.kick is False and "hierarchy" in same.reason


@test
def test_decide_keep_all_bots():
    cfg = make_cfg(keep_all_bots=True)
    assert check(StubMember(70, "bot-lain", bot=True, top_role=StubRole(ROLE_MEMBER, 1)), cfg).kick is False
    assert check(StubMember(71, "orang", top_role=StubRole(ROLE_MEMBER, 1)), cfg).kick is True


# ---------------------------------------------------------------- scan

def build_guild(*, carol_error=None) -> StubGuild:
    members = [
        ME,
        OWNER,
        TOOLS,
        StubMember(10, "alice", roles=[StubRole(ROLE_MEMBER, 1)]),
        StubMember(11, "bob", top_role=StubRole(ROLE_HI, 4)),
        StubMember(12, "dave"),
        StubMember(13, "carol", roles=[StubRole(ROLE_MEMBER, 1)], error=carol_error),
    ]
    return StubGuild(owner_id=2, members=members, me=ME)


@test
def test_scan_preview_no_kicks():
    guild = build_guild()
    stats = asyncio.run(scan(guild, make_cfg(), execute=False))
    assert stats.total == 7
    assert stats.planned == 3          # alice, dave, carol
    assert stats.skipped == 4          # me, owner, tools, bob
    assert stats.kicked == 0 and stats.failed == 0 and stats.attempted == 0
    assert not any(m.kicked for m in guild._members)


@test
def test_scan_execute_kicks_targets_only():
    guild = build_guild(carol_error=forbidden())
    calls = []

    async def progress(stats):
        calls.append((stats.attempted, stats.kicked, stats.failed))

    stats = asyncio.run(scan(guild, make_cfg(), execute=True, on_progress=progress))
    assert stats.total == 7 and stats.planned == 3 and stats.skipped == 4
    assert stats.kicked == 2 and stats.failed == 1 and stats.attempted == 3

    by_name = {m.name: m for m in guild._members}
    assert by_name["alice"].kick_reason == "uji"
    assert by_name["dave"].kick_reason == "uji"
    assert not by_name["carol"].kicked          # gagal: Forbidden
    assert not TOOLS.kicked                      # whitelist bot selamat
    assert not OWNER.kicked and not ME.kicked
    assert not by_name["bob"].kicked             # hierarchy di atas bot
    assert len(stats.errors) == 1 and "Forbidden" in stats.errors[0]
    assert calls and calls[-1][0] == 3          # progres terakhir saat attempt terakhir
    assert stats.sample_kick and stats.sample_keep


@test
def test_scan_requires_kick_permission():
    guild = build_guild()
    guild.me = StubMember(1, "kickbot", bot=True, top_role=StubRole(ROLE_ADMIN, 3), kick_perms=False)
    try:
        asyncio.run(scan(guild, make_cfg(), execute=True))
    except ConfigError as exc:
        assert "Kick Members" in str(exc)
    else:
        raise AssertionError("tanpa izin Kick Members harus ConfigError")


# ---------------------------------------------------------------- laporan & warning

@test
def test_formatters_and_warning():
    guild = build_guild()
    preview = asyncio.run(scan(guild, make_cfg(), execute=False))
    text = format_preview(preview)
    assert "PREVIEW" in text and "kickall confirm" in text and "Dilindungi" in text

    guild2 = build_guild(carol_error=forbidden())
    result = asyncio.run(scan(guild2, make_cfg(), execute=True))
    done = format_result(result)
    assert "EKSEKUSI SELESAI" in done and "Berhasil kick: 2" in done and "Gagal        : 1" in done

    assert bot_warning(make_cfg(whitelist_bots=[])) is not None
    assert bot_warning(make_cfg(whitelist_bots=[1])) is None
    assert bot_warning(make_cfg(whitelist_bots=[], keep_all_bots=True)) is None


def main() -> int:
    failed = 0
    for fn in TESTS:
        try:
            fn()
        except Exception:  # noqa: BLE001
            failed += 1
            print(f"FAIL {fn.__name__}")
            traceback.print_exc()
        else:
            print(f"PASS {fn.__name__}")
    print(f"\n{len(TESTS) - failed}/{len(TESTS)} test lulus")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
