import asyncio
import io
import json
import os
import random
import time

import discord
from discord.ext import commands
from discord.ui import Button, Modal, Select, TextInput, View

TOKEN = os.getenv("DISCORD_TOKEN", "your token here")

FREE_COOLDOWN = 86400
PREMIUM_COOLDOWN = 300
BULK_COOLDOWN = 172800  
PREMIUM_ROLE = "Premium"
PREMIUM_LIMIT = 3
PREMIUM_LIMIT_WINDOW = 43200  
BULK_MIN = 10
BULK_MAX = 150
DEFAULT_BULK_ROLE = "Bulk Gen"
WEBSITE_URL = "https://jxvhub666.mysellauth.com/product/jxv-account-generator"

ALTS_FILE = "alts.json"
PREMIUM_FILE = "premium.json"
BULK_FILE = "bulk.json"
COOLDOWN_FILE = "cooldowns.json"
BULK_COOLDOWN_FILE = "bulk_cooldowns.json"
USED_FILE = "used.json"
CONFIG_FILE = "config.json"
LOG_FILE = "logs.json"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  

bot = commands.Bot(command_prefix="!", intents=intents)

panel_message = None


WEBHOOK_URL = None
WEBHOOK_CHANNEL_ID = None

def load_webhook_config():
    global WEBHOOK_URL, WEBHOOK_CHANNEL_ID
    config = load(CONFIG_FILE)
    WEBHOOK_URL = config.get("webhook_url")
    WEBHOOK_CHANNEL_ID = config.get("webhook_channel_id")


def save_webhook_config():
    save(CONFIG_FILE, {
        "webhook_url": WEBHOOK_URL,
        "webhook_channel_id": WEBHOOK_CHANNEL_ID
    })



def ensure_files():
    for file in [
        ALTS_FILE, PREMIUM_FILE, BULK_FILE, COOLDOWN_FILE,
        BULK_COOLDOWN_FILE, USED_FILE, CONFIG_FILE, LOG_FILE
    ]:
        if not os.path.exists(file):
            with open(file, "w", encoding="utf-8") as f:
                json.dump({}, f)


