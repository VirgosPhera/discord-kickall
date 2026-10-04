# TASKS — Task Siap-Tempel

Urutan dan penamaan mengikuti `ROADMAP.md` + `SPECS.md`. Tiap task memuat **prompt
markdown** yang bisa ditempel apa adanya ke AI coding agent.

**Status:** seluruh task fase 1–3 sudah diimplementasikan dan teruji
(`test_core.py` 9/9 lulus, smoke test CLI sampai login Discord). Task dipakai sebagai
**checklist verifikasi** atau bila project perlu di-port ulang.

**Aturan yang disertakan di setiap prompt (menyebar dari PRD):**
- bot token resmi saja — dilarang user token / selfbot (ToS Discord)
- scope hanya kick member — tidak ada hapus channel/role/pesan/ban
- preview wajib sebelum eksekusi; tidak ada auto-run saat boot
- chunked write: maksimal 300 baris per operasi tulis

---

## F1 — Konfigurasi & Proteksi

### T1.1 — Loader config tervalidasi
**Sub-fitur:** F1.1 Validasi Config · **Priority:** high
**Deskripsi:** `load_config()` menolak config cacat sebelum koneksi Discord dibuat.

````markdown
Buat `kickall_core.load_config(path: Path) -> dict` untuk project Python
`discord-kickall` (dependensi: discord.py==2.7.1, stdlib saja):

- merge `DEFAULTS`: whitelist_bots, whitelist_users, whitelist_roles,
  keep_all_bots(false), delay_per_kick(0.5), progress_every(10),
  reason, command_prefix("!"), allowed_guilds([])
- tolak dengan `ConfigError` yang MENYEBUT nama field + contoh format:
  file hilang · JSON rusak · hasil bukan dict · token kosong / placeholder
  "TOKEN_..." · list ID berisi non-int (termasuk `bool`) · delay_per_kick di luar
  0.1–10 · progress_every < 1 · keep_all_bots bukan bool · reason kosong
- token di-strip, delay dikonversi float, config tidak pernah di-print apa adanya

Aturan: tanpa jaringan, tanpa login, token asli tidak pernah muncul di pesan error.
Verifikasi: tambahkan test dengan 8 kasus invalid + file hilang + JSON rusak,
semua harus melempar ConfigError.
````

### T1.2 — Whitelist bot, user, role, dan allowed_guilds
**Sub-fitur:** F1.2 + F1.3 · **Priority:** high
**Deskripsi:** Daftar proteksi yang membuat target tertentu tidak pernah tersentuh.

````markdown
Di `kickall_core.py` + `bot.py` project `discord-kickall`:

1. `evaluate_member()` wajib mengecek, SEBELUM logika lain:
   `whitelist_users` (id member), bot dengan id di `whitelist_bots`
   (atau `keep_all_bots=true` untuk semua bot), irisan `member.roles` dengan
   `whitelist_roles` → `Decision(kick=False, reason="<kategori>")`.
2. `bot.py` menolak perintah bila `allowed_guilds` terisi dan `ctx.guild.id`
   tidak ada di daftar — tolak sebelum memanggil scan (nol API call).

Aturan: bandingkan ID sebagai `int` murni; alasan berbahasa Indonesia.
Verifikasi: test membuktikan bot tools ber-role rendah pun tetap dilindungi,
dan guild di luar allowed_guilds menerima balasan penolakan tanpa progres.
````

### T1.3 — Peringatan whitelist kosong
**Sub-fitur:** F1.4 · **Priority:** high
**Deskripsi:** Pengguna diperingatkan sebelum meng-kick semua bot termasuk bot toolsnya.

````markdown
Di project `discord-kickall` buat `bot_warning(cfg) -> Optional[str]`:
mengembalikan teks peringatan bila `whitelist_bots` kosong DAN `keep_all_bots=false`,
selain itu `None`.

Pasang di tiga titik SEBELUM aksi:
- `bot.py check` → cetak setelah ringkasan config
- preview CLI (`once` tanpa `--yes`) → lampirkan setelah laporan preview
- perintah chat preview `kickall` → lampirkan di akhir pesan preview
- `scan(execute=True)` → `log.warning` saja (jangan memblokir eksekusi)

