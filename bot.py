import os
import asyncio
from datetime import datetime
from typing import Dict, Tuple, Optional

import discord
from discord.ext import commands
from discord import app_commands, Intents
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_BOT_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID', 0))
WELCOME_CHANNEL_ID = int(os.getenv('WELCOME_CHANNEL_ID', 0))
BY_CHANNEL_ID = int(os.getenv('BY_CHANNEL_ID', 0))
LOG_CHANNEL_ID = int(os.getenv('LOG_CHANNEL_ID', 0))

# ---- Intents / Bot ----
intents = Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# 招待キャッシュ構造
# guild_id -> {
#   "uses": {invite_code: uses_int},
#   "inviter": {invite_code: inviter_id},
#   "vanity": vanity_uses_int or None
# }
# =========================
invite_cache: Dict[int, Dict[str, Dict[str, int]]] = {}

# ---------- ユーティリティ ----------
def utc_str(dt: Optional[datetime] = None) -> str:
    return (dt or datetime.utcnow()).strftime('%Y/%m/%d %H:%M:%S')

def get_text_channel(guild: discord.Guild, channel_id: int) -> Optional[discord.TextChannel]:
    ch = guild.get_channel(channel_id)
    return ch if isinstance(ch, discord.TextChannel) else None

async def snapshot_invites(guild: discord.Guild) -> Tuple[Dict[str, int], Dict[str, int], Optional[int]]:
    """現在の招待の使用回数と招待者をスナップショット"""
    uses_map: Dict[str, int] = {}
    inviter_map: Dict[str, int] = {}

    try:
        invites = await guild.invites()
        for inv in invites:
            uses_map[inv.code] = inv.uses or 0
            if inv.inviter:
                inviter_map[inv.code] = inv.inviter.id
    except discord.Forbidden:
        # 権限不足
        pass
    except discord.HTTPException:
        pass

    vanity_uses = None
    try:
        # サーバーがバニティURL（discord.gg/xxxx）を持つ場合
        vanity = await guild.vanity_invite()
        if vanity:
            vanity_uses = vanity.uses or 0
    except discord.Forbidden:
        pass
    except discord.HTTPException:
        pass

    return uses_map, inviter_map, vanity_uses

def detect_inviter_from_delta(
    before_uses: Dict[str, int],
    after_uses: Dict[str, int],
    inviter_map: Dict[str, int],
    before_vanity: Optional[int],
    after_vanity: Optional[int]
) -> Tuple[Optional[int], Optional[str], int]:
    """
    招待使用回数の差分から、招待者ユーザーIDと招待コード、増加数を返す
    返り値: (inviter_id, invite_code or 'VANITY', delta)
    """
    # 通常の招待コードで差分が出ているものを探す（最大増加のものを採用）
    top_code = None
    top_delta = 0
    for code, after_val in after_uses.items():
        before_val = before_uses.get(code, 0)
        delta = after_val - before_val
        if delta > top_delta:
            top_delta = delta
            top_code = code

    if top_code and top_delta > 0:
        inviter_id = inviter_map.get(top_code)
        return inviter_id, top_code, top_delta

    # バニティURLの増加をチェック
    if after_vanity is not None and before_vanity is not None:
        v_delta = after_vanity - before_vanity
        if v_delta > 0:
            return None, "VANITY", v_delta

    return None, None, 0

async def send_log_embed(
    guild: discord.Guild,
    title: str,
    description: str,
    color: discord.Color = discord.Color.blurple(),
    thumbnail_url: Optional[str] = None,
    fields: Optional[list] = None,
):
    ch = get_text_channel(guild, LOG_CHANNEL_ID)
    if not ch:
        return
    embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.utcnow())
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    if fields:
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)
    await ch.send(embed=embed)

# ---------- 起動時 ----------
@bot.event
async def on_ready():
    try:
        # ギルド限定でコマンド同期
        if GUILD_ID:
            guild_obj = bot.get_guild(GUILD_ID)
            if guild_obj:
                synced = await bot.tree.sync(guild=guild_obj)
                print(f"✅ Synced {len(synced)} command(s) to guild {GUILD_ID}.")
            else:
                synced = await bot.tree.sync()
                print(f"ℹ️ Guild not found. Synced {len(synced)} command(s) globally.")
        else:
            synced = await bot.tree.sync()
            print(f"ℹ️ GUILD_ID 未設定。Synced {len(synced)} command(s) globally.")

    except Exception as e:
        print(f"❌ Sync failed: {e}")

    # 招待キャッシュを構築
    for guild in bot.guilds:
        uses_map, inviter_map, vanity_uses = await snapshot_invites(guild)
        invite_cache[guild.id] = {
            "uses": uses_map,
            "inviter": inviter_map,
            "vanity": {"uses": vanity_uses if vanity_uses is not None else -1}
        }
    # ログ
    if LOG_CHANNEL_ID:
        ch = bot.get_channel(LOG_CHANNEL_ID)
        if isinstance(ch, discord.TextChannel):
            await ch.send("✅ Botが起動しました。")

