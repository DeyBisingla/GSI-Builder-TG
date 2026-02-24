# Automatic GSI Builder

Build Generic System Image (GSI) Android secara otomatis via GitHub Actions dengan kontrol Telegram Bot.

## Cara Kerja

```
┌─────────────┐     Trigger      ┌──────────────────┐
│ Telegram    │ ───────────────> │ GitHub Actions   │
│ Bot (VPS)   │                  │ Runner           │
└─────────────┘                  └────────┬─────────┘
       ^                                  │
       │                                  │
       │    Status JSON                   │ Build GSI
       │    (Real-time)                   │
       │                                  ▼
       └───────────────────────  ┌──────────────────┐
                                  │ Cloudflare One   │
                                  │ Tunnel           │
                                  └────────┬─────────┘
                                           │
                                           ▼
                                  ┌──────────────────┐
                                  │ gsi.hanhosting   │
                                  │ .dpdns.org       │
                                  └──────────────────┘
```

## Setup

### 1. GitHub Repository

Fork repo ini, lalu tambahkan **Secrets** di Settings > Secrets and variables > Actions:

| Secret | Keterangan |
|--------|-----------|
| `CLOUDFLARE_KEY` | Cloudflare Tunnel Token (wajib untuk status API) |
| `PIXELDRAIN_API_KEY` | API Key PixelDrain (optional) |
| `GOFILE_API_KEY` | API Key GoFile (optional) |

**Cara mendapatkan CLOUDFLARE_KEY:**
1. Login ke [Cloudflare One](https://one.dash.cloudflare.com/)
2. Buat tunnel baru atau gunakan tunnel existing
3. Copy **Tunnel Token** (bukan tunnel ID)
4. Paste ke GitHub Secrets sebagai `CLOUDFLARE_KEY`

### 2. Bot Telegram (VPS)

Install dependencies:
```bash
pip install -r requirements.txt
```

Set environment variables:
```bash
export TELEGRAM_BOT_TOKEN="your_bot_token"
export GITHUB_TOKEN="your_github_token"
export GITHUB_REPO="username/repo-name"
export OWNER_ID="your_telegram_id"
export STATUS_URL="https://gsi.hanhosting.dpdns.org/api/status"
```

Jalankan bot:
```bash
python3 bot_telegram.py
```

## Penggunaan

1. Chat bot Telegram, kirim `/newgsi`
2. Ikuti instruksi (URL ROM → Branch → Variant)
3. Konfirmasi build
4. Workflow GitHub Actions akan berjalan
5. Status real-time tersedia di `https://gsi.hanhosting.dpdns.org/api/status`
6. Tunggu notifikasi selesai (1-3 jam)
7. Download link akan dikirim ke Telegram

## Command Bot

| Command | Fungsi |
|---------|--------|
| `/start` | Mulai bot |
| `/newgsi` | Build GSI baru |
| `/status` | Cek status build real-time |
| `/guide` | Panduan lengkap |
| `/help` | Bantuan |
| `/cancel` | Batalkan operasi |

## Status API

Endpoint: `https://gsi.hanhosting.dpdns.org/api/status`

Response JSON:
```json
{
  "status": "building",
  "step": "compile",
  "progress": 70,
  "message": "Building system image...",
  "timestamp": 1700000000
}
```

Status yang mungkin:
- `idle` - Menunggu trigger
- `initializing` - Setup environment
- `syncing` - Sync ROM source
- `patching` - Apply Treble patches
- `configuring` - Generate device config
- `building` - Compile system image
- `uploading` - Upload hasil build
- `success` - Build berhasil
- `failed` - Build gagal

## Catatan

- Build membutuhkan waktu **1-3 jam**
- Hasil diupload ke **PixelDrain** & **GoFile**
- Support ROM: LineageOS, Pixel Experience, crDroid, AOSP, dll
- Status API berjalan via **Cloudflare One Tunnel** dari runner
