#!/usr/bin/env python3
"""
GSI Builder Telegram Bot
Bot interaktif untuk trigger dan monitoring build GSI via GitHub Actions
"""

import os
import json
import asyncio
import aiohttp
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ConversationHandler, MessageHandler, ContextTypes, filters
)

# Config
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')  # GitHub Personal Access Token
GITHUB_REPO = os.getenv('GITHUB_REPO', 'username/repo-name')  # Format: owner/repo
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
OWNER_ID = int(os.getenv('OWNER_ID', '0'))  # Telegram ID owner
STATUS_URL = os.getenv('STATUS_URL', 'https://gsi.hanhosting.dpdns.org/api/status')

# Conversation states
(ROM_URL, ROM_BRANCH, BUILD_VARIANT, CONFIRM) = range(4)

# Temporary storage untuk user input
user_data = {}

def is_owner(user_id: int) -> bool:
    """Cek apakah user adalah owner"""
    return user_id == OWNER_ID or OWNER_ID == 0

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /start"""
    user = update.effective_user
    
    keyboard = [
        [InlineKeyboardButton("🚀 Build GSI Baru", callback_data='newgsi')],
        [InlineKeyboardButton("📊 Cek Status", callback_data='status')],
        [InlineKeyboardButton("📖 Panduan", callback_data='guide')],
    ]
    
    welcome_text = f"""
👋 *Selamat datang di GSI Builder Bot!*

Halo {user.first_name}!

Bot ini memungkinkanmu membuild *Generic System Image (GSI)* secara otomatis via GitHub Actions.

*Fitur:*
• Build GSI interaktif
• Monitoring status real-time
• Upload otomatis ke PixelDrain & GoFile

Pilih menu di bawah untuk memulai:
"""
    
    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def newgsi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /newgsi - Mulai proses build baru"""
    user_id = update.effective_user.id
    
    if not is_owner(user_id):
        await update.message.reply_text("❌ Kamu tidak memiliki izin untuk menggunakan fitur ini.")
        return ConversationHandler.END
    
    await update.message.reply_text("""
🚀 *Build GSI Baru*

Langkah 1/4: *ROM Manifest URL*

Masukkan URL manifest ROM yang ingin dibuild.

*Contoh:*
• LineageOS: `https://github.com/LineageOS/android.git`
• Pixel Experience: `https://github.com/PixelExperience/manifest`
• AOSP: `https://android.googlesource.com/platform/manifest`

Ketik /cancel untuk membatalkan.
""", parse_mode='Markdown')
    
    return ROM_URL

async def rom_url_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Terima input ROM URL"""
    user_id = update.effective_user.id
    user_data[user_id] = {'rom_url': update.message.text}
    
    await update.message.reply_text("""
✅ URL diterima!

Langkah 2/4: *Branch ROM*

Masukkan branch yang ingin digunakan.

*Contoh:*
• `lineage-22.1` (LineageOS 15)
• `thirteen` (Pixel Experience 13)
• `android-14.0.0_r21` (AOSP)

