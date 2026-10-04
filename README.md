# KickAll — Clean & Safe Discord Server Member Cleanup Tool

> **Languages**: **English** (Top) | **Bahasa Indonesia** (Bawah / Bottom half)

A professional, high-reliability Discord bot designed to wipe/kick **all regular members from a server you own**, while enforcing a strict zero-touch whitelist: your existing bots, server owner, designated admin/VIP accounts, and special roles. Built with a mandatory **two-stage workflow (dry-run preview first -> explicit confirmation to execute)**.

---

# [ ENGLISH SECTION ]

## 1. Core Principles & Safety Guarantees

| What KickAll Does | What KickAll NEVER Does |
|---|---|
| Kicks members strictly via the **official Discord Bot REST API** | Never uses user tokens or selfbots (violates Discord ToS, zero ban risk) |
| Hard-protects server owner, executor bot, and whitelisted bots/users | Never deletes channels, emojis, roles, chat history, or bans anyone |
| Strictly respects Discord role hierarchy (skips targets >= bot role) | Never operates on any server outside `allowed_guilds` |
| Built-in pacing (`delay_per_kick`) + auto rate-limit backoff | Never transmits bot tokens anywhere outside `discord.com` |
| Requires dry-run preview before execution | Never triggers automatically on boot or without explicit confirmation |

Every kick action is logged directly into your server's **Audit Log** with a customizable audit reason, and saved locally to `kickall.log`.

---

## 2. Prerequisites

1. **Python 3.10+** installed on your system (Python 3.14+ fully supported).
2. A Discord Bot Application created under your Discord Developer account.
3. The bot invited to your target server with at least the **Kick Members** permission.
4. The bot's role placed **HIGHER** than the roles of members you intend to kick.
5. Privileged Gateway Intents enabled in Developer Portal:
   - **SERVER MEMBERS INTENT** (Mandatory for member enumeration via REST/Gateway).
   - **MESSAGE CONTENT INTENT** (Mandatory if using chat command mode `!kickall`).

---

## 3. Installation & Virtual Environment

Open a terminal (Command Prompt, PowerShell, or Git Bash) inside the project folder:

```bat
cd discord-kickall

:: Create isolated virtual environment
python -m venv .venv

:: Install dependencies
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

*Linux / macOS equivalent:*
```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

*Pinned dependency:* `discord.py==2.7.1` (no bloated external packages).

---

## 4. End-to-End Setup Tutorial

### Step 4.1: Create Bot Application & Retrieve Token
1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Click **New Application** (top right) -> Enter a name (e.g. `autokick member`) -> Click **Create**.
3. In the left sidebar, click **Bot**.
4. Click **Reset Token** -> Enter 2FA / Password -> Click **Copy**.
5. Keep this token ready for `config.json` (treat it like a password; never share it).

### Step 4.2: Enable Privileged Gateway Intents
1. On the same **Bot** page, scroll down to the **Privileged Gateway Intents** section.
2. Toggle **ON**:
   - `SERVER MEMBERS INTENT` (Required to fetch guild members).
   - `MESSAGE CONTENT INTENT` (Required if using text commands like `!kickall`).
3. Click **Save Changes** at the bottom.

### Step 4.3: Generate OAuth2 Invite Link
1. In the left sidebar, click **OAuth2** -> **URL Generator**.
2. Under **Scopes**, select only `bot`.
3. Under **Bot Permissions**, select `Kick Members` (Permission integer `2`).
   *(Note: Do NOT select Administrator; `Kick Members` is sufficient and follows least-privilege security).*
4. Copy the generated URL at the bottom -> Open in browser -> Select your server -> Click **Authorize**.

### Step 4.4: Enable Developer Mode & Collect Snowflake IDs
To protect specific bots or users, you need their numeric Discord Snowflake IDs (17–19 digits):
1. In Discord Desktop / Web, open **User Settings** (gear icon near your avatar).
2. In the left menu, select **Advanced** -> Turn **ON Developer Mode**.
3. Exit settings.
4. **Copy Bot IDs**:
   - Right-click any bot in the member list or chat -> Click **Copy User ID**.
   *(If the bot is yours, you can also copy **Application ID** directly from General Information in Developer Portal).*
