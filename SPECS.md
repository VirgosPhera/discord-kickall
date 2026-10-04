# SPECS — Spesifikasi 4 Bagian per Fitur

Urutan fitur dan sub-fitur **sama persis** dengan `ROADMAP.md`. Tiap blok memuat:
**Tujuan / Detail Implementasi / Aturan & Batasan / Kriteria Penerimaan**.
Constraint yang menyebar (dari PRD): tanpa selfbot · tanpa hapus channel/role/pesan/ban ·
preview wajib sebelum eksekusi · tanpa eksekusi otomatis saat boot.

---

## F1 — Konfigurasi & Proteksi

### Spec F1 (fitur induk)

**Tujuan**
Menjamin hanya konfigurasi yang valid dan disengaja yang sampai ke proses login, dan
menjamin siapa yang tidak boleh tersentuh (whitelist) sudah terdefinisi sebelum
satu kick pun dihitung.

**Detail Implementasi**
`kickall_core.load_config(path)` membaca `config.json`, meng-merge dengan `DEFAULTS`,
lalu memvalidasi: token non-kosong dan bukan placeholder (`TOKEN_...`), keempat list ID
berupa `int` murni (bukan `bool`), `delay_per_kick` dalam 0.1–10, `progress_every` ≥ 1,
`keep_all_bots` bool, `reason` teks non-kosong. Hasil: dict `cfg` yang dipakai semua
modul lain. `bot_warning(cfg)` mengembalikan teks peringatan bila `whitelist_bots`
kosong dan `keep_all_bots=false`.

**Aturan & Batasan**
- Gagal validasi = `ConfigError` dengan pesan yang menyebut nama field — bukan
  exception tak tertangani.
- Validasi terjadi **sebelum** `bot.run()`: tidak ada koneksi Discord dengan config rusak.
- Token tidak pernah ditulis ke log/stdout (hanya "token ditolak" bila Discord menolak).
- Tidak ada penggunaan user token/selfbot dalam bentuk apa pun.

**Kriteria Penerimaan**
- `bot.py check` mencetak ringkasan config (prefix, whitelist, delay) dan exit 0.
- Placeholder token / tipe salah → pesan field spesifik, exit 2.
- Peringatan whitelist kosong tampil di `check` dan di preview.

### Sub-spec F1.1 — Validasi Config

**Tujuan:** menolak config cacat sebelum login.
**Detail:** `load_config` mengecek keberadaan file, parse JSON, tipe dict, lalu semua
field wajib; nilai `bool` ditolak untuk list ID karena `bool` subclass `int`.
**Aturan:** pesan error selalu menyebut field + contoh format yang benar.
**Kriteria:** 8 kasus invalid + file hilang + JSON rusak semuanya melempar `ConfigError`
(diuji `test_config_rejects_bad_input`).

### Sub-spec F1.2 — Whitelist Bot & User

**Tujuan:** bot tools dan orang tertentu tidak pernah di-kick.
**Detail:** `whitelist_bots` / `whitelist_users` dicek di `evaluate_member` sebelum
logika lain; ID dibandingkan sebagai `int`.
**Aturan:** `keep_all_bots=true` membuat semua bot lolos tanpa perlu daftar ID.
**Kriteria:** bot tools dengan role rendah pun tetap `Decision(kick=False, "bot dilindungi")`
(diuji `test_decide_protections`, `test_decide_keep_all_bots`).

### Sub-spec F1.3 — Whitelist Role & Allowed Guild

**Tujuan:** proteksi kelompok member dan pembatasan server.
**Detail:** `whitelist_roles` dicek terhadap `member.roles` (termasuk @everyone);
`allowed_guilds` dicek di `bot.py` sebelum handler perintah berjalan — kosong = semua
server yang di-invite diizinkan.
**Aturan:** `allowed_guilds` non-kosong menolak perintah di luar daftar tanpa membaca
member apa pun.
**Kriteria:** member ber-role whitelist → dilindungi; guild tak terdaftar → balasan
penolakan, nol kick.

### Sub-spec F1.4 — Peringatan Whitelist Kosong