*Tips:* Cek branch di repository manifest ROM yang dipilih.
""", parse_mode='Markdown')
    
    return ROM_BRANCH

async def rom_branch_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Terima input ROM Branch"""
    user_id = update.effective_user.id
    user_data[user_id]['rom_branch'] = update.message.text
    
    keyboard = [
        [InlineKeyboardButton("treble_arm64_bvN", callback_data='treble_arm64_bvN-userdebug')],
        [InlineKeyboardButton("treble_arm64_bgN", callback_data='treble_arm64_bgN-userdebug')],
        [InlineKeyboardButton("treble_a64_bvN", callback_data='treble_a64_bvN-userdebug')],
        [InlineKeyboardButton("treble_a64_bgN", callback_data='treble_a64_bgN-userdebug')],
    ]
    
    await update.message.reply_text("""
✅ Branch diterima!

Langkah 3/4: *Build Variant*

Pilih variant GSI yang ingin dibuild:

*Penjelasan:*
• `arm64` = 64-bit devices
• `a64` = 32-bit devices (older)
• `bvN` = Vanilla (no GApps), VNDK-lite
• `bgN` = With GApps, VNDK-lite

Pilih dari tombol di bawah:
""", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    return BUILD_VARIANT

async def build_variant_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Terima pilihan build variant"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_data[user_id]['build_variant'] = query.data
    
    data = user_data[user_id]
    
    summary = f"""
📋 *Konfirmasi Build*

*ROM URL:* `{data['rom_url']}`
*Branch:* `{data['rom_branch']}`
*Variant:* `{data['build_variant']}`

⚠️ *Perhatian:*
• Build membutuhkan waktu 1-3 jam
• GitHub Actions akan berjalan
• Kamu akan menerima notifikasi saat selesai

Build sekarang?
"""
    
    keyboard = [
        [InlineKeyboardButton("✅ Ya, Build!", callback_data='confirm_build')],
        [InlineKeyboardButton("❌ Batal", callback_data='cancel_build')],
    ]
    
    await query.edit_message_text(summary, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    return CONFIRM

async def confirm_build(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Konfirmasi dan trigger workflow"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = user_data[user_id]
    
    await query.edit_message_text("🔄 *Memulai build...*", parse_mode='Markdown')
    
    # Trigger GitHub Actions workflow
    success = await trigger_github_workflow(
        data['rom_url'],
        data['rom_branch'],
        data['build_variant'],
        str(update.effective_chat.id)
    )
    
    if success:
        await query.edit_message_text("""
✅ *Build berhasil dimulai!*

Build sedang berjalan di GitHub Actions.

*Monitoring:*
• Status: [Klik di sini](https://gsi.hanhosting.dpdns.org/api/status)
• GitHub: Cek Actions tab di repository

Gunakan /status untuk cek status terkini.
""", parse_mode='Markdown', disable_web_page_preview=True)
    else:
        await query.edit_message_text("""
❌ *Gagal memulai build!*

Pastikan:
• GITHUB_TOKEN sudah diatur
• Repository sudah benar
• Workflow file sudah ada

Coba lagi nanti atau cek logs.
""", parse_mode='Markdown')
    
    return ConversationHandler.END

async def cancel_build(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Batalkan build"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text("❌ Build dibatalkan.")
    
    user_id = update.effective_user.id
    if user_id in user_data:
        del user_data[user_id]
    
    return ConversationHandler.END

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /cancel"""
    user_id = update.effective_user.id
    if user_id in user_data:
        del user_data[user_id]
    
    await update.message.reply_text("❌ Dibatalkan.")
    return ConversationHandler.END

async def trigger_github_workflow(rom_url: str, rom_branch: str, build_variant: str, chat_id: str) -> bool:
    """Trigger GitHub Actions workflow"""
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/gsi-builder.yml/dispatches"
        
        headers = {
            'Authorization': f'token {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        payload = {
            'ref': 'main',
            'inputs': {
                'rom_url': rom_url,
                'rom_branch': rom_branch,
                'build_variant': build_variant,
                'telegram_chat_id': chat_id,
                'telegram_bot_token': TELEGRAM_BOT_TOKEN
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                return response.status == 204
                
    except Exception as e:
        print(f"Error triggering workflow: {e}")
        return False

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /status - Cek status build"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(STATUS_URL, timeout=10) as response:
                data = await response.json()
        
        status_emoji = {
            'idle': '⏸️',
            'initializing': '🔄',
            'syncing': '📥',
            'patching': '🩹',
            'configuring': '⚙️',
            'building': '🔨',
            'uploading': '📤',
            'success': '✅',
            'failed': '❌',
            'error': '⚠️'
        }
        
        emoji = status_emoji.get(data.get('status', 'idle'), '⏸️')
        progress = data.get('progress', 0)
        message = data.get('message', 'Tidak ada informasi')
        
        # Progress bar
        filled = int(progress / 10)
        bar = '█' * filled + '░' * (10 - filled)
        
        status_text = f"""
{emoji} *Status Build GSI*

`[{bar}]` {progress}%

📋 *Step:* {data.get('step', 'N/A')}
💬 *Message:* {message}
"""
        
        # Jika build selesai, tampilkan download links
        if data.get('status') == 'success' and 'downloads' in data:
            downloads = data['downloads']
            status_text += f"""
📥 *Download Links:*
• PixelDrain: {downloads.get('pixeldrain', 'N/A')}
• GoFile: {downloads.get('gofile', 'N/A')}
📁 File: `{downloads.get('filename', 'N/A')}`
"""
        
        # Jika gagal, tampilkan error
        if data.get('status') == 'failed':
            status_text += f"""
⚠️ *Error:* {data.get('error', 'Unknown error')}
"""
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data='refresh_status')],
            [InlineKeyboardButton("🌐 Buka Status Page", url='https://gsi.hanhosting.dpdns.org/')],
        ]
        
        await update.message.reply_text(
            status_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=True
        )
        
    except Exception as e:
        await update.message.reply_text(f"""
⚠️ *Gagal mengambil status*

Error: `{str(e)}`

Pastikan:
• Status server berjalan
• URL status benar

Status URL: {STATUS_URL}
""", parse_mode='Markdown')

async def refresh_status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Refresh status callback"""
    query = update.callback_query
    await query.answer("Refreshing...")
    
    # Delete old message and send new status
    await query.delete_message()
    await status_command(update, context)

async def guide_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /guide - Tampilkan panduan"""
    guide_text = """
📖 *Panduan Build GSI*

*Apa itu GSI?*
Generic System Image adalah system image Android yang bisa diinstall di berbagai device yang support Project Treble.

*Persyaratan Device:*
• Android 8.1+ (Treble enabled)
• Unlock bootloader
• Custom recovery (TWRT/dll)

*Cara Build:*
1. Ketik /newgsi
2. Masukkan URL manifest ROM
3. Pilih branch
4. Pilih variant
5. Konfirmasi build

*Variant GSI:*
• `arm64_bvN` - 64-bit, Vanilla (no GApps)
• `arm64_bgN` - 64-bit, dengan GApps
• `a64_bvN` - 32-bit, Vanilla
• `a64_bgN` - 32-bit, dengan GApps

*Tips:*
• Build membutuhkan waktu 1-3 jam
• Hasil akan diupload ke PixelDrain & GoFile
• Gunakan /status untuk monitoring

*ROM yang Support:*
• LineageOS
• Pixel Experience
• crDroid
• AOSP
• Dan lainnya...
"""
    
    keyboard = [
        [InlineKeyboardButton("🚀 Mulai Build", callback_data='newgsi')],
        [InlineKeyboardButton("📊 Cek Status", callback_data='status')],
    ]
    
    await update.message.reply_text(
        guide_text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle tombol inline"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'newgsi':
        await newgsi_command(update, context)
    elif query.data == 'status':
        await status_command(update, context)
    elif query.data == 'guide':
        await guide_command(update, context)
    elif query.data == 'refresh_status':
        await refresh_status_callback(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /help"""
    help_text = """
🤖 *GSI Builder Bot - Bantuan*

*Perintah Tersedia:*

/start - Mulai bot
/newgsi - Build GSI baru
/status - Cek status build
/guide - Panduan lengkap
/help - Tampilkan bantuan ini
/cancel - Batalkan operasi

*Cara Penggunaan:*
1. Pastikan kamu adalah owner (OWNER_ID)
2. Ketik /newgsi untuk mulai
3. Ikuti instruksi step by step
4. Tunggu notifikasi selesai

*Butuh Bantuan?*
Hubungi admin atau cek /guide
"""
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

def main():
    """Main function"""
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN tidak diatur!")
        return
    
    if not GITHUB_TOKEN:
        print("Warning: GITHUB_TOKEN tidak diatur, trigger workflow tidak akan berfungsi!")
    
    print("=" * 50)
    print("🤖 GSI Builder Telegram Bot")
    print("=" * 50)
    print(f"GitHub Repo: {GITHUB_REPO}")
    print(f"Status URL: {STATUS_URL}")
    print(f"Owner ID: {OWNER_ID}")
    print("=" * 50)
    
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Conversation handler untuk /newgsi
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('newgsi', newgsi_command)],
        states={
            ROM_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, rom_url_input)],
            ROM_BRANCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, rom_branch_input)],
            BUILD_VARIANT: [CallbackQueryHandler(build_variant_callback, pattern='^treble_')],
            CONFIRM: [
                CallbackQueryHandler(confirm_build, pattern='^confirm_build$'),
                CallbackQueryHandler(cancel_build, pattern='^cancel_build$')
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel_command)],
    )
    
    # Register handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('status', status_command))
    application.add_handler(CommandHandler('guide', guide_command))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_handler))
    
    print("✅ Bot siap!")
    print("Tekan Ctrl+C untuk berhenti")
    
    # Run bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
