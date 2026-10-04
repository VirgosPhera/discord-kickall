# ROADMAP — Pohon Fitur KickAll

Sumber dari `PRD.md`. Ikon diambil dari enum feature-skeleton ngodingpakeai
(`lock, dashboard, chat, bell, export, users, chart, calendar, settings, search,
file, payment, shield, box`). Prioritas = urgensi membangun, bukan urutan kerja.

**Aturan yang menyebar ke semua fitur:** tanpa selfbot/user token · tanpa
penghapusan channel/role/pesan/ban · preview wajib sebelum eksekusi · whitelist
dipertimbangkan sebelum hierarchy · tanpa eksekusi otomatis saat boot.

---

## Fitur Utama

| # | Fitur | Ringkasan | Ikon | Prioritas |
|---|---|---|---|---|
| F1 | Konfigurasi & Proteksi | Config tervalidasi ketat plus whitelist yang menentukan siapa yang tidak akan pernah di-kick | shield | high |
| F2 | Penentuan Target Kick | Satu fungsi murni yang memutus kick/tidak untuk tiap member beserta alasannya | search | high |
| F3 | Eksekusi & Kendali Risiko | Scan preview/execute dengan jeda, penanganan error Discord, progres live, laporan akhir | box | high |
| F4 | Kendali Via CLI & Bot | Tiga mode CLI plus perintah teks `kickall` yang hanya bisa dipakai owner | chat | medium |

---

## F1 — Konfigurasi & Proteksi

| Sub-fitur | Ringkasan | Ikon | Prioritas |
|---|---|---|---|
| Validasi Config | Tolak token placeholder, tipe salah, rentang nilai ilegal sebelum login | settings | high |
| Whitelist Bot & User | `whitelist_bots` (bot tools) dan `whitelist_users` lolos tanpa syarat | users | high |
| Whitelist Role & Guild | `whitelist_roles` plus `allowed_guilds` untuk membatasi server yang boleh disentuh | lock | high |
| Peringatan Whitelist Kosong | Preview menampilkan peringatan bila tidak ada proteksi bot sama sekali | bell | high |

## F2 — Penentuan Target Kick

| Sub-fitur | Ringkasan | Ikon | Prioritas |
|---|---|---|---|
| Urutan Aturan Proteksi | Bot sendiri → owner → whitelist user → whitelist bot → whitelist role | shield | high |
| Pemeriksaan Hierarchy | Role-top target ≥ role-top bot dilewati sebagai "dilindungi", bukan error | lock | high |
| Alasan Keputusan | Tiap keputusan membawa teks alasan yang muncul di laporan preview | file | medium |

## F3 — Eksekusi & Kendali Risiko

| Sub-fitur | Ringkasan | Ikon | Prioritas |
|---|---|---|---|
| Scan Preview Dry-Run | Iterasi seluruh member via REST tanpa satu pun kick dieksekusi | dashboard | high |
| Eksekusi Berjeda | Jeda `delay_per_kick` antar attempt, `Forbidden`/HTTP dicatat bukan menghentikan run | bell | high |
| Progres Live & Laporan | Pembaruan `n/m sukses gagal` selama jalan plus ringkasan akhir | chart | medium |
| Mode Sekali Jalan | `once <guild> [--yes]` login → kerja → cetak → keluar tanpa sisa proses | settings | medium |

## F4 — Kendali Via CLI & Bot

| Sub-fitur | Ringkasan | Ikon | Prioritas |
|---|---|---|---|
| Subcommand check / once / run | `check` validasi config tanpa login; `once` sekali jalan; `run` bot online | settings | high |
| Perintah kickall + confirm | Dua langkah di chat: preview dulu, `kickall confirm` untuk eksekusi | chat | high |
| Otorisasi Owner-Only | Hanya pemilik guild atau owner aplikasi bot; selain itu ditolak | lock | high |
| Penanganan Intent & Error Login | Pesan jelas + exit code untuk token salah, intent mati, HTTP gagal | bell | medium |

---

## Fase Eksekusi

| Fase | Isi | Status |
|---|---|---|
| 1 | `kickall_core`: config loader + `evaluate_member` + `scan` + formatter | ✅ selesai, 9/9 test |
| 2 | `bot.py`: CLI `check`/`once`/`run`, perintah teks, penanganan error login | ✅ selesai, smoke test login |
| 3 | Dokumen: PRD → ROADMAP → SPECS → TASKS → README | ✅ selesai |
| 4 | Setup manual pengguna: token, intents, invite, isi `whitelist_bots` | ⏳ menunggu pengguna |
| 5 | Dry-run di server produksi (mode `once` tanpa `--yes`) lalu eksekusi | ⏳ menunggu fase 4 |

**Cross-reference:** `SPECS.md` = detail 4-bagian tiap fitur · `TASKS.md` = prompt
siap-tempel per sub-fitur · `test_core.py` = bukti perilaku F1–F3.