5. **Copy Server ID**:
   - Right-click your server's icon/name on the left server bar -> Click **Copy Server ID**.
6. **Copy User ID (Yourself / Staff)**:
   - Right-click your own profile or staff account -> Click **Copy User ID**.

### Step 4.5: Discord Role Hierarchy Setup (CRITICAL)
Discord strictly prevents any bot from kicking members who have a role **equal to or higher** than the bot's highest role.
If members are not being kicked or show as protected by hierarchy:
1. Open **Server Settings** -> **Roles**.
2. Find your bot's role (e.g. `autokick member`).
3. Drag the role **UP** so it sits above the roles of the members you want kicked (e.g. above `BUYERS`, `Member`, etc.).
4. Keep the bot's role **BELOW** the bots or server admins you want to protect.

*Working Hierarchy Example:*
```text
[Position 9] ServerStats (Bot)      <- Protected
[Position 8] OWNER (Admin Role)     <- Protected
[Position 7] Ticket Tool (Bot)      <- Protected
[Position 6] Dyno (Bot)             <- Protected
[Position 5] RootFS BOT (Bot)       <- Protected
[Position 4] autokick member (Bot)  <== Kicking Bot Role
--------------------------------------------------------- (Line of authority)
[Position 3] BUYERS                 <== Target Member Role (Kicked!)
[Position 2] BABU ROOTFS            <== Target Member Role (Kicked!)
[Position 0] @everyone              <== Target Regular Members (Kicked!)
```

---

## 5. Configuration Reference (`config.json`)

Edit `config.json` in the root folder:

```json
{
  "token": "YOUR_DISCORD_BOT_TOKEN_HERE",
  "whitelist_bots": [
    123456789012345678
  ],
  "keep_all_bots": false,
  "whitelist_users": [],
  "whitelist_roles": [],
  "allowed_guilds": [
    987654321098765432
  ],
  "delay_per_kick": 0.5,
  "progress_every": 10,
  "reason": "KickAll: cleanup server",
  "command_prefix": "!"
}
```

### Parameter Explanations:
- `token` (string, required): The Discord bot authentication token.
- `whitelist_bots` (list of integers): Discord IDs of bots that must **NEVER** be kicked.
- `keep_all_bots` (boolean): When set to `true`, **ALL** bots are automatically exempted from kicking without needing IDs.
- `whitelist_users` (list of integers): User IDs of humans (owner, alt accounts, staff) who must **NEVER** be kicked.
- `whitelist_roles` (list of integers): Role IDs. Any member who has at least one of these roles will be skipped.
- `allowed_guilds` (list of integers): Target Server IDs. If populated, KickAll will strictly refuse to run on any other server.
- `delay_per_kick` (float, 0.1 – 10.0): Pause duration in seconds between kick calls to prevent API bursts and stay comfortably within Discord rate limits (0.5s recommended).
- `progress_every` (integer): How often progress is logged or live-updated in chat.
- `reason` (string): Text string that will permanently appear in the Discord Server Audit Log for each kicked member.
- `command_prefix` (string): Trigger prefix for Discord chat commands.

---

## 6. How to Run

### Workflow 1: Recommended Single-Pass CLI (Fastest & Safest)

1. **Validate Configuration (Offline, no login)**:
   ```bat
   .venv\Scripts\python.exe bot.py check
   ```
   *Verifies JSON structure, validates tokens, checks whitelist IDs, and warns if bot protection is missing.*

2. **Run Preview Mode (Dry-Run, ZERO kicks)**:
   ```bat
   .venv\Scripts\python.exe bot.py once YOUR_SERVER_ID
   ```
   *Fetches all guild members via Discord REST API, evaluates each against the whitelist and role hierarchy, and outputs a complete breakdown with sample names.*

3. **Confirm & Execute Kicks**:
   ```bat
   .venv\Scripts\python.exe bot.py once YOUR_SERVER_ID --yes
   ```
   *Kicks designated targets sequentially with the configured delay, streams progress, prints the final tally, and cleanly closes the session.*

### Workflow 2: Double-Click Batch Helpers (Windows)

- `start.bat`: Checks configuration and launches the bot in persistent chat-command mode.
- `once.bat <SERVER_ID>`: Runs dry-run preview mode.
- `once.bat <SERVER_ID> --yes`: Runs live execution mode.