**Tujuan:** mencegah pengguna tidak sadar meng-kick semua bot termasuk bot toolsnya.
**Detail:** `bot_warning(cfg)` dipanggil di `check`, mode preview CLI, dan perintah
chat preview (`_with_warning`); di `scan(execute=True)` dipetakan ke `log.warning`.
**Aturan:** peringatan hanya tampil **sebelum** aksi (preview), tidak menghalangi eksekusi.
**Kriteria:** preview dengan `whitelist_bots=[]` memuat kata "PERINGATAN" dan "bot tools";
preview dengan whitelist terisi tidak memuatnya.

---

## F2 — Penentuan Target Kick

### Spec F2 (fitur induk)

**Tujuan**
Menyatukan seluruh keputusan kick dalam satu fungsi murni yang bisa diuji tanpa
jaringan, sehingga aturan proteksi tidak pernah bergantung pada state Discord.

**Detail Implementasi**
`kickall_core.evaluate_member(member, *, me, owner_id, cfg) -> Decision(kick: bool,
reason: str)` dievaluasi berurutan: (1) id == id bot, (2) id == `guild.owner_id`,
(3) `whitelist_users`, (4) bot & (`keep_all_bots` atau `whitelist_bots`),
(5) irisan `member.roles` dengan `whitelist_roles`, (6) `member.top_role >=
me.top_role` → dilindungi karena hierarchy. Lolos semua → `Decision(True, "ok")`.
Parameter bersifat duck-typed (`id`, `bot`, `roles`, `top_role`) agar test cukup stub.

**Aturan & Batasan**
- Urutan tidak boleh dibalik: whitelist harus dicek **sebelum** hierarchy supaya alasan
  yang tampil di laporan mencerminkan proteksi, bukan kebetulan hierarchy.
- Tidak ada I/O, tidak ada exception untuk kondisi normal — semua hasil lewat `Decision`.
- Hierarchy mengikuti semantik `discord.Role.__ge__` (posisi, lalu id; @everyone
  paling bawah): target setara role bot = dilindungi, bukan error.

**Kriteria Penerimaan**
- 6 kategori proteksi + 4 kasus hierarchy/normal teruji (`test_decide_*`), tanpa login.
- Tidak ada `guild.*`/`http.*` yang dipanggil dari fungsi ini.

### Sub-spec F2.1 — Urutan Aturan Proteksi

**Tujuan:** keputusan deterministik dan alasan akurat.
**Detail:** ladder if bertingkat di `evaluate_member`; return pertama yang cocok menang.
**Aturan:** bot sendiri dan owner server tidak bisa dimatikan dari config.
**Kriteria:** setiap kasus menghasilkan `reason` persis seperti yang diharapkan test.

### Sub-spec F2.2 — Pemeriksaan Hierarchy Role

**Tujuan:** menghindari ratusan error `Forbidden` yang membanjiri log.
**Detail:** perbandingan `member.top_role >= me.top_role` memakai operator bawaan
`discord.Role`.
**Aturan:** target setara/lebih tinggi dihitung `skipped` (dilindungi), bukan `failed`.
**Kriteria:** member role posisi 4 vs bot posisi 3 → `kick=False` ber-alasan hierarchy;
member @everyone → layak kick.

### Sub-spec F2.3 — Alasan Keputusan per Member

**Tujuan:** pengguna paham kenapa seseorang tidak di-kick.
**Detail:** `reason` string berbahasa Indonesia, dirangkai di laporan via
`sample_keep` format `nama (id) - alasan` (maks 12 entri).
**Aturan:** alasan tidak memuat token atau data sensitif apa pun.
**Kriteria:** preview menampilkan minimal satu baris contoh "dilindungi" beserta alasannya.

---

## F3 — Eksekusi & Kendali Risiko

### Spec F3 (fitur induk)

**Tujuan**
Menjalankan iterasi seluruh member guild dengan risiko terkendali: preview benar-benar
nol aksi, eksekusi berjeda dan tidak berhenti di tengah jalan karena satu kegagalan,
dan hasil akhir terukur.

**Detail Implementasi**
`kickall_core.scan(guild, cfg, *, execute, on_progress=None) -> PurgeStats`:
1. Pra-kondisi: `guild.me` ada dan `me.guild_permissions.kick_members` — kalau tidak,
   `ConfigError` sebelum iterasi dimulai.
