# PRD — Project Requirements Document

**Proyek:** KickAll — pengosongan member server Discord milik sendiri (kecuali whitelist)
**Versi:** 1.0 · **Tanggal:** 2026-10-04
**Metodologi:** pipeline ngodingpakeai (PRD → ROADMAP → SPECS → TASKS)
**Output bahasa:** Indonesia

---

## Overview

KickAll adalah tool bot Discord berbasis CLI yang meng-kick **seluruh member dari satu
server yang dimiliki pengguna**, dengan **whitelist ketat**: bot tools milik pengguna,
owner server, user tertentu, dan role tertentu tidak pernah tersentuh. Dirancang untuk
pengguna yang ingin "mereset" server sendiri (members pindah/konten lama dibersihkan)
tanpa mengorbankan infrastruktur bot yang sedang berjalan.

Masalah yang dipecahkan: members > 100 tidak mungkin di-kick manual satu-satu, dan
solusi "nuclear" yang beredar biasanya memakai **user token (selfbot)** — melanggar
Discord ToS dan berisiko ban permanen — serta tidak punya tahap preview sehingga
sekali salah eksekusi, member lawas ikut hilang.

Solusi: **bot token resmi + dua tahap (preview → confirm) + whitelist eksplisit +
jeda antar kick**. Semua keputusan kick dihitung oleh satu fungsi murni
(`evaluate_member`) yang teruji unit test, sehingga aturan proteksi bisa diverifikasi
sebelum menyentuh produksi.

## Requirements

**Fungsional**

1. Mengiterasi **seluruh** member guild lewat REST (`fetch_members(limit=None)`),
   bukan cache — hasil akurat untuk guild besar.
2. Dua mode aksi: **preview** (dry-run, nol kick) dan **execute** (kick real-time).
3. Whitelist berlaku sebelum mode apa pun: `whitelist_bots`, `whitelist_users`,
   `whitelist_roles`, plus flag `keep_all_bots`.
4. Proteksi bawaan yang tidak bisa dimatikan: **owner server** dan **bot itu sendiri**.
5. Hormati hierarchy Discord: target dengan role-top ≥ role-top bot dilewati (bukan
   dihitung sebagai error).
6. Jeda terkonfigurasi antar kick (`delay_per_kick`, batas 0.1–10 detik) + auto-retry
   rate limit dari discord.py.
7. Otorisasi perintah: hanya pemilik guild atau owner aplikasi bot.
8. Laporan akhir: total, berhasil, gagal, dilindungi, sampel nama, dan daftar error.

**Non-fungsional**

1. **Tanpa selfbot** — hanya bot token resmi; token tidak pernah di-log.
2. **Zero-trust terhadap config** — `config.json` divalidasi ketat (tipe, rentang,
   placeholder) sebelum login; gagal = pesan jelas + exit code, bukan stack trace.
3. **Tidak ada akses jaringan selain Discord API**; tidak ada telemetri.
4. Log lokal `kickall.log` (INFO) untuk audit debugging; warning level untuk kegagalan.
5. Test tanpa jaringan: seluruh logika keputusan + alur eksekusi diuji dengan stub.
6. Kode modular: logika murni (`kickall_core.py`) terpisah dari orkestrasi Discord
   (`bot.py`) supaya bisa diuji tanpa login.

**Konstraint desain / aturan yang harus menyebar ke semua deliverable**

- Dilarang memakai user token / selfbot (ToS Discord) — ditegaskan di PRD, SPECS, TASKS.
- Tidak ada fitur hapus channel/role/pesan/ban — scope hanya **kick member**.
- Preview wajib sebelum eksekusi; peringatan whitelist kosong tampil **sebelum** aksi.
- Tidak ada fitur yang berjalan tanpa keputusan eksplisit pengguna (`--yes`,
  `kickall confirm`) — tidak ada eksekusi otomatis saat bot boot.

## Core Features

1. **Validasi Config & Proteksi Whitelist** — loader config dengan validasi ketat,
   whitelist bot/user/role, peringatan bila proteksi bot kosong.
2. **Penentuan Target Kick** — fungsi murni `evaluate_member`: urutan aturan
   proteksi → hierarchy → keputusan final beserta alasan.
3. **Eksekusi Berisiko Terkendali** — scan preview/execute, jeda antar kick,
   penanganan `Forbidden`/HTTP, progres live, laporan akhir.
4. **Kendali Via CLI & Bot Discord** — mode `check`/`once`/`run`, perintah
   `kickall` + `kickall confirm`, otorisasi owner-only, penanganan intent.