Aturan: peringatan hanya tampil di mode preview, tidak pernah menahan eksekusi.
Verifikasi: preview kosong memuat kata "PERINGATAN" dan "bot tools";
preview terisi tidak memuatnya.
````

---

## F2 — Penentuan Target Kick

### T2.1 — Ladder aturan proteksi (fungsi murni)
**Sub-fitur:** F2.1 · **Priority:** high
**Deskripsi:** Satu fungsi menentukan kick/tidak untuk tiap member beserta alasan.

````markdown
Buat `kickall_core.evaluate_member(member, *, me, owner_id, cfg) -> Decision`
(kick: bool, reason: str) — pure function, tanpa I/O, tanpa akses Discord API.

Urutan ladder (return pertama yang cocok menang):
1. id == id bot sendiri → "bot itu sendiri"
2. id == owner_id → "pemilik server"
3. id di whitelist_users → "whitelist user"
4. bot & (keep_all_bots atau id di whitelist_bots) → "bot dilindungi"
5. ada role di whitelist_roles → "whitelist role"
6. member.top_role >= me.top_role → "hierarchy: role target >= role bot"
7. lolos → Decision(True, "ok")

Aturan: parameter duck-typed (hanya .id/.bot/.roles/.top_role) supaya bisa diuji stub;
urutan tidak boleh dibalik (whitelist dicek sebelum hierarchy).
Verifikasi: satu test per kasus dengan stub object, tanpa jaringan.
````

### T2.2 — Pemeriksaan hierarchy role
**Sub-fitur:** F2.2 · **Priority:** high
**Deskripsi:** Target setara/lebih tinggi dihitung dilindungi, bukan error.

````markdown
Di `evaluate_member` (project `discord-kickall`) gunakan operator
bawaan `discord.Role` untuk perbandingan: `member.top_role >= me.top_role`.

Konteks semantik discord.Role: posisi lebih rendah dulu, lalu id; @everyone selalu
paling bawah; role dari guild berbeda akan melempar RuntimeError (pastikan semua
objek berasal dari guild yang sama).

Aturan: hasilnya `Decision(False, "hierarchy...")` — dihitung `skipped` pada laporan,
BUKAN `failed`.
Verifikasi: test target role posisi 4 vs bot posisi 3 → dilindungi;
member @everyone vs bot role posisi 3 → layak kick.
````

### T2.3 — Alasan keputusan pada laporan
**Sub-fitur:** F2.3 · **Priority:** medium
**Deskripsi:** Preview menjelaskan kenapa seseorang tidak ikut di-kick.

````markdown
Di `kickall_core.py` buat `label(member)` → `"nama (id)"`, lalu isi
`PurgeStats.sample_kick` (maks 12) dan `sample_keep` berformat
`"nama (id) - alasan"` selama scan.

Tampilkan keduanya di `format_preview` dengan judul "Contoh target kick" dan
"Contoh yang dilindungi", plus `(tidak ada)` bila kosong.

Aturan: tanpa data sensitif (token/permission mentah); id angka aman dicatat.
Verifikasi: preview berisi minimal satu baris tiap daftar beserta alasan.
````

---

## F3 — Eksekusi & Kendali Risiko

### T3.1 — Scan preview dry-run (nol side effect)
**Sub-fitur:** F3.1 · **Priority:** high
**Deskripsi:** Iterasi seluruh member via REST tanpa satu pun kick.

````markdown
Buat `kickall_core.scan(guild, cfg, *, execute, on_progress=None) -> PurgeStats` di
`discord-kickall`:

- pra-kondisi: `guild.me` non-kosong dan `me.guild_permissions.kick_members` —
  kalau tidak, lempar `ConfigError` SEBELUM iterasi
- iterasi `guild.fetch_members(limit=None)` (REST penuh, bukan cache; butuh
  Intents.members)
- per member: `evaluate_member` → dilindungi = `skipped` + sampel alasan;
  layak = `planned` + sampel nama; cabang `execute=False` berhenti di sini