2. Iterasi `guild.fetch_members(limit=None)` (REST, cursor id — tidak bergantung cache).
3. Per member: `evaluate_member` → bila dilindungi, masuk `skipped` + sampel alasan;
   bila layak, masuk `planned` + sampel nama; `execute=False` berhenti di sini.
4. `execute=True`: `await member.kick(reason=cfg["reason"])`, tangkap `Forbidden` dan
   `HTTPException` ke `errors[]` (run tetap lanjut), tunggu `delay_per_kick`, panggil
   `on_progress` tiap `progress_every` attempt dan sekali di akhir.
5. `PurgeStats` (total, planned, kicked, failed, skipped, attempted, sample_*, errors)
   diformat `format_preview` / `format_result` / `format_progress`.

**Aturan & Batasan**
- **Preview = nol side effect**: tidak ada `member.kick`, tidak ada sleep, tidak ada
  panggilan API tulis.
- Gagal per member dicatat, bukan dilempar — satu 403 tidak boleh membatalkan run.
- `delay_per_kick` ≥ 0.1s (divalidasi config); discord.py menangani retry 429 otomatis.
- Scope hanya `member.kick` — tidak ada `ban`, `purge`, `delete`, `edit` di modul ini.
- Tidak ada auto-run: `scan(execute=True)` hanya dipanggil dari `--yes` /
  `kickall confirm`.

**Kriteria Penerimaan**
- `test_scan_preview_no_kicks`: 7 member, 3 layak, 4 dilindungi, nol objek `kicked`.
- `test_scan_execute_kicks_targets_only`: 2 sukses, 1 `Forbidden` → `failed`, whitelist
  selamat, owner/bot sendiri/hierarchy tidak tersentuh, callback progres terpanggil.
- `test_scan_requires_kick_permission`: tanpa izin → `ConfigError`, nol kick dicoba.

### Sub-spec F3.1 — Scan Preview Dry-Run

**Tujuan:** pengguna bisa memverifikasi target sebelum kehilangan apa pun.
**Detail:** cabang `execute=False` pada `scan` — mengisi `planned`/`skipped`/sampel
tanpa blok eksekusi.
**Aturan:** keluaran preview selalu menyertakan langkah lanjut (`kickall confirm`).
**Kriteria:** assert `attempted == 0` dan `not any(m.kicked ...)` pada test preview.

### Sub-spec F3.2 — Eksekusi Berjeda + Penanganan Gagal

**Tujuan:** tahan rate limit dan tidak putus di tengah.
**Detail:** `asyncio.sleep(delay_per_kick)` per attempt; `discord.Forbidden` →
`errors[]` format `nama (id) -> Forbidden (hierarchy/izin)`; `HTTPException` →
`errors[]` dengan status+teks.
**Aturan:** penamaan error memuat kata `Forbidden` agar mudah dicari di log.
**Kriteria:** run dengan satu anggota yang selalu `Forbidden` tetap menyelesaikan
anggota lain dan melaporkan `failed=1`.

### Sub-spec F3.3 — Progres Live & Laporan

**Tujuan:** tahu posisi jalan tanpa membaca log mentah.
**Detail:** `format_progress` (Proses n/m, Kick sukses/gagal, Sisa) diedit ke pesan
status Discord; `format_progress` gagal edit karena 429 diabaikan (laporan akhir tetap
dikirim).
**Aturan:** laporan akhir memuat total/berhasil/gagal/dilindungi + maks 10 error.
**Kriteria:** teks laporan akhir memuat `EKSEKUSI SELESAI` dan angka yang cocok dengan
counter (dites `test_formatters_and_warning`).

### Sub-spec F3.4 — Mode Sekali Jalan

**Tujuan:** alur paling umum: sekali jalan lalu proses berakhir bersih.
**Detail:** `bot.py once <GUILD_ID> [--yes]` menaruh `{"guild_id", "execute", "done"}`
di closure; `on_ready` menjalankan `_one_shot` tepat sekali (flag `done` menahan
reconnect), mencetak laporan ke stdout, lalu `await bot.close()` di blok `finally`.
**Aturan:** tanpa `--yes` = preview (dengan petunjuk menambah `--yes`).
**Kriteria:** guild tak terlihat → pesan jelas + tetap menutup koneksi; exception apa pun
tetap melewati `finally` (koneksi tidak menggantung).