### Workflow 3: Chat Command Mode

```bat
.venv\Scripts\python.exe bot.py run
```
Once the console logs `online as bot_name#1234`:
- In any channel where the bot has access, type:
  `!kickall` -> Prints preview stats (Total, Planned, Protected, Samples).
- To confirm and begin kicking:
  `!kickall confirm` -> Live message edits progress, then updates to final completion report.
*(Security: Only the Guild Owner and the Bot Application Owner can invoke this command. Non-owners are immediately rejected).*

---

## 7. Verification & Audit Trail

1. **Discord Native Audit Log**:
   Go to **Server Settings** -> **Audit Log** -> Filter by **Kick Members**. You will see each kick recorded with your configured reason.
2. **Local Log File**:
   Check `kickall.log` in the project root for timestamps, skipped member reasons, and network diagnostics.
3. **Unit Tests (Offline)**:
   ```bat
   .venv\Scripts\python.exe test_core.py
   ```
   *Runs 9 unit test suites testing config errors, role hierarchy, whitelist rules, dry-run safety, and exception handling without opening any network sockets.*

---

## 8. Troubleshooting Matrix

| Issue / Error Output | Root Cause | Solution |
|---|---|---|
| `Token ditolak Discord: Improper token has been passed (exit 3)` | Token was reset, expired, or copied with missing characters | Go to Developer Portal -> Bot -> Reset Token -> Copy once and paste into `config.json`. |
| `Privileged Gateway Intent belum diaktifkan (exit 4)` | Members or Message intent not enabled in portal | Go to Developer Portal -> Bot -> Privileged Gateway Intents -> Toggle both ON. |
| Target members marked as `hierarchy: role target >= role bot` | Bot's role is below or equal to the target's role | Open Server Settings -> Roles -> Drag bot role above the target role (e.g. above `BUYERS`). |
| Target shows 0 kicks planned when server is full | Server ID incorrect or all members have whitelisted roles | Verify `allowed_guilds` and review reasons listed in preview under "Contoh yang dilindungi". |
| `bot tidak punya izin Kick Members` | Bot invite link was generated without Kick permission | Re-invite the bot using an OAuth2 URL with `Kick Members` permission checked. |
| Owner account appears in preview as protected | By design (Discord hard limit) | Server owners cannot be kicked by any bot under any circumstance. |

---
---

# [ BAGIAN BAHASA INDONESIA ]

## 1. Prinsip Utama & Jaminan Keamanan

| Yang Dilakukan KickAll | Yang TIDAK PERNAH Dilakukan |
|---|---|
| Kick member murni melalui **Discord Bot REST API resmi** | Tidak memakai token user / selfbot (bebas risiko ban Discord) |
| Melindungi pemilik server, bot tools, dan akun/role whitelist | Tidak menghapus channel, role, pesan, atau ban permanen siapapun |
| Menghormati hierarki role (otomatis skip target >= role bot) | Tidak menyentuh server manapun di luar `allowed_guilds` |
| Jeda per kick (`delay_per_kick`) + auto backoff rate limit | Tidak mengirim token ke manapun selain API resmi Discord |
| Wajib preview (dry-run) sebelum eksekusi dimulai | Tidak ada eksekusi otomatis tanpa perintah eksplisit `--yes` / `confirm` |

Setiap tindakan kick tercatat permanen di **Audit Log** server Discord Anda dengan alasan yang bisa diatur, serta tersimpan detail di log lokal `kickall.log`.

---

## 2. Persyaratan Sistem

1. **Python 3.10 ke atas** (Python 3.14+ sudah terpasang dan teruji).
2. Akun Bot Discord yang dibuat di Discord Developer Portal.
3. Bot sudah di-invite ke server target dengan izin minimal **Kick Members**.
4. Role bot sudah digeser ke **ATAS** role member yang ingin di-kick.
5. Privileged Gateway Intents aktif di Developer Portal:
   - **SERVER MEMBERS INTENT** (Wajib untuk semua mode agar bisa baca daftar member).
   - **MESSAGE CONTENT INTENT** (Wajib jika ingin menggunakan perintah chat `!kickall`).

---

## 3. Instalasi & Virtual Environment

Buka terminal (Command Prompt, PowerShell, atau Git Bash) di folder project:

