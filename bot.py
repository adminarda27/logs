import os
import discord
from discord.ext import commands
from discord import app_commands, Intents
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

TOKEN = os.getenv('DISCORD_BOT_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID', 0))
WELCOME_CHANNEL_ID = int(os.getenv('WELCOME_CHANNEL_ID', 0))
BY_CHANNEL_ID = int(os.getenv('BY_CHANNEL_ID', 0))
LOG_CHANNEL_ID = int(os.getenv('LOG_CHANNEL_ID', 0))

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
    join_time = datetime.utcnow().strftime('%Y/%m/%d %H:%M:%S')

    # --- WELCOME Embed ---
    if WELCOME_CHANNEL_ID:
        channel = bot.get_channel(WELCOME_CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                title="🎉 新しいメンバーが参加！",
                description=f"{member.mention} ようこそサーバーへ！",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
            embed.add_field(name="ユーザー名", value=f"{member.name}#{member.discriminator}", inline=True)
            embed.add_field(name="ID", value=member.id, inline=True)
            embed.set_footer(text=f"参加日時: {join_time}")
            await channel.send(embed=embed)

    # --- DMでのみ認証案内を送信 ---
    try:
        dm = await member.create_dm()
        embed_dm = discord.Embed(
            title="🔐 認証が必要です",
            description=f"{member.mention} 認証がまだ完了していません。\n下のボタンから認証してください。",
            color=discord.Color.blurple()
        )
        embed_dm.set_footer(text="セキュリティ保護のため認証が必要です。")
        view_dm = discord.ui.View()
        view_dm.add_item(discord.ui.Button(label="✅ 認証する", style=discord.ButtonStyle.link, url="https://your-auth-link.com"))
        await dm.send(embed=embed_dm, view=view_dm)
    except discord.Forbidden:
        print(f"⚠️ {member.name} にDMを送れませんでした。")

@bot.event
async def on_member_remove(member):
    if BY_CHANNEL_ID:
        channel = bot.get_channel(BY_CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                title="😢 さようなら、また会う日まで。",
                description=f"**{member.name}#{member.discriminator}** さんがサーバーを退出しました。",
                color=discord.Color.dark_red()
            )
            embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
            embed.set_footer(text=f"ID: {member.id}｜退会時刻: {datetime.utcnow().strftime('%Y/%m/%d %H:%M:%S')}")
            await channel.send(embed=embed)

@bot.event
async def on_message_delete(message):
    # ボットのメッセージ削除は無視
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
    if added_roles and log_channel:
        await log_channel.send(f"✅ {after.mention} にロール追加: {', '.join([r.name for r in added_roles])}")
    if removed_roles and log_channel:
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
