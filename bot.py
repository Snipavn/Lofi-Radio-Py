#Tải package pip install discord dotenv yt_dlp dotenv

import os
import discord
from discord import app_commands
from discord.ext import commands
from yt_dlp import YoutubeDL
from dotenv import load_dotenv
import asyncio
import ffmpeg

# Load token từ file .env
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

LOFI_URL = "https://www.youtube.com/watch?v=jfKfPfyJRdk"
VOICE_CHANNEL_FILE = "voice_channel.txt"

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree


async def play_lofi(vc: discord.VoiceClient):
    if vc.is_playing():
        return

    ffmpeg_opts = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }

    ydl_opts = {'format': 'bestaudio'}
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(LOFI_URL, download=False)
        stream_url = info['url']

    vc.play(discord.FFmpegPCMAudio(stream_url, **ffmpeg_opts), after=lambda e: asyncio.run_coroutine_threadsafe(play_lofi(vc), bot.loop))
    print("🎧 Đang phát Lofi Radio...")


@bot.event
async def on_ready():
    print(f"✅ Bot đã đăng nhập: {bot.user.name}")
    await tree.sync()

    try:
        with open(VOICE_CHANNEL_FILE, "r") as f:
            channel_id = int(f.read())

        for guild in bot.guilds:
            channel = guild.get_channel(channel_id)
            if isinstance(channel, discord.VoiceChannel):
                vc = await channel.connect()
                await play_lofi(vc)
                break
    except FileNotFoundError:
        print("ℹ️ Chưa có kênh voice được thiết lập. Dùng /setvoice để chọn.")


class LofiControlView(discord.ui.View):
    def __init__(self, vc: discord.VoiceClient):
        super().__init__(timeout=None)
        self.vc = vc

    @discord.ui.button(label="▶️ Play", style=discord.ButtonStyle.success)
    async def play(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.vc.is_playing():
            await play_lofi(self.vc)
            await interaction.response.send_message("▶️ Đã phát lại Lofi.", ephemeral=True)
        else:
            await interaction.response.send_message("🎶 Đang phát rồi.", ephemeral=True)

    @discord.ui.button(label="⏸️ Pause", style=discord.ButtonStyle.secondary)
    async def pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.vc.is_playing():
            self.vc.pause()
            await interaction.response.send_message("⏸️ Đã tạm dừng nhạc.", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Không có nhạc đang phát.", ephemeral=True)

    @discord.ui.button(label="⏹️ Stop", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.vc.is_playing():
            self.vc.stop()
            await interaction.response.send_message("⏹️ Đã dừng nhạc.", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Không có nhạc đang phát.", ephemeral=True)

    @discord.ui.button(label="👋 Leave", style=discord.ButtonStyle.danger)
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.vc.disconnect()
        await interaction.response.send_message("👋 Bot đã rời khỏi voice.", ephemeral=True)
        self.stop()


@tree.command(name="setvoice", description="Chọn kênh voice để phát Lofi Radio")
@app_commands.describe(channel="Chọn kênh voice")
async def setvoice(interaction: discord.Interaction, channel: discord.VoiceChannel):
    with open(VOICE_CHANNEL_FILE, "w") as f:
        f.write(str(channel.id))

    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()

    vc = await channel.connect()
    await play_lofi(vc)

    view = LofiControlView(vc)
    await interaction.response.send_message(
        f"✅ Đã kết nối tới **{channel.name}** và đang phát Lofi.",
        view=view
    )


bot.run(TOKEN)
