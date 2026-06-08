import discord
from discord.ext import commands
from discord.ui import Button, View
import json
import os
import random
import time
import asyncio

TOKEN = "your token here"

FREE_COOLDOWN = 86400
PREMIUM_COOLDOWN = 180  # 3 minutes
PREMIUM_ROLE = "Premium"
PREMIUM_LIMIT = 3
PREMIUM_LIMIT_WINDOW = 43200  # 12 hours

ALTS_FILE = "alts.json"
PREMIUM_FILE = "premium.json"
COOLDOWN_FILE = "cooldowns.json"
USED_FILE = "used.json"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================= FILE CREATION =================
for file in [ALTS_FILE, PREMIUM_FILE, COOLDOWN_FILE, USED_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({}, f)

def load(file):
    if not os.path.exists(file):
        return {}
    try:
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except:
        return {}

def save(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

panel_message = None

# ================= BOT READY =================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Synced commands")
    print(f"🤖 Bot is online as {bot.user}")

# ================= PANEL =================
def create_panel():
    normal_stock = load(ALTS_FILE)
    premium_stock = load(PREMIUM_FILE)

    embed = discord.Embed(
        title="🔥 Jxv Alt Generator 🔥",
        description="Click a button below to generate an account.",
        color=discord.Color.from_rgb(0, 20, 255)
    )
    embed.add_field(
        name="📦 Stock",
        value=f"Normal: **{len(normal_stock)}**\nPremium: **{len(premium_stock)}**",
        inline=False
    )
    embed.add_field(
        name="⏱ Cooldown & Limits",
        value="Free Users: 24 Hours\nPremium Users: 3 Minutes\nPremium Limit: 3 Accounts / 12 Hours",
    )

    view = View(timeout=None)
    normal_btn = Button(label="Generate Account", style=discord.ButtonStyle.primary, emoji="⚡")
    premium_btn = Button(label="Premium Generate", style=discord.ButtonStyle.success, emoji="💎")

    async def normal_click(interaction):
        await generate_account(interaction, ALTS_FILE)

    async def premium_click(interaction):
        if PREMIUM_ROLE not in [r.name for r in interaction.user.roles]:
            await interaction.response.send_message("Premium only button.", ephemeral=True)
            return
        await generate_account(interaction, PREMIUM_FILE)

    normal_btn.callback = normal_click
    premium_btn.callback = premium_click
    view.add_item(normal_btn)
    view.add_item(premium_btn)

    return embed, view

async def update_panel():
    global panel_message
    if panel_message is None:
        return
    embed, view = create_panel()
    try:
        await panel_message.edit(embed=embed, view=view)
    except:
        pass

# ================= GENERATE ACCOUNT =================
async def generate_account(interaction, file):
    await interaction.response.send_message("🔄 Generating account...", ephemeral=True)
    await asyncio.sleep(2)

    stock = load(file)
    cooldowns = load(COOLDOWN_FILE)
    used = load(USED_FILE)

    user = str(interaction.user.id)
    now = time.time()
    is_premium = PREMIUM_ROLE in [r.name for r in interaction.user.roles]
    cooldown = PREMIUM_COOLDOWN if is_premium else FREE_COOLDOWN

    if user in cooldowns:
        remaining = cooldown - (now - cooldowns[user])
        if remaining > 0:
            await interaction.edit_original_response(content="You are on cooldown.")
            return

    if is_premium:
        if user not in used or not isinstance(used[user], list):
            used[user] = []
        used[user] = [t for t in used[user] if now - t < PREMIUM_LIMIT_WINDOW]
        if len(used[user]) >= PREMIUM_LIMIT:
            await interaction.edit_original_response(
                content="❌ Premium users can only generate **3 accounts every 12 hours**."
            )
            save(USED_FILE, used)
            return

    if len(stock) == 0:
        await interaction.edit_original_response(content="No accounts left.")
        return

    key = random.choice(list(stock.keys()))
    acc = stock[key]
    del stock[key]
    save(file, stock)

    cooldowns[user] = now
    save(COOLDOWN_FILE, cooldowns)

    used.setdefault(user, []).append(now)
    save(USED_FILE, used)

    try:
        await interaction.user.send(
            f"✅ Here is your account:\n\n"
            f"**Username:** {acc['username']}\n"
            f"**Password:** {acc['password']}"
        )
        await interaction.edit_original_response(content="📩 Account sent to your DMs enjoy!")
    except:
        await interaction.edit_original_response(
            content="❌ I couldn't DM you. Turn on DMs and try again."
        )

    await update_panel()

# ================= COMMANDS =================
@bot.tree.command(name="panel", description="Send the generator panel")
async def panel(interaction: discord.Interaction):
    global panel_message
    embed, view = create_panel()
    panel_message = await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message("✅ Panel sent!", ephemeral=True)

@bot.tree.command(name="stock", description="Check stock")
async def stock(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"📦 Normal: {len(load(ALTS_FILE))}\n💎 Premium: {len(load(PREMIUM_FILE))}",
        ephemeral=True
    )

@bot.tree.command(name="cooldown", description="Check cooldown")
async def cooldown(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.send_message("🔍 Checking...", ephemeral=True)
    try:
        cooldowns = load(COOLDOWN_FILE)
        user_id = str(member.id)
        if user_id not in cooldowns:
            await interaction.edit_original_response(content=f"{member.mention} has no active cooldown.")
            return
        is_premium = PREMIUM_ROLE in [r.name for r in member.roles]
        cd_time = PREMIUM_COOLDOWN if is_premium else FREE_COOLDOWN
        remaining = cd_time - (time.time() - cooldowns[user_id])
        if remaining <= 0:
            await interaction.edit_original_response(content=f"{member.mention} is ready to generate.")
            return
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)
        await interaction.edit_original_response(content=f"{member.mention} cooldown left: **{minutes}m {seconds}s**")
    except:
        await interaction.edit_original_response(content="❌ Error checking cooldown.")

# ================= RESET COOLDOWN (ADMIN ONLY) =================
@bot.tree.command(name="resetcooldown", description="Reset a user's cooldown")
async def resetcooldown(interaction: discord.Interaction, member: discord.Member):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Admin only.", ephemeral=True)
        return

    try:
        cooldowns = load(COOLDOWN_FILE)
        uid = str(member.id)

        if uid in cooldowns:
            del cooldowns[uid]
            save(COOLDOWN_FILE, cooldowns)

        await interaction.response.send_message(
            f"✅ Cooldown reset for {member.mention}",
            ephemeral=True
        )
    except:
        await interaction.response.send_message("❌ Error resetting cooldown.", ephemeral=True)

# ================= RESET 12-HOUR PREMIUM LIMIT (ADMIN ONLY) =================
@bot.tree.command(name="reset12h", description="Reset the 12-hour premium generation limit")
async def reset12h(interaction: discord.Interaction, member: discord.Member):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Admin only.", ephemeral=True)
        return

    try:
        used = load(USED_FILE)
        uid = str(member.id)

        if uid in used:
            del used[uid]
            save(USED_FILE, used)

        await interaction.response.send_message(
            f"✅ Reset 12-hour premium limit for {member.mention}",
            ephemeral=True
        )
    except:
        await interaction.response.send_message("❌ Error resetting 12-hour limit.", ephemeral=True)

# ================= ROLE COMMANDS =================
@bot.tree.command(name="giverole", description="Give premium role")
async def giverole(interaction: discord.Interaction, member: discord.Member):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Admin only.", ephemeral=True)
        return
    try:
        role = discord.utils.get(interaction.guild.roles, name=PREMIUM_ROLE)
        if role is None:
            await interaction.response.send_message("❌ Premium role not found. Create one named 'Premium'.", ephemeral=True)
            return
        await member.add_roles(role)
        await interaction.response.send_message(f"✅ Gave **Premium** to {member.mention}", ephemeral=True)
    except:
        await interaction.response.send_message("❌ Error giving role.", ephemeral=True)

@bot.tree.command(name="removerole", description="Remove premium role")
async def removerole(interaction: discord.Interaction, member: discord.Member):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Admin only.", ephemeral=True)
        return
    try:
        role = discord.utils.get(interaction.guild.roles, name=PREMIUM_ROLE)
        if role is None:
            await interaction.response.send_message("❌ Premium role not found.", ephemeral=True)
            return
        await member.remove_roles(role)
        await interaction.response.send_message(f"✅ Removed **Premium** from {member.mention}", ephemeral=True)
    except:
        await interaction.response.send_message("❌ Error removing role.", ephemeral=True)

# ================= RESTOCK COMMANDS =================
@bot.tree.command(name="restock", description="Restock normal accounts")
async def restock(interaction: discord.Interaction, file: discord.Attachment):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Admin only.", ephemeral=True)
        return
    await interaction.response.send_message("📤 Processing file...", ephemeral=True)
    try:
        data = await file.read()
        text = data.decode("utf-8")
        lines = text.splitlines()
        stock = load(ALTS_FILE)
        added = 0
        for line in lines:
            line = line.strip()
            if not line or ":" not in line:
                continue
            username, password = line.split(":", 1)
            stock[str(random.randint(100000, 999999))] = {
                "username": username.strip(),
                "password": password.strip()
            }
            added += 1
        save(ALTS_FILE, stock)
        await update_panel()
        await interaction.edit_original_response(content=f"✅ Added **{added}** normal accounts.")
    except Exception as e:
        await interaction.edit_original_response(content=f"❌ Error: {str(e)}")

@bot.tree.command(name="restockpremium", description="Restock premium accounts")
async def restockpremium(interaction: discord.Interaction, file: discord.Attachment):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Admin only.", ephemeral=True)
        return
    await interaction.response.send_message("📤 Processing file...", ephemeral=True)
    try:
        data = await file.read()
        text = data.decode("utf-8")
        lines = text.splitlines()
        stock = load(PREMIUM_FILE)
        added = 0
        for line in lines:
            line = line.strip()
            if not line or ":" not in line:
                continue
            username, password = line.split(":", 1)
            stock[str(random.randint(100000, 999999))] = {
                "username": username.strip(),
                "password": password.strip()
            }
            added += 1
        save(PREMIUM_FILE, stock)
        await update_panel()
        await interaction.edit_original_response(content=f"✅ Added **{added}** premium accounts.")
    except Exception as e:
        await interaction.edit_original_response(content=f"❌ Error: {str(e)}")

bot.run(TOKEN)