# ---------- 招待の作成/削除でキャッシュ更新 ----------
@bot.event
async def on_invite_create(invite: discord.Invite):
    guild = invite.guild
    if not guild:
        return
    # 再スナップショット
    uses_map, inviter_map, vanity_uses = await snapshot_invites(guild)
    invite_cache[guild.id] = {
        "uses": uses_map,
        "inviter": inviter_map,
        "vanity": {"uses": vanity_uses if vanity_uses is not None else -1}
    }

@bot.event
async def on_invite_delete(invite: discord.Invite):
    guild = invite.guild
    if not guild:
        return
    # 再スナップショット
    uses_map, inviter_map, vanity_uses = await snapshot_invites(guild)
    invite_cache[guild.id] = {
        "uses": uses_map,
        "inviter": inviter_map,
        "vanity": {"uses": vanity_uses if vanity_uses is not None else -1}
    }

# ---------- 参加 ----------
@bot.event
async def on_member_join(member: discord.Member):
    guild = member.guild
    join_time = utc_str()

    # 参加メッセージ（公開チャンネル）
    if WELCOME_CHANNEL_ID:
        channel = bot.get_channel(WELCOME_CHANNEL_ID)
        if isinstance(channel, discord.TextChannel):
            embed = discord.Embed(
                title="🎉 新しいメンバーが参加！",
                description=f"{member.mention} ようこそサーバーへ！",
                color=discord.Color.green(),
                timestamp=datetime.utcnow(),
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="ユーザー名", value=f"{member} ", inline=True)
            embed.add_field(name="ID", value=str(member.id), inline=True)
            embed.set_footer(text=f"参加日時: {join_time}")
            await channel.send(embed=embed)

    # DMで認証案内
    try:
        dm = await member.create_dm()
        embed_dm = discord.Embed(
            title="🔐 認証が必要です",
            description=f"{member.mention} 認証がまだ完了していません。\n下のボタンから認証してください。",
            color=discord.Color.blurple(),
            timestamp=datetime.utcnow(),
        )
        embed_dm.set_footer(text="セキュリティ保護のため認証が必要です。")
        view_dm = discord.ui.View()
        view_dm.add_item(discord.ui.Button(label="✅ 認証する", style=discord.ButtonStyle.link, url="https://your-auth-link.com"))
        await dm.send(embed=embed_dm, view=view_dm)
    except discord.Forbidden:
        # DM閉鎖ユーザー
        pass

    # --- 招待追跡 ---
    # 参加前のキャッシュ
    before = invite_cache.get(guild.id, {"uses": {}, "inviter": {}, "vanity": {"uses": -1}})
    before_uses = before.get("uses", {})
    before_vanity = before.get("vanity", {}).get("uses", -1)
    # 直後のスナップショット
    after_uses, inviter_map, after_vanity = await snapshot_invites(guild)

    inviter_id, invite_code, delta = detect_inviter_from_delta(
        before_uses=before_uses,
        after_uses=after_uses,
        inviter_map=inviter_map,
        before_vanity=before_vanity if before_vanity != -1 else None,
        after_vanity=after_vanity
    )

    # キャッシュ更新
    invite_cache[guild.id] = {
        "uses": after_uses,
        "inviter": inviter_map,
        "vanity": {"uses": after_vanity if after_vanity is not None else -1}
    }

    # ログ送信
    fields = [
        ("ユーザー", f"{member} (`{member.id}`)", True),
        ("参加日時 (UTC)", join_time, True),
    ]
    thumb = member.display_avatar.url

    if invite_code == "VANITY":
        await send_log_embed(
            guild,
            "👋 メンバー参加（バニティURL）",
            f"{member.mention} が参加しました。\nバニティURL（カスタム招待）からの参加と推測されます（+{delta}）。",
            color=discord.Color.brand_green(),
            thumbnail_url=thumb,
            fields=fields,
        )
    elif inviter_id:
        inviter_user = guild.get_member(inviter_id) or (await bot.fetch_user(inviter_id))
        inv_name = f"{inviter_user} (`{inviter_id}`)" if inviter_user else f"`{inviter_id}`"
        await send_log_embed(
            guild,
            "👋 メンバー参加（招待追跡）",
            f"{member.mention} が参加しました。\n**招待者:** {inv_name}\n**招待コード:** `{invite_code}`（+{delta}）",
            color=discord.Color.brand_green(),
            thumbnail_url=thumb,
            fields=fields,
        )
    else:
        await send_log_embed(
            guild,
            "👋 メンバー参加",
            f"{member.mention} が参加しました（招待者の特定はできませんでした）。",
            color=discord.Color.brand_green(),
            thumbnail_url=thumb,
            fields=fields,
        )