```bat
cd discord-kickall

:: Buat virtual environment terisolasi
python -m venv .venv

:: Install dependencies resmi
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

*Di Git Bash / Linux:*
```bash
./.venv/Scripts/python.exe -m pip install -r requirements.txt
```

*Satu-satunya library:* `discord.py==2.7.1` (ringan, stabil, async).

---

## 4. Panduan Setup Lengkap dari Nol (Step-by-Step)

### Langkah 4.1: Buat Aplikasi Bot & Ambil Token
1. Buka browser dan login ke [Discord Developer Portal](https://discord.com/developers/applications).
2. Klik tombol **New Application** di pojok kanan atas.
3. Masukkan nama aplikasi (misalnya: `autokick member`), lalu klik **Create**.
4. Di panel menu kiri, klik tab **Bot**.
5. Klik tombol **Reset Token** -> Konfirmasi / masukkan password atau kode 2FA jika diminta.
6. Klik tombol **Copy** untuk menyalin token bot.
7. Simpan token ini untuk dimasukkan ke `config.json` pada field `"token"`.
   *(PENTING: Jangan bagikan token ini kepada siapapun; token ini berfungsi seperti password).*

### Langkah 4.2: Aktifkan Privileged Gateway Intents
1. Masih di halaman tab **Bot** yang sama, gulir ke bawah ke bagian **Privileged Gateway Intents**.
2. Centang / geser toggle menjadi **ON** untuk:
   - `SERVER MEMBERS INTENT` (Wajib untuk membaca seluruh anggota server).
   - `MESSAGE CONTENT INTENT` (Wajib jika menggunakan perintah bot via chat).
3. Klik tombol hijau **Save Changes** di bagian bawah.

### Langkah 4.3: Generate Link Invite Bot ke Server
1. Di panel menu kiri, klik tab **OAuth2** -> lalu pilih sub-menu **URL Generator**.
2. Pada bagian **Scopes**, centang hanya `bot`.
3. Pada bagian **Bot Permissions** yang muncul di bawahnya, centang hanya `Kick Members` (Nilai integer: `2`).
   *(Catatan: Jangan mencentang Administrator jika tidak diperlukan; izin Kick Members sudah cukup).*
4. Di bagian paling bawah, salin URL yang muncul di kotak **Generated URL**.
5. Buka URL tersebut di browser, pilih server Discord Anda, lalu klik **Authorize**.

### Langkah 4.4: Aktifkan Developer Mode & Ambil ID
Untuk melindungi bot tools Anda atau user tertentu, Anda membutuhkan ID numerik (17–19 digit angka):
1. Buka aplikasi Discord (Desktop atau Web).
2. Buka **User Settings** (ikon gerigi ⚙ di samping avatar Anda).
3. Di menu kiri, pilih tab **Advanced** -> Nyalakan toggle **Developer Mode** menjadi **ON**.
4. Tutup halaman pengaturan.
5. **Ambil ID Bot Tools**:
   - Klik kanan pada bot tools Anda di daftar member atau chat -> Klik **Copy User ID**.
   *(Jika bot tersebut adalah bot buatan Anda sendiri, ID ini sama dengan Application ID di menu General Information portal).*
6. **Ambil ID Server**:
   - Klik kanan pada ikon/nama server Anda di sidebar kiri -> Klik **Copy Server ID**.
7. **Ambil ID User (Anda / Staff)**:
   - Klik kanan pada akun Anda atau admin lain -> Klik **Copy User ID**.

### Langkah 4.5: Susun Hierarki Role di Discord (SANGAT KRUSIAL)
Discord memiliki aturan keamanan mutlak: **Bot TIDAK BISA meng-kick siapapun yang posisi role tertingginya sama atau lebih tinggi dari posisi role tertinggi bot tersebut.**
Jika member memiliki role tertentu (contoh: `BUYERS`), role bot Anda harus berada di atas role tersebut!

Cara mengatur hierarki:
1. Buka server Discord Anda -> Klik panah di samping nama server -> **Server Settings**.
2. Klik tab **Roles**.
3. Cari role bot Anda (misalnya role `autokick member`).
4. **Tarik role bot tersebut ke ATAS role member yang ingin di-kick** (misalnya taruh di atas role `BUYERS`).
5. Pastikan role bot tetap berada di **BAWAH** role bot lain yang ingin dilindungi (misalnya di bawah `RootFS BOT`, `Dyno`, `ServerStats`).
6. Klik **Save Changes**.

*Contoh Urutan Hierarki yang Benar:*
```text
[Posisi 9] ServerStats (Bot)      <- Aman terlindungi
[Posisi 8] OWNER (Role Admin)     <- Aman terlindungi
[Posisi 7] Ticket Tool (Bot)      <- Aman terlindungi
[Posisi 6] Dyno (Bot)             <- Aman terlindungi
[Posisi 5] RootFS BOT (Bot)       <- Aman terlindungi
[Posisi 4] autokick member (Bot)  <== Posisi Role Bot Eksekutor
----------------------------------------------------------------- (Batas Kuasa Bot)
[Posisi 3] BUYERS                 <== Role Member Target (Bisa di-kick!)
[Posisi 2] BABU ROOTFS            <== Role Member Target (Bisa di-kick!)
[Posisi 0] @everyone              <== Member Biasa Tanpa Role (Bisa di-kick!)
```

---

## 5. Penjelasan Parameter File `config.json`

File konfigurasi berada di folder utama `config.json`:

```json
{
  "token": "TOKEN_BOT_DISINI",
  "whitelist_bots": [
    123456789012345678
  ],
  "keep_all_bots": false,
  "whitelist_users": [],
  "whitelist_roles": [],
  "allowed_guilds": [
    987654321098765432
  ],
  "delay_per_kick": 0.5,
  "progress_every": 10,
  "reason": "KickAll: cleanup server",
  "command_prefix": "!"
}
```

### Arti Setiap Kolom:
- `token` (teks): Token rahasia bot Discord dari Developer Portal.
- `whitelist_bots` (daftar angka): Kumpulan ID bot yang **HARAM** di-kick (bot tools Anda, Dyno, ServerStats, Ticket Tool, dll).
- `keep_all_bots` (boolean): Jika diset `true`, **SEMUA** bot apapun jenisnya otomatis dilewati tanpa perlu mencatat ID satu per satu.
- `whitelist_users` (daftar angka): Kumpulan ID user manusia yang aman dari kick (akun utama Anda, akun alt, staff/admin).
- `whitelist_roles` (daftar angka): Kumpulan ID role. Member yang memegang salah satu role ini akan otomatis dilewati.
- `allowed_guilds` (daftar angka): ID Server target. Jika diisi, bot akan menolak beroperasi di server lain manapun.
- `delay_per_kick` (desimal, 0.1 – 10.0 detik): Waktu jeda istirahat antar setiap kick agar tidak memicu rate-limit Discord (direkomendasikan `0.5` detik).
- `progress_every` (angka): Tiap berapa kali kick progres diperbarui di layar atau pesan chat.
- `reason` (teks): Catatan alasan yang akan tertera resmi di Audit Log Discord untuk setiap member yang dikeluarkan.
- `command_prefix` (teks): Awalan simbol untuk memanggil perintah di chat Discord (default `!`).

---

## 6. Cara Menjalankan

### Cara 1: Mode Terminal Sekali Jalan (Sangat Disarankan, Paling Cepat)

1. **Uji Validasi Config (Tanpa Login / Tanpa Jaringan)**:
   ```bat
   .venv\Scripts\python.exe bot.py check
   ```
   *Memeriksa apakah JSON valid, format ID benar, dan memberikan peringatan jika proteksi bot belum diatur.*

2. **Jalankan Mode PREVIEW (Dry-Run, Nol Kick)**:
   ```bat
   .venv\Scripts\python.exe bot.py once ID_SERVER_ANDA
   ```
   *Bot akan membaca seluruh member via REST API resmi, membandingkannya dengan whitelist dan hierarki role, lalu menampilkan laporan lengkap siapa saja yang akan di-kick dan siapa yang dilindungi. Tidak ada satupun yang dikeluarkan pada tahap ini.*

3. **Eksekusi Pembersihan**:
   ```bat
   .venv\Scripts\python.exe bot.py once ID_SERVER_ANDA --yes
   ```
   *Bot akan mulai meng-kick target satu per satu sesuai delay, menampilkan progres berjalan, mencetak laporan akhir (Berhasil/Gagal/Dilindungi), lalu proses menutup sendiri secara bersih.*

### Cara 2: Pakai File Shortcut Bawaan Windows (.bat)

- `start.bat`: Cek config otomatis lalu langsung menyalakan bot dalam mode online untuk chat.
- `once.bat <ID_SERVER>`: Melakukan preview dry-run untuk server tersebut.
- `once.bat <ID_SERVER> --yes`: Melakukan eksekusi pembersihan langsung.

### Cara 3: Mode Chat Discord Langsung

```bat
.venv\Scripts\python.exe bot.py run
```
Biarkan jendela terminal tetap menyala (status bot di server akan menjadi **Online**):
- Di channel server Anda, ketik:
  `!kickall` -> Bot akan membalas dengan laporan preview (Total member, Target kick, Dilindungi).
- Jika angka sudah sesuai dan ingin mengeksekusi, ketik:
  `!kickall confirm` -> Pesan bot akan diedit secara langsung menampilkan progres live (`Proses n/m, sukses, gagal`), lalu ditutup dengan rekapitulasi akhir.
*(Keamanan: Hanya Pemilik Server asli atau Pemilik Aplikasi Bot yang diizinkan menjalankan perintah ini).*

---

## 7. Bukti & Verifikasi Hasil

Setelah eksekusi selesai, Anda dapat membuktikannya melalui 3 jalur independen:
1. **Discord Server Audit Log**:
   Buka **Server Settings** -> **Audit Log** -> Pilih Filter **Kick Members**. Anda akan melihat riwayat setiap member yang dikeluarkan lengkap dengan alasan dari config Anda.
2. **File Log Lokal**:
   Buka file `kickall.log` di folder project untuk melihat riwayat waktu, siapa yang dilewati beserta alasannya, dan catatan jaringan.
3. **Unit Test Mandiri**:
   ```bat
   .venv\Scripts\python.exe test_core.py
   ```
   *Menjalankan 9 unit test komprehensif menguji aturan whitelist, perlindungan owner, hierarki role, dan isolasi preview tanpa perlu koneksi internet.*

---

## 8. Tabel Diagnostik & Solusi Masalah

| Pesan Kendala di Terminal | Penyebab Utama | Solusi Pasti |
|---|---|---|
| `Token ditolak Discord: Improper token has been passed (exit 3)` | Token salah salin, terpotong, atau sudah ter-reset di portal | Masuk Developer Portal -> Tab Bot -> Reset Token -> Copy satu kali -> Tempel di `config.json`. |
| `Privileged Gateway Intent belum diaktifkan (exit 4)` | Intent Server Members atau Message Content belum dicentang | Buka Developer Portal -> Tab Bot -> Privileged Gateway Intents -> Nyalakan kedua toggle -> Save. |
| Member target masuk daftar `hierarchy: role target >= role bot` | Role bot berada di posisi lebih rendah daripada role target | Masuk Server Settings -> Roles -> Geser role bot ke atas role target (contoh: di atas `BUYERS`). |
| Target kick 0 padahal ada banyak member | ID server salah atau semua member memegang role whitelist | Cek kembali `allowed_guilds` dan baca daftar alasan di preview bagian "Contoh yang dilindungi". |
| `bot tidak punya izin Kick Members` | Saat membuat invite link, izin Kick Members tidak dicentang | Invite ulang bot menggunakan URL generator yang sudah dicentang izin `Kick Members`. |
| Akun pemilik server tetap aman / tidak bisa di-kick | Aturan mutlak sistem Discord | Pemilik server tidak bisa di-kick oleh bot manapun di dunia. Ini adalah aturan keamanan bawaan Discord. |

---

## 9. Catatan Penting Mengenai Kick vs Ban

1. **Kick berbeda dengan Ban**: Member yang di-kick **masih dapat bergabung kembali** jika mereka memiliki link invite server yang masih aktif. Jika Anda ingin server tetap kosong permanen, buka **Server Settings** -> **Invites** -> lalu **Revoke** semua link invite yang lama.
2. **Perlindungan Bot**: Selalu pastikan ID bot tools Anda tercatat di `whitelist_bots` atau ubah `"keep_all_bots": true` di `config.json` agar bot kesayangan Anda tidak pernah ikut terhapus.