Aturan preview: TIDAK ADA `member.kick`, tidak ada sleep, tidak ada API tulis.
Verifikasi: test preview menghitung total/planned/skipped benar dan
`not any(m.kicked for m in members)`.
````

### T3.2 — Eksekusi berjeda + penanganan gagal
**Sub-fitur:** F3.2 · **Priority:** high
**Deskripsi:** Satu kegagalan tidak boleh membatalkan seluruh run.

````markdown
Lengkapi `scan(..., execute=True)` di `kickall_core.py`:

- `await member.kick(reason=cfg["reason"])` → `stats.kicked += 1`
- `discord.Forbidden` → `failed`, errors[] format
  `"nama (id) -> Forbidden (hierarchy/izin)"`, lanjut ke member berikutnya
- `discord.HTTPException` → `failed`, errors[] memuat `exc.status` + `exc.text`
- `await asyncio.sleep(cfg["delay_per_kick"])` setiap attempt (config sudah
  divalidasi 0.1–10 detik; discord.py menangani retry 429 otomatis)
- bila `execute`, `log.warning` sekali saat `bot_warning(cfg)` menghasilkan teks

Aturan: scope HANYA `member.kick` — tidak ada ban/purge/delete/edit di file ini.
Verifikasi: satu member yang selalu melempar Forbidden tetap menghasilkan
kicked=2, failed=1, errors berisi "Forbidden".
````

### T3.3 — Progres live dan laporan akhir
**Sub-fitur:** F3.3 · **Priority:** medium
**Deskripsi:** Status berjalan tampil real-time, laporan akhir terukur.

````markdown
Di `kickall_core.py` buat:
- `format_progress(stats)` → "Proses n/m", "Kick sukses/gagal", "Sisa n"
- `format_result(stats)` → "EKSEKUSI SELESAI" + total/berhasil/gagal/dilindungi
  + sampel dilindungi + maks 10 baris errors

Di `bot.py`: `on_progress` mengedit pesan status Discord; kegagalan edit
(`discord.HTTPException`, mis. 429) diabaikan — laporan akhir tetap dikirim.
Panggil `on_progress` tiap `cfg["progress_every"]` attempt dan sekali di akhir.

Verifikasi: teks laporan memuat angka yang cocok dengan counter PurgeStats.
````

### T3.4 — Mode sekali jalan (`once`)
**Sub-fitur:** F3.4 · **Priority:** medium
**Deskripsi:** Login → kerja → cetak laporan → proses berakhir bersih.

````markdown
Di `bot.py` implementasikan mode `once <GUILD_ID> [--yes]`:

- bangun dict `{"guild_id", "execute", "done"}` dan serahkan ke `build_bot(cfg, once=...)`
- di `on_ready`: jalankan `_one_shot` HANYA bila `done` belum di-set (tahan reconnect)
- `_one_shot`: `bot.get_guild(id)` → None = pesan "invite bot dulu"; selanjutnya
  `scan(...)` → cetak laporan (format_result bila `--yes`, format_preview + peringatan
  bila tidak) → `await bot.close()` di blok `finally`
- tanpa `--yes` = preview, cetak petunjuk menambah `--yes`

Aturan: tanpa `--yes` tidak ada satu pun kick; exception apa pun tetap menutup koneksi.
Verifikasi: smoke test dengan token palsu menghasilkan "Token ditolak Discord" + exit 3.
````

---

## F4 — Kendali Via CLI & Bot

### T4.1 — Subcommand `check` / `once` / `run`
**Sub-fitur:** F4.1 · **Priority:** high
**Deskripsi:** Jalur terpisah untuk verifikasi, eksekusi tunggal, dan bot jangka panjang.

````markdown
Di `bot.py` (project `discord-kickall`) buat `main(argv)` dengan
`argparse` + `subparsers(required=True)`:

- `check` → `load_config` lalu cetak ringkasan (prefix, whitelist, keep_all_bots,
  allowed_guilds, delay) + `bot_warning` bila ada, exit 0; config invalid → pesan
  `[!] <alasan>` + exit 2