def load(file):
    if not os.path.exists(file):
        return {}
    try:
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def save(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def load_config():
    ensure_files()
    config = load(CONFIG_FILE)
    return {
        "bulk_role": config.get("bulk_role", DEFAULT_BULK_ROLE),
        "banner_url": config.get("banner_url"),
    }


def save_config(config):
    save(CONFIG_FILE, config)


def get_bulk_role_name():
    return load_config()["bulk_role"]


def user_has_role(member, role_name):
    return role_name in [role.name for role in member.roles]


def is_premium(member):
    return user_has_role(member, PREMIUM_ROLE)


def format_remaining(seconds):
    if seconds <= 0:
        return "0m"
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    if hours > 0:
        return f"{hours}h {minutes}m"
    secs = int(seconds % 60)
    return f"{minutes}m {secs}s"


def get_bulk_cooldown_remaining(user_id):
    bulk_cooldowns = load(BULK_COOLDOWN_FILE)
    user = str(user_id)
    if user not in bulk_cooldowns:
        return 0
    return BULK_COOLDOWN - (time.time() - bulk_cooldowns[user])


def get_logs():
    ensure_files()
    return load(LOG_FILE)


def log_generate(interaction, stock_type: str, amount: int = 1):
    logs = get_logs()
    member = interaction.guild.get_member(interaction.user.id)
    role_name = "None"
    if member and member.roles:
        roles = [r.name for r in member.roles if r.name != "@everyone"]
        if roles:
            role_name = ", ".join(roles[:3])

    entry = {
        "user": interaction.user.id,
        "username": interaction.user.name,
        "role": role_name,
        "type": stock_type,
        "amount": amount,
        "time": int(time.time())
    }

    if "logs" not in logs:
        logs["logs"] = []
    logs["logs"].append(entry)

    if len(logs["logs"]) > 2000:
        logs["logs"] = logs["logs"][-2000:]

    save(LOG_FILE, logs)


    if WEBHOOK_URL and WEBHOOK_CHANNEL_ID:
        try:
            send_to_webhook(entry)
        except:
            pass


def send_to_webhook(entry):
    if not WEBHOOK_URL or not WEBHOOK_CHANNEL_ID:
        return

    try:
        webhook = discord.Webhook.from_url(WEBHOOK_URL, client=bot)
        channel = bot.get_channel(int(WEBHOOK_CHANNEL_ID))
        if not channel:
            return

        color = discord.Color.from_rgb(0, 20, 255)
        if entry["type"] == "standard":
            color = discord.Color.from_rgb(0, 255, 100)
        elif entry["type"] == "premium":
            color = discord.Color.from_rgb(255, 215, 0)
        elif entry["type"] == "bulk":
            color = discord.Color.from_rgb(255, 100, 0)

        embed = discord.Embed(
            title=f"New {entry['type'].title()} Generation",
            description=(
                f"**Amount:** {entry['amount']} accounts\n"
                f"**User:** {entry['username']} (`{entry['user']}`)\n"
                f"**Role:** {entry['role']}\n"
                f"**Time:** <t:{entry['time']}:R>"
            ),
            color=color,
            timestamp=discord.utils.utcnow()
        )

        webhook.send(
            content=None,
            embeds=[embed],
            username="Account Generator",
            avatar_url="https://cdn.discordapp.com/embed/avatars/0.png"
        )
    except Exception:
        pass


def get_log_paginator(logs_list):
    fields = []
    for log in logs_list:
        time_str = f"<t:{log['time']}:R>"
        fields.append((
            f"**{log['type'].title()}** | {log['amount']} accounts",
            f"**User:** {log['username']} (`{log['user']}`)\n"
            f"**Role:** {log['role']}\n"
            f"**Time:** {time_str}"
        ))

    chunks = []
    for name, value in fields:
        line = f"**{name}**\n{value}\n{'─' * 50}"
        if len(chunks) == 0 or len("\n".join(chunks) + "\n" + line) > 4000:
            chunks.append("")
        chunks[-1] += "\n" + line

    paginator = discord.Paginator(max_size=4096, page_length=4000)
    for chunk in chunks:
        paginator.add_line(chunk)
    return paginator



async def bulk_generate_accounts(interaction, amount):
    if amount < BULK_MIN:
        await interaction.edit_original_response(content=f"The minimum bulk amount is **{BULK_MIN}** accounts per request.")
        return
    if amount > BULK_MAX:
        await interaction.edit_original_response(content=f"The maximum bulk amount is **{BULK_MAX}** accounts per request.")
        return

    remaining = get_bulk_cooldown_remaining(interaction.user.id)
    if remaining > 0:
        await interaction.edit_original_response(content=f"You are on bulk cooldown. Try again in **{format_remaining(remaining)}**.")
        return

    stock = load(BULK_FILE)
    if len(stock) < amount:
        await interaction.edit_original_response(content=f"Not enough bulk stock. Requested **{amount}**, but only **{len(stock)}** are available.")
        return

    keys = random.sample(list(stock.keys()), amount)
    removed = {key: stock[key] for key in keys}
    lines = [f"{acc['username']}:{acc['password']}" for acc in removed.values()]

    for key in keys:
        del stock[key]
    save(BULK_FILE, stock)

    buffer = io.BytesIO("\n".join(lines).encode("utf-8"))
    file = discord.File(buffer, filename=f"jxv_accounts_{amount}.txt")

    try:
        await interaction.user.send(
            content=f"Here are your **{amount}** account(s). Format: `username:password` (one per line)",
            file=file,
        )
        await interaction.edit_original_response(content=f"Successfully sent **{amount}** account(s) to your DMs.")
    except discord.Forbidden:
        stock.update(removed)
        save(BULK_FILE, stock)
        await interaction.edit_original_response(content="Could not DM you. Enable DMs and try again.\nNo accounts were removed.")
        return

    bulk_cooldowns = load(BULK_COOLDOWN_FILE)
    bulk_cooldowns[str(interaction.user.id)] = time.time()
    save(BULK_COOLDOWN_FILE, bulk_cooldowns)

    await update_panel()



def create_panel():
    config = load_config()
    normal_stock = load(ALTS_FILE)
    premium_stock = load(PREMIUM_FILE)
    bulk_stock = load(BULK_FILE)
    bulk_role = config["bulk_role"]

    embed = discord.Embed(
        title="Jxv Account Generator",
        description=(
            "Use the buttons below to generate accounts.\n"
            "Credentials are sent privately to your DMs."
        ),
        color=discord.Color.from_rgb(0, 20, 255),
    )

    if config["banner_url"]:
        embed.set_image(url=config["banner_url"])

    embed.add_field(
        name="Current Stock",
        value=(
            f"Standard: **{len(normal_stock)}**\n"
            f"Premium: **{len(premium_stock)}**\n"
            f"Bulk: **{len(bulk_stock)}**"
        ),
        inline=True,
    )
    embed.add_field(
        name="Cooldowns & Limits",
        value=(
            "**Standard** — 1 account every 24 hours\n"
            "**Premium** — 1 account every 5 minutes\n"
            "**Premium cap** — 3 accounts every 12 hours"
        ),
        inline=True,
    )
    embed.add_field(
        name="Bulk Generation",
        value=(
            f"Requires the **{bulk_role}** role.\n"
            f"Generate **{BULK_MIN}–{BULK_MAX}** accounts at once.\n"
            "**Bulk cooldown** — once every 2 days"
        ),
        inline=False,
    )
    embed.set_footer(text="Need more access? Visit our store using the button below.")

    view = View(timeout=None)

    normal_btn = Button(label="Generate Standard", style=discord.ButtonStyle.primary, emoji="⚡", custom_id="panel_generate_standard")
    shop_btn = Button(label="Visit Store", style=discord.ButtonStyle.link, url=WEBSITE_URL, emoji="🛒")
    premium_btn = Button(label="Generate Premium", style=discord.ButtonStyle.success, emoji="💎", custom_id="panel_generate_premium")
    bulk_btn = Button(label="Bulk Generate", style=discord.ButtonStyle.secondary, emoji="📦", custom_id="panel_bulk_generate")

    async def normal_click(interaction):
        await generate_account(interaction, ALTS_FILE)

    async def premium_click(interaction):
        if not is_premium(interaction.user):
            await interaction.response.send_message("This button is for **Premium** members only.", ephemeral=True)
            return
        await generate_account(interaction, PREMIUM_FILE)

    async def bulk_click(interaction):
        bulk_role_name = get_bulk_role_name()
        if not user_has_role(interaction.user, bulk_role_name):
            await interaction.response.send_message(f"You need the **{bulk_role_name}** role to use bulk generation.", ephemeral=True)
            return

        remaining = get_bulk_cooldown_remaining(interaction.user.id)
        if remaining > 0:
            await interaction.response.send_message(f"You are on bulk cooldown. Try again in **{format_remaining(remaining)}**.", ephemeral=True)
            return

        bulk_embed = discord.Embed(
            title="Bulk Generator",
            description="Use the dropdown below to enter how many accounts you want.",
            color=discord.Color.from_rgb(0, 20, 255),
        )
        bulk_embed.set_footer(text=f"Limit: {BULK_MIN}–{BULK_MAX} accounts per request")

        await interaction.response.send_message(
            embed=bulk_embed,
            view=BulkStartView(),
            ephemeral=True,
        )

    normal_btn.callback = normal_click
    premium_btn.callback = premium_click
    bulk_btn.callback = bulk_click

    view.add_item(normal_btn)
    view.add_item(shop_btn)
    view.add_item(premium_btn)
    view.add_item(bulk_btn)

    return embed, view


async def update_panel():
    global panel_message
    if panel_message is None:
        return
    embed, view = create_panel()
    try:
        await panel_message.edit(embed=embed, view=view)
    except discord.HTTPException:
        pass



class BulkAmountModal(Modal, title="Bulk Generator"):
    amount = TextInput(label="Choose how many accounts", placeholder=f"Enter {BULK_MIN}–{BULK_MAX}", min_length=1, max_length=3, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = int(self.amount.value.strip())
        except ValueError:
            await interaction.response.send_message("Please enter a valid whole number.", ephemeral=True)
            return

        if amount < BULK_MIN:
            await interaction.response.send_message(f"The minimum is **{BULK_MIN}** accounts per request.", ephemeral=True)
            return
        if amount > BULK_MAX:
            await interaction.response.send_message(f"The maximum is **{BULK_MAX}** accounts per request.", ephemeral=True)
            return

        confirm_embed = discord.Embed(
            title="Bulk Generator",
            description=f"You entered **{amount}** account(s).\n\nClick **Generate Accounts** below to confirm.",
            color=discord.Color.from_rgb(0, 20, 255),
        )
        confirm_embed.set_footer(text=f"Limit: {BULK_MIN}–{BULK_MAX} accounts per request")

        await interaction.response.send_message(
            embed=confirm_embed,
            view=BulkConfirmView(amount, interaction.user.id),
            ephemeral=True,
        )


class BulkOpenModalSelect(Select):
    def __init__(self):
        super().__init__(
            placeholder="Bulk Generator — choose how many accounts",
            min_values=1,
            max_values=1,
            options=[discord.SelectOption(label="Enter Account Amount", description=f"Type an amount between {BULK_MIN} and {BULK_MAX}", value="enter_amount", emoji="📝")]
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(BulkAmountModal())


class BulkStartView(View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(BulkOpenModalSelect())


class BulkConfirmView(View):
    def __init__(self, amount, owner_id):
        super().__init__(timeout=120)
        self.amount = amount
        self.owner_id = owner_id

    @discord.ui.button(label="Generate Accounts", style=discord.ButtonStyle.success, emoji="📦")
    async def generate_accounts_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("This confirmation is not for you.", ephemeral=True)
            return

        remaining = get_bulk_cooldown_remaining(interaction.user.id)
        if remaining > 0:
            await interaction.response.send_message(f"You are on bulk cooldown. Try again in **{format_remaining(remaining)}**.", ephemeral=True)
            return

        await interaction.response.edit_message(content=f"Generating **{self.amount}** account(s)...", embed=None, view=None)
        await bulk_generate_accounts(interaction, self.amount)



async def generate_account(interaction, file):
    await interaction.response.send_message("Generating your account...", ephemeral=True)
    await asyncio.sleep(2)

    stock = load(file)
    cooldowns = load(COOLDOWN_FILE)
    used = load(USED_FILE)

    user = str(interaction.user.id)
    now = time.time()
    premium = is_premium(interaction.user)
    cooldown = PREMIUM_COOLDOWN if premium else FREE_COOLDOWN

    if user in cooldowns:
        remaining = cooldown - (now - cooldowns[user])
        if remaining > 0:
            minutes = int(remaining // 60)
            seconds = int(remaining % 60)
            await interaction.edit_original_response(content=f"You are on cooldown. Try again in **{minutes}m {seconds}s**.")
            return

    if premium:
        if user not in used or not isinstance(used[user], list):
            used[user] = []
        used[user] = [t for t in used[user] if now - t < PREMIUM_LIMIT_WINDOW]
        if len(used[user]) >= PREMIUM_LIMIT:
            await interaction.edit_original_response(content="Premium members can generate up to **3 accounts every 12 hours**. You have reached that limit.")
            save(USED_FILE, used)
            return

    if len(stock) == 0:
        stock_type = "premium" if file == PREMIUM_FILE else "standard"
        await interaction.edit_original_response(content=f"No **{stock_type}** accounts are available right now. Check back later.")
        return

    key = random.choice(list(stock.keys()))
    acc = stock[key]
    del stock[key]
    save(file, stock)

    cooldowns[user] = now
    save(COOLDOWN_FILE, cooldowns)

    if premium:
        used.setdefault(user, []).append(now)
        save(USED_FILE, used)

    stock_type = "standard" if file == ALTS_FILE else "premium"

    try:
        await interaction.user.send(
            "Here is your account:\n\n"
            f"**Username:** `{acc['username']}`\n"
            f"**Password:** `{acc['password']}`"
        )
        await interaction.edit_original_response(content="Your account has been sent to your DMs.")
    except discord.Forbidden:
        stock[key] = acc
        save(file, stock)
        del cooldowns[user]
        save(COOLDOWN_FILE, cooldowns)
        if premium and user in used and used[user]:
            used[user].pop()
            save(USED_FILE, used)
        await interaction.edit_original_response(content="Could not DM you. Enable DMs and try again.\nNo account was taken from stock.")
        return

    log_generate(interaction, stock_type)

    await update_panel()



@bot.tree.command(name="panel", description="Post the account generator panel")
async def panel(interaction: discord.Interaction):
    global panel_message
    embed, view = create_panel()
    panel_message = await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message("Panel posted successfully.", ephemeral=True)


@bot.tree.command(name="stock", description="Check current account stock")
async def stock(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"Standard stock: **{len(load(ALTS_FILE))}**\n"
        f"Premium stock: **{len(load(PREMIUM_FILE))}**\n"
        f"Bulk stock: **{len(load(BULK_FILE))}**",
        ephemeral=True,
    )



@bot.tree.command(name="logs", description="View generation logs (owner only)")
async def logs(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Administrator only.", ephemeral=True)
        return

    await interaction.response.send_message(
        "Select what type of logs you want to see:",
        view=LogSelectorView(),
        ephemeral=True
    )


class LogSelectorView(View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(LogSelect())

    async def on_timeout(self):
        try:
            await self.message.edit(content="Log view timed out.")
        except:
            pass


class LogSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Standard", description="Standard account generation logs", value="standard"),
            discord.SelectOption(label="Premium", description="Premium account generation logs", value="premium"),
            discord.SelectOption(label="Bulk", description="Bulk account generation logs", value="bulk"),
        ]
        super().__init__(placeholder="Choose log type...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        log_type = self.values[0]

        logs = get_logs()
        if "logs" not in logs or not logs["logs"]:
            await interaction.followup.send("No logs recorded yet.", ephemeral=True)
            return

        filtered = [log for log in logs["logs"] if log["type"] == log_type]
        if not filtered:
            await interaction.followup.send(f"No {log_type} logs found.", ephemeral=True)
            return

        paginator = get_log_paginator(filtered)

        await interaction.followup.send(f"**{log_type.title()} Logs** ({len(filtered)} entries)\nPage 1/({len(paginator.pages)})", ephemeral=True)

        for i, page in enumerate(paginator.pages):
            if i == 0:
                await interaction.followup.send(page, ephemeral=True)
            else:
                await interaction.followup.send(page, ephemeral=True)



@bot.tree.command(name="view_accounts", description="View all accounts (owner only)")
async def view_accounts(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Administrator only.", ephemeral=True)
        return

    await interaction.response.send_message(
        "Select which accounts you want to view:",
        view=StockSelectorView(),
        ephemeral=True
    )


class StockSelectorView(View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(StockSelect())

    async def on_timeout(self):
        try:
            await self.message.edit(content="Stock view timed out.")
        except:
            pass


class StockSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Standard Alts", description="View all standard accounts", value="standard"),
            discord.SelectOption(label="Premium", description="View premium accounts", value="premium"),
            discord.SelectOption(label="Bulk", description="View bulk accounts", value="bulk"),
        ]
        super().__init__(placeholder="Choose stock type...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        stock_type = self.values[0]

        if stock_type == "standard":
            stock_data = load(ALTS_FILE)
        elif stock_type == "premium":
            stock_data = load(PREMIUM_FILE)
        elif stock_type == "bulk":
            stock_data = load(BULK_FILE)

        if not stock_data:
            await interaction.followup.send(f"No {stock_type} accounts found.", ephemeral=True)
            return

        sorted_keys = sorted(stock_data.keys(), key=lambda k: (len(str(stock_data[k]["username"])) + len(str(stock_data[k]["password"])), -k))

        fields = []
        current = []
        last_len = len(str(stock_data[sorted_keys[0]]["username"])) + len(str(stock_data[sorted_keys[0]]["password"]))

        for key in sorted_keys:
            acc = stock_data[key]
            length = len(str(acc["username"])) + len(str(acc["password"]))
            line = f"`{key}` • `{acc['username']}`:`{acc['password']}`"
            if length == last_len:
                current.append(line)
            else:
                if current:
                    fields.append(("Duplicates (" + str(last_len) + " chars):", "\n".join(current)))
                current = [line]
                last_len = length
        if current:
            fields.append(("Duplicates (" + str(last_len) + " chars):", "\n".join(current)))

        chunks = []
        for name, value in fields:
            if len(chunks) == 0 or len("\n".join(chunks) + "\n" + value) > 4000:
                chunks.append("")
            chunks[-1] += "\n" + value if chunks[-1] else value
            if len(chunks[-1]) > 1024:
                chunks.append("\n" + value)

        paginator = discord.Paginator(max_size=4096, page_length=4000)
        for chunk in chunks:
            paginator.add_line(chunk)

        await interaction.followup.send("Loading stock pages...", ephemeral=True)

        for i, page in enumerate(paginator.pages):
            if i == 0:
                await interaction.followup.send(page, ephemeral=True)
            else:
                await interaction.followup.send(page, ephemeral=True)



@bot.tree.command(name="webhook", description="Configure Discord webhook for live logs (owner only)")
async def webhook(interaction: discord.Interaction, webhook: discord.Webhook):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Administrator only.", ephemeral=True)
        return

    global WEBHOOK_URL, WEBHOOK_CHANNEL_ID
    WEBHOOK_URL = webhook.url
    WEBHOOK_CHANNEL_ID = str(webhook.channel.id)

    save_webhook_config()

    await interaction.response.send_message(
        f"✅ Webhook set successfully!\n"
        f"Channel: {webhook.channel.mention}\n"
        f"Logs will now update in real-time when anyone uses the bot.",
        ephemeral=True
    )



@bot.tree.command(name="cooldown", description="Check a member's generation cooldown")
async def cooldown(interaction: discord.Interaction, member: discord.Member):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Administrator only.", ephemeral=True)
        return

    await interaction.response.send_message("Checking cooldown...", ephemeral=True)

    cooldowns = load(COOLDOWN_FILE)
    user_id = str(member.id)
    lines = []

    if user_id in cooldowns:
        cd_time = PREMIUM_COOLDOWN if is_premium(member) else FREE_COOLDOWN
        remaining = cd_time - (time.time() - cooldowns[user_id])
        if remaining > 0:
            lines.append(f"Standard/Premium: **{format_remaining(remaining)}**")
        else:
            lines.append("Standard/Premium: **ready**")
    else:
        lines.append("Standard/Premium: **ready**")

    bulk_remaining = get_bulk_cooldown_remaining(member.id)
    if bulk_remaining > 0:
        lines.append(f"Bulk: **{format_remaining(bulk_remaining)}**")
    else:
        lines.append("Bulk: **ready**")

    await interaction.edit_original_response(
        content=f"{member.mention}\n" + "\n".join(lines)
    )


@bot.tree.command(name="resetcooldown", description="Reset a member's generation cooldown")
async def resetcooldown(interaction: discord.Interaction, member: discord.Member):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Administrator only.", ephemeral=True)
        return

    cooldowns = load(COOLDOWN_FILE)
    bulk_cooldowns = load(BULK_COOLDOWN_FILE)
    uid = str(member.id)

    if uid in cooldowns:
        del cooldowns[uid]
        save(COOLDOWN_FILE, cooldowns)
    if uid in bulk_cooldowns:
        del bulk_cooldowns[uid]
        save(BULK_COOLDOWN_FILE, bulk_cooldowns)

    await interaction.response.send_message(f"Cooldowns reset for {member.mention}.", ephemeral=True)


@bot.tree.command(name="giverole", description="Grant a member the Premium role")
async def giverole(interaction: discord.Interaction, member: discord.Member):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Administrator only.", ephemeral=True)
        return

    role = discord.utils.get(interaction.guild.roles, name=PREMIUM_ROLE)
    if role is None:
        await interaction.response.send_message("Premium role not found. Create a role named `Premium` first.", ephemeral=True)
        return

    await member.add_roles(role)
    await interaction.response.send_message(f"Granted **Premium** to {member.mention}.", ephemeral=True)


@bot.tree.command(name="removerole", description="Remove the Premium role from a member")
async def removerole(interaction: discord.Interaction, member: discord.Member):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Administrator only.", ephemeral=True)
        return

    role = discord.utils.get(interaction.guild.roles, name=PREMIUM_ROLE)
    if role is None:
        await interaction.response.send_message("Premium role not found.", ephemeral=True)
        return

    await member.remove_roles(role)
    await interaction.response.send_message(f"Removed **Premium** from {member.mention}.", ephemeral=True)


@bot.tree.command(name="setbulkrole", description="Set which role can use bulk generation")
async def setbulkrole(interaction: discord.Interaction, role: discord.Role):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Administrator only.", ephemeral=True)
        return

    config = load_config()
    config["bulk_role"] = role.name
    save_config(config)
    await update_panel()

    await interaction.response.send_message(f"Bulk generation is now restricted to members with **{role.name}**.", ephemeral=True)


@bot.tree.command(name="addphoto", description="Set or update the panel banner image")
async def addphoto(interaction: discord.Interaction, photo: discord.Attachment):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Administrator only.", ephemeral=True)
        return

    if not photo.content_type or not photo.content_type.startswith("image/"):
        await interaction.response.send_message("Please upload a valid image file (PNG, JPG, GIF, etc.).", ephemeral=True)
        return

    config = load_config()
    config["banner_url"] = photo.url
    save_config(config)
    await update_panel()

    await interaction.response.send_message("Panel banner updated. Run `/panel` again if the image does not appear on an older panel.", ephemeral=True)


@bot.tree.command(name="removephoto", description="Remove the panel banner image")
async def removephoto(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Administrator only.", ephemeral=True)
        return

    config = load_config()
    config["banner_url"] = None
    save_config(config)
    await update_panel()

    await interaction.response.send_message("Panel banner removed.", ephemeral=True)



@bot.tree.command(name="restock", description="Restock standard accounts from a text file")
async def restock(interaction: discord.Interaction, file: discord.Attachment):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Administrator only.", ephemeral=True)
        return

    await interaction.response.send_message("Processing restock file...", ephemeral=True)
    try:
        data = await file.read()
        text = data.decode("utf-8")
        lines = text.splitlines()
        stock = load(ALTS_FILE)
        added = 0
        duplicates = 0

        for line in lines:
            line = line.strip()
            if not line or ":" not in line:
                continue
            username, password = line.split(":", 1)
            username = username.strip()
            password = password.strip()

            existing = load(ALTS_FILE)
            is_duplicate = any(
                (acc["username"] == username and acc["password"] == password) or
                (acc["username"].lower() == username.lower() and acc["password"].lower() == password.lower())
                for acc in existing.values()
            )

            if not is_duplicate:
                stock[str(random.randint(100000, 999999))] = {"username": username, "password": password}
                added += 1
            else:
                duplicates += 1

        save(ALTS_FILE, stock)
        await update_panel()
        await interaction.edit_original_response(
            content=f"Added **{added}** standard account(s) to stock.\nDuplicates found: **{duplicates}**"
        )
    except Exception as exc:
        await interaction.edit_original_response(content=f"Restock failed: {exc}")


@bot.tree.command(name="restockpremium", description="Restock premium accounts from a text file")
async def restockpremium(interaction: discord.Interaction, file: discord.Attachment):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Administrator only.", ephemeral=True)
        return

    await interaction.response.send_message("Processing restock file...", ephemeral=True)

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
                "password": password.strip(),
            }
            added += 1

        save(PREMIUM_FILE, stock)
        await update_panel()
        await interaction.edit_original_response(
            content=f"Added **{added}** premium account(s) to stock."
        )
    except Exception as exc:
        await interaction.edit_original_response(content=f"Restock failed: {exc}")


@bot.tree.command(name="restockbulk", description="Restock bulk accounts from a text file")
async def restockbulk(interaction: discord.Interaction, file: discord.Attachment):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Administrator only.", ephemeral=True)
        return

    await interaction.response.send_message("Processing bulk restock file...", ephemeral=True)

    try:
        data = await file.read()
        text = data.decode("utf-8")
        lines = text.splitlines()
        stock = load(BULK_FILE)
        added = 0

        for line in lines:
            line = line.strip()
            if not line or ":" not in line:
                continue
            username, password = line.split(":", 1)
            stock[str(random.randint(100000, 999999))] = {
                "username": username.strip(),
                "password": password.strip(),
            }
            added += 1

        save(BULK_FILE, stock)
        await update_panel()
        await interaction.edit_original_response(
            content=f"Added **{added}** bulk account(s) to stock."
        )
    except Exception as exc:
        await interaction.edit_original_response(content=f"Restock failed: {exc}")


bot.run(TOKEN)
