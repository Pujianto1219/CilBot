require('dotenv').config();
const { Telegraf, Markup } = require('telegraf');
const { exec } = require('child_process');
const si = require('systeminformation');
const chalk = require('chalk');

// --- KONFIGURASI ---
const token = process.env.BOT_TOKEN;
const ownerId = Number(process.env.OWNER_ID); // Pastikan ini angka

if (!token) {
    console.error(chalk.red('❌ Token belum diset! Jalankan "npm start" dulu.'));
    process.exit(1);
}

const bot = new Telegraf(token);

// --- MIDDLEWARE KEAMANAN (PENTING!) ---
// Hanya Owner yang bisa pakai bot ini. Orang lain akan diabaikan.
bot.use(async (ctx, next) => {
    if (ctx.from && ctx.from.id === ownerId) {
        await next();
    } else {
        if (ctx.message) {
            ctx.reply('⛔ *Akses Ditolak!* Bot ini milik pribadi.', { parse_mode: 'Markdown' });
            console.log(chalk.red(`[Unauthorized Access] dari ${ctx.from.first_name} (${ctx.from.id})`));
        }
    }
});

// --- HELPER FUNGSI EKSEKUSI SHELL ---
const runCommand = async (ctx, command, loadingText = '⏳ Sedang memproses...') => {
    const msg = await ctx.reply(loadingText);
    
    // Eksekusi perintah bash
    exec(command, (error, stdout, stderr) => {
        let response = '';
        if (error) {
            response = `❌ *Error:*\n\`${error.message}\``;
        } else if (stderr) {
            // Kadang stderr isinya cuma warning, bukan error fatal
            response = `⚠️ *Stderr:*\n\`${stderr}\``;
            if (stdout) response += `\n\n✅ *Output:*\n\`${stdout}\``;
        } else {
            response = `✅ *Sukses:*\n\`${stdout}\``;
        }

        // Potong pesan jika terlalu panjang untuk Telegram (Limit 4096 char)
        if (response.length > 4000) response = response.substring(0, 4000) + '... (terpotong)';

        ctx.telegram.editMessageText(ctx.chat.id, msg.message_id, null, response, { parse_mode: 'Markdown' })
            .catch(() => ctx.reply(response)); // Fallback jika edit gagal
    });
};

// --- MENU UTAMA ---
const mainMenu = Markup.inlineKeyboard([
    [Markup.button.callback('🖥️ System Info', 'sys_info'), Markup.button.callback('🔄 Update VPS', 'vps_update')],
    [Markup.button.callback('🚀 Install Script (ZiVPN)', 'install_zivpn'), Markup.button.callback('🗑️ Clear RAM', 'clear_ram')],
    [Markup.button.callback('💀 Reboot Server', 'reboot_vps'), Markup.button.callback('🔌 Cek Port', 'check_port')]
]);

bot.start((ctx) => {
    ctx.reply(`
👮‍♂️ *CilBot VPS Manager*
Server Control Panel

Selamat datang, Master *${ctx.from.first_name}*.
Silakan pilih perintah di bawah:
    `, { parse_mode: 'Markdown', ...mainMenu });
});

// --- ACTIONS HANDLER ---

// 1. System Info (Mirip Neofetch tapi realtime)
bot.action('sys_info', async (ctx) => {
    const msg = await ctx.reply('⏳ Mengambil data server...');
    try {
        const cpu = await si.currentLoad();
        const mem = await si.mem();
        const os = await si.osInfo();
        const uptime = si.time().uptime;

        // Format waktu uptime
        const h = Math.floor(uptime / 3600);
        const m = Math.floor((uptime % 3600) / 60);

        const text = `
📊 *SERVER STATUS*
-------------------------
🖥️ *OS:* ${os.distro}
⏱️ *Uptime:* ${h} Jam ${m} Menit
🧠 *RAM:* ${(mem.active / 1024 / 1024 / 1024).toFixed(2)}GB / ${(mem.total / 1024 / 1024 / 1024).toFixed(2)}GB
⚡ *CPU Load:* ${cpu.currentLoad.toFixed(2)}%
-------------------------
`;
        ctx.telegram.editMessageText(ctx.chat.id, msg.message_id, null, text, { parse_mode: 'Markdown' });
    } catch (e) {
        ctx.reply('Gagal mengambil info system.');
    }
});

// 2. Update VPS (apt update)
bot.action('vps_update', (ctx) => {
    runCommand(ctx, 'apt update && apt upgrade -y', '🔄 Sedang melakukan update & upgrade package...');
});

// 3. Install Script (Contoh: Menjalankan script setup.sh dari repo ZiVPN Anda)
bot.action('install_zivpn', (ctx) => {
    // Perintah ini mendownload script setup.sh anda dan menjalankannya
    // NOTE: Karena setup.sh biasanya interaktif (butuh input keyboard), 
    // kita asumsikan kita hanya mendownloadnya atau menjalankan perintah auto-install jika ada.
    
    const cmd = 'wget https://raw.githubusercontent.com/Pujianto1219/ZiVPN/main/setup.sh && chmod +x setup.sh && ./setup.sh --auto'; 
    // Tambahkan flag --auto jika script bash anda mendukung auto install tanpa tanya-tanya
    
    ctx.reply('⚠️ *Peringatan:* Jika script `setup.sh` membutuhkan input manual (seperti memilih angka 1, 2), script akan macet di sini.\n\nSaya akan mencoba mendownload file-nya saja.');
    
    runCommand(ctx, 'wget -qO setup.sh https://raw.githubusercontent.com/Pujianto1219/ZiVPN/main/setup.sh && chmod +x setup.sh && ls -lh setup.sh', '⬇️ Downloading Setup Script...');
});

// 4. Clear RAM
bot.action('clear_ram', (ctx) => {
    runCommand(ctx, 'sync; echo 3 > /proc/sys/vm/drop_caches', '🧹 Membersihkan Cache RAM...');
});

// 5. Cek Port
bot.action('check_port', (ctx) => {
    runCommand(ctx, 'netstat -nutlp', '🔌 Checking open ports...');
});

// 6. Reboot (Bahaya butuh konfirmasi)
bot.action('reboot_vps', (ctx) => {
    ctx.reply('⚠️ Anda yakin ingin me-restart server?', Markup.inlineKeyboard([
        Markup.button.callback('✅ YA, Reboot Sekarang', 'confirm_reboot'),
        Markup.button.callback('❌ Batal', 'cancel')
    ]));
});

bot.action('confirm_reboot', (ctx) => {
    ctx.reply('🔄 Server sedang reboot... Bot akan offline sebentar.');
    exec('reboot');
});

bot.action('cancel', (ctx) => ctx.deleteMessage());

// --- CUSTOM SHELL COMMAND ---
// Fitur canggih: Ketik /exec <perintah> untuk menjalankan apa saja
bot.command('exec', (ctx) => {
    const cmd = ctx.message.text.replace('/exec ', '');
    if (!cmd || cmd === '/exec') return ctx.reply('Tulis perintahnya. Contoh:\n/exec ls -lah');
    runCommand(ctx, cmd);
});

// Start Bot
console.log(chalk.green('🚀 CilBot Manager (VPS) Berjalan!'));
bot.launch();

process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));