## User Flow

**Alur 1 — sekali jalan (paling sering dipakai)**

1. `python bot.py check` → config valid / pesan kesalahan spesifik.
2. `python bot.py once <GUILD_ID>` → bot login → daftar member ditarik → laporan
   preview: total, akan di-kick, dilindungi, sampel nama, peringatan whitelist.
3. Pengguna membandingkan angka dengan jumlah member di Discord UI.
4. `python bot.py once <GUILD_ID> --yes` → eksekusi berjeda → laporan akhir
   (berhasil/gagal/dilindungi) → bot keluar sendiri.

**Alur 2 — mode bot online**

1. `python bot.py run` → bot online.
2. Pemilik server kirim `!kickall` → laporan preview (termasuk peringatan whitelist).
3. Pemilik server kirim `!kickall confirm` → pesan status berubah real-time
   (`Proses n/m, sukses, gagal`) → laporan akhir.
4. Non-owner mencoba perintah → ditolak tanpa eksekusi apa pun.

**Alur 3 — kegagalan**

- Token salah → `Token ditolak Discord` + exit 3.
- Intent belum diaktifkan → petunjuk menuju Developer Portal + exit 4.
- Tanpa izin Kick Members → `GAGAL: bot tidak punya izin Kick Members` (tidak ada
  kick yang dicoba).

## Architecture

```
discord-kickall/
├── bot.py            # orkestrasi: argparse CLI, event bot, perintah teks, error UX
├── kickall_core.py   # LOGIKA MURNI: load_config, evaluate_member, scan, formatter
├── test_core.py      # 9 unit test berbasis stub (tanpa jaringan)
├── config.json       # token + whitelist + parameter (divalidasi saat load)
├── requirements.txt  # discord.py==2.7.1 (terkunci)
├── kickall.log       # dihasilkan saat runtime
└── PRD.md / ROADMAP.md / SPECS.md / TASKS.md / README.md
```

Alur data:

```
config.json ──load_config()──▶ cfg (dict tervalidasi)
                                   │
Discord REST ◀──fetch_members(limit=None)── scan(guild, cfg, execute)
                                   │
                    evaluate_member(member) ─▶ Decision(kick, alasan)
                                   │ execute=True
                    member.kick(reason) ─▶ PurgeStats ──▶ formatter ──▶ stdout / pesan Discord
```

Prinsip: `kickall_core` tidak tahu-menahu soal Discord gateway (hanya tipe eksepsi
`discord.Forbidden`/`HTTPException`), sehingga seluruh keputusan kick bisa diuji dengan
stub object. `bot.py` hanya menerjemahkan intent pengguna (CLI/perintah) menjadi
panggilan `scan()`.

## Database Schema

**Tidak ada database.** State dipilih disengaja:

| Data | Penyimpanan | Alasan |
|---|---|---|
| Token, whitelist, parameter | `config.json` (file lokal) | Sekali jalan, mudah diedit, tidak butuh server |
| Riwayat aksi | `kickall.log` + Discord Audit Log | Discord sudah punya audit bawaan untuk kick |
| Status progres | memori proses (`PurgeStats`) | Tidak ada gunanya persist — setiap run baru dihitung ulang |

Jika kelak butuh riwayat (mis. siapa pernah di-kick kapan), skema kandidat:
`kicks(guild_id, user_id, username, kicked_at, reason, batch_id)` di SQLite lokal.
**Tidak diimplementasikan di v1.0** — sumber kebenaran tetap Audit Log Discord.

## Tech Stack

| Layer | Pilihan | Alasan |
|---|---|---|
| Bahasa | Python 3.14 (>= 3.10) | Sudah terpasang di mesin; discord.py resmi |
| Library Discord | `discord.py==2.7.1` (terkunci) | Async, auto rate-limit, resmi didukung Discord |
| CLI | `argparse` (stdlib) | Tanpa dependensi tambahan |
| Konfigurasi | `json` (stdlib) | File tunggal, validasi manual ketat |
| Logging | `logging` (stdlib) → `kickall.log` | Audit trail lokal tanpa layanan eksternal |
| Testing | runner assert manual (`test_core.py`) | Tanpa pytest; stub object, nol jaringan |
| Distribusi | folder project + `requirements.txt` | Tidak perlu build; jalankan `python bot.py` |
| Intents | Server Members + Message Content | Wajib untuk fetch member & perintah teks |