---

## F4 — Kendali Via CLI & Bot

### Spec F4 (fitur induk)

**Tujuan**
Menerjemahkan maksud pengguna menjadi panggilan `scan` yang tepat, dengan otorisasi
ketat dan kegagalan operasional yang bisa ditindaklanjuti.

**Detail Implementasi**
`bot.py`:
- `main()` → argparse tiga subcommand: `check` (validasi + cetak ringkasan, exit 0),
  `run` (bot online), `once` (sekali jalan, argumen `guild_id` + flag `--yes`).
- `build_intents(need_message_content=...)` → `members=True` selalu; `message_content`
  hanya untuk mode `run` (menghindari permintaan intent yang tidak dipakai).
- `build_bot(cfg, once=...)` → `commands.Bot`; handler `kickall` dengan gate:
  `allowed_guilds` → `_authorize` (pemilik guild ATAU `bot.is_owner`) → parsing mode →
  `scan` → edit pesan status dengan laporan.
- Penanganan `discord.LoginFailure` (exit 3), `PrivilegedIntentsRequired` (exit 4 +
  petunjuk portal), `HTTPException` (exit 5), `ConfigError` (exit 2).

**Aturan & Batasan**
- Hanya dua pemicu eksekusi: flag `--yes` dan perintah `confirm` — tidak ada yang lain.
- Balasan untuk non-owner bersifat menolak tegas tanpa membocorkan info server.
- Pesan error CLI menyebut lokasi perbaikan (file config / halaman portal).
- Intents diminta seperlunya; `once` tidak meminta Message Content.

**Kriteria Penerimaan**
- `bot.py --help` menampilkan tiga mode; `check` valid → ringkasan; token placeholder →
  exit 2 (teruji manual).
- Login dengan token palsu menghasilkan `Token ditolak Discord: ...` + exit 3
  (teruji smoke test).
- Perintah di luar guild, oleh non-owner, atau di guild terlarang → ditolak sebelum scan.

### Sub-spec F4.1 — Subcommand check / once / run

**Tujuan:** jalur terpisah untuk verifikasi, eksekusi tunggal, dan bot jangka panjang.
**Detail:** `argparse` dengan `subparsers(required=True)`; `once` memaksa `guild_id`
bertipe `int`.
**Aturan:** `check` tidak pernah menyentuh jaringan.
**Kriteria:** ketiga subcommand muncul di `--help`; `check` bekerja tanpa intent apa pun.

### Sub-spec F4.2 — Perintah kickall + confirm

**Tujuan:** kontrol dari dalam server tanpa membuka terminal.
**Detail:** `@bot.command(name="kickall")` + `@commands.guild_only()`; argumen `action`
(`preview` default, `confirm`/`ya`/`execute` mengeksekusi); argumen lain → balasan
pemakaian.
**Aturan:** prefix dari config (`command_prefix`); tanpa `Message Content Intent`
perintah tidak jalan (dokumentasikan di README).
**Kriteria:** `kickall` → laporan preview + langkah lanjut; `kickall confirm` → progres
lalu laporan akhir.

### Sub-spec F4.3 — Otorisasi Owner-Only

**Tujuan:** perintah merusak tidak bisa dipanggil anggota biasa.
**Detail:** `_authorize` menimbang `ctx.author.id == ctx.guild.owner_id` atau
`await bot.is_owner(ctx.author)` (dibungkus `try/except ClientException`).
**Aturan:** penolakan terjadi sebelum `scan` dipanggil (nol API baca member).
**Kriteria:** member non-owner menerima balasan penolakan dan tidak ada pesan progres.

### Sub-spec F4.4 — Penanganan Intent & Error Login

**Tujuan:** kegagalan setup terjawab dalam satu pesan, bukan traceback.
**Detail:** `try/except` di sekitar `bot.run` memetakan empat exception discord.py ke
pesan + exit code; pesan `PrivilegedIntentsRequired` mencantumkan intent yang relevan
per mode.
**Aturan:** token asli tidak pernah dicetak.
**Kriteria:** token palsu → exit 3 dengan petunjuk Developer Portal (terverifikasi
lewat smoke test terisolasi).