# ---------- 退出 ----------
@bot.event
async def on_member_remove(member: discord.Member):
    guild = member.guild
    ch = get_text_channel(guild, BY_CHANNEL_ID)
    embed = discord.Embed(
        title="😢 さようなら、また会う日まで。",
        description=f"**{member}** さんがサーバーを退出しました。",
        color=discord.Color.dark_red(),
        timestamp=datetime.utcnow(),
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"ID: {member.id}｜退会時刻: {utc_str()}")
    if ch:
        await ch.send(embed=embed)

# ---------- メッセージ削除 ----------
@bot.event
async def on_message_delete(message: discord.Message):
    if message.author.bot:
        return
    content = message.content or "(本文なし)"
    # 長文対策でトリム
    if len(content) > 1500:
        content = content[:1500] + " …(省略)"
    attach_info = ""
    if message.attachments:
        urls = "\n".join(att.url for att in message.attachments[:5])
        attach_info = f"\n**添付:**\n{urls}"

    await send_log_embed(
        message.guild,
        "🗑️ メッセージ削除",
        f"**ユーザー:** {message.author.mention}\n**チャンネル:** {message.channel.mention}\n```{content}```{attach_info}",
        color=discord.Color.red(),
        thumbnail_url=message.author.display_avatar.url,
    )

# ---------- メッセージ編集 ----------
@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    if before.author.bot:
        return
    if before.content == after.content:
        return

    before_c = before.content or "(本文なし)"
    after_c = after.content or "(本文なし)"
    if len(before_c) > 1000:
        before_c = before_c[:1000] + " …(省略)"
    if len(after_c) > 1000:
        after_c = after_c[:1000] + " …(省略)"

    await send_log_embed(
        before.guild,
        "✏️ メッセージ編集",
        f"**ユーザー:** {before.author.mention}\n**チャンネル:** {before.channel.mention}\n**Before:**\n```{before_c}```\n**After:**\n```{after_c}```",
        color=discord.Color.orange(),
        thumbnail_url=before.author.display_avatar.url,
    )

# ---------- ロール変更 ----------
@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    if before.roles == after.roles:
        return

    added = [r for r in after.roles if r not in before.roles]
    removed = [r for r in before.roles if r not in after.roles]

    fields = []
    if added:
        fields.append(("追加されたロール", ", ".join([r.mention for r in added]), False))
    if removed:
        fields.append(("削除されたロール", ", ".join([r.mention for r in removed]), False))

    await send_log_embed(
        after.guild,
        "🧩 ロール変更",
        f"{after.mention} のロールが変更されました。",
        color=discord.Color.teal(),
        thumbnail_url=after.display_avatar.url,
        fields=fields,
    )

# =========================
# スラッシュコマンド
# =========================
@bot.tree.command(name="ルール", description="サーバールールを表示します")
@app_commands.guilds(discord.Object(id=GUILD_ID))  # ギルド限定
async def rule_command(interaction: discord.Interaction):
    rules_text = (
        "**サーバールール**\n"
        "1. 荒らし禁止\n"
        "2. スパム禁止\n"
        "3. 他人に迷惑をかけない\n"
        "4. モデレーターの指示に従う\n"
    )
    await interaction.response.send_message(rules_text, ephemeral=True)

@bot.tree.command(name="認証", description="認証を案内します")
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def auth_command(interaction: discord.Interaction):
    view = discord.ui.View()
    # 必要に応じてURLを差し替え
    view.add_item(discord.ui.Button(label="認証する", style=discord.ButtonStyle.link, url="https://jaf-ruan.onrender.com/"))
    await interaction.response.send_message("以下のボタンから認証を進めてください：", view=view, ephemeral=True)

# ========== 実行 ==========
if not TOKEN:
    raise RuntimeError("環境変数 DISCORD_BOT_TOKEN が設定されていません。")
if not GUILD_ID:
    print("⚠️ 環境変数 GUILD_ID が未設定です（グローバル同期になります）。")
bot.run(TOKEN)