- `once <guild_id:int> [--yes]` → mode sekali jalan (lihat T3.4)
- `run` → bot online dengan perintah teks
- `--help` menampilkan ketiganya

Aturan: `check` tidak pernah membuka koneksi jaringan.
Verifikasi: jalankan `python bot.py --help` dan `python bot.py check`.
````

### T4.2 — Perintah `kickall` + `kickall confirm`
**Sub-fitur:** F4.2 · **Priority:** high
**Deskripsi:** Dua langkah di chat: preview dulu, baru eksekusi.

````markdown
Di dalam `build_bot(cfg, once=None)` pada `bot.py` buat
`@bot.command(name="kickall")` + `@commands.guild_only()` dengan argumen
`*, action: str = "preview"`:

- gate berurutan: `allowed_guilds` → `_authorize` → parsing mode
  (`preview|dry|lihat` = False, `confirm|ya|execute` = True, lainnya = balasan
  pemakaian dengan prefix config)
- kirim pesan status "Mengambil daftar member...", panggil `scan`,
  edit pesan dengan `_with_warning(format_preview/format_result)`
- `on_command_error` mengabaikan `CommandNotFound`

Aturan: `kickall` TIDAK PERNAH meng-kick; hanya `kickall confirm` yang boleh.
Verifikasi: jalankan mode `run` → `!kickall` menampilkan laporan tanpa aksi.
````

### T4.3 — Otorisasi owner-only
**Sub-fitur:** F4.3 · **Priority:** high
**Deskripsi:** Perintah merusak tidak bisa dipanggil anggota biasa.

````markdown
Di `bot.py` buat `async _authorize(bot, ctx) -> bool`:
`ctx.author.id == ctx.guild.owner_id` ATAU `await bot.is_owner(ctx.author)`
(dibungkus `try/except discord.ClientException`).

Panggil SEBELUM `scan`; bila False → balasan penolakan via `ctx.reply(...,
mention_author=False)` dan return (tanpa membaca member, tanpa pesan progres).

Aturan: penolakan tidak membocorkan isi config atau daftar member.
Verifikasi: test manual dengan akun non-owner di server uji.
````

### T4.4 — Penanganan intent & error login
**Sub-fitur:** F4.4 · **Priority:** medium
**Deskripsi:** Kegagalan setup terjawab satu pesan + exit code, bukan traceback.

````markdown
Di `bot.py`:
- `build_intents(need_message_content: bool)` → `members=True` selalu;
  `message_content` hanya untuk mode `run` (sekali jalan tidak meminta intent ini)
- `try/except` di sekitar `bot.run(cfg["token"], log_handler=None)`:
  `discord.LoginFailure` → "Token ditolak Discord" + petunjuk Copy Token, exit 3;
  `discord.PrivilegedIntentsRequired` → daftar intent yang harus diaktifkan per mode,
  exit 4; `discord.HTTPException` → status+text, exit 5
- logging: root INFO → `kickall.log` + stdout; logger `discord` dibatasi WARNING

Aturan: token asli tidak pernah dicetak ke mana pun.
Verifikasi: token palsu → exit 3 + pesan portal; token valid + intent mati → exit 4.
````

---

## Urutan Eksekusi Berfase

| Fase | Task | Keluaran |
|---|---|---|
| 1 — fondasi | T1.1 → T2.1 → T2.2 → T1.2 → T1.3 → T2.3 | `kickall_core.py` + test keputusan |
| 2 — eksekusi | T3.1 → T3.2 → T3.3 | `scan` + formatter, 9/9 test lulus |
| 3 — antarmuka | T3.4 → T4.1 → T4.2 → T4.3 → T4.4 | `bot.py` + smoke test login |
| 4 — operasional | setup pengguna: token, intents, invite, isi `whitelist_bots` | config siap pakai |
| 5 — produksi | `check` → `once <id>` (preview) → `once <id> --yes` | server bersih |

**Definisi selesai:** `test_core.py` 9/9 · `bot.py check` exit 0 · preview menampilkan
angka yang cocok dengan UI Discord · tidak ada member whitelist yang muncul di
"Contoh target kick".
