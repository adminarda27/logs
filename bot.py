import os
import discord
from discord.ext import commands
from discord import app_commands, Intents
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_BOT_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID', 0))
WELCOME_CHANNEL_ID = int(os.getenv('WELCOME_CHANNEL_ID', 0))
BY_CHANNEL_ID = int(os.getenv('BY_CHANNEL_ID', 0))
AUTH_CHANNEL_ID = int(os.getenv('AUTH_CHANNEL_ID', 0))
LOG_CHANNEL_ID = int(os.getenv('LOG_CHANNEL_ID', 0))
INVITE_TRACK_CHANNEL_ID = int(os.getenv('INVITE_TRACK_CHANNEL_ID', 0))

intents = Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"✅ Synced {len(synced)} command(s).")
    except Exception as e:
        print(f"❌ Sync failed: {e}")
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send("✅ Botが起動しました。")

@bot.event
async def on_member_join(member):
    if WELCOME_CHANNEL_ID:
        channel = bot.get_channel(WELCOME_CHANNEL_ID)
        if channel:
            await channel.send(f"🎉 ようこそ {member.mention}！")
    if AUTH_CHANNEL_ID:
        channel = bot.get_channel(AUTH_CHANNEL_ID)
        if channel:
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="認証する", style=discord.ButtonStyle.link, url="https://your-auth-link.com"))
            await channel.send(f"{member.mention} 認証を完了してください。", view=view)

@bot.event
async def on_member_remove(member):
    if BY_CHANNEL_ID:
        channel = bot.get_channel(BY_CHANNEL_ID)
        if channel:
            await channel.send(f"👋 {member.name} が退出しました。")

@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(
            f"🗑️ メッセージ削除 by {message.author.mention}:\n```{message.content}```"
        )

@bot.event
async def on_message_edit(before, after):
    if before.author.bot:
        return
    if before.content != after.content:
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(
                f"✏️ メッセージ編集 by {before.author.mention}:\n**Before:** ```{before.content}```\n**After:** ```{after.content}```"
            )

@bot.event
async def on_member_update(before, after):
    if before.roles == after.roles:
        return
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    added_roles = [r for r in after.roles if r not in before.roles]
    removed_roles = [r for r in before.roles if r not in after.roles]
    if added_roles:
        await log_channel.send(f"✅ {after.mention} にロール追加: {', '.join([r.name for r in added_roles])}")
    if removed_roles:
        await log_channel.send(f"❌ {after.mention} からロール削除: {', '.join([r.name for r in removed_roles])}")

# -----------------------------
# スラッシュコマンド
# -----------------------------

@bot.tree.command(name="ルール", description="サーバールールを表示します", guild=discord.Object(id=GUILD_ID))
async def rule_command(interaction: discord.Interaction):
    rules_text = "**サーバールール**\n1. 荒らし禁止\n2. スパム禁止\n3. 他人に迷惑をかけない"
    await interaction.response.send_message(rules_text, ephemeral=True)

@bot.tree.command(name="認証", description="認証を案内します", guild=discord.Object(id=GUILD_ID))
async def auth_command(interaction: discord.Interaction):
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="認証する", style=discord.ButtonStyle.link, url="https://your-auth-link.com"))
    await interaction.response.send_message("以下のボタンから認証を進めてください：", view=view, ephemeral=True)

bot.run(TOKEN)
