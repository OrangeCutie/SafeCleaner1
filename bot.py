import discord
from discord.ext import commands
from better_profanity import profanity
import json
import re
import os
from datetime import datetime, date

BOT_TOKEN = os.environ.get("BOT_TOKEN")  # Railway environment variable
MAX_WARNINGS = 4

NSFW_KEYWORDS = ["condo", "erp", "nsfw", "lewd", "explicit", "cp"]
INVITE_REGEX = re.compile(r"(discord\.gg|discord\.com/invite)/[A-Za-z0-9]+")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

profanity.load_censor_words()
DATA_FILE = "warnings.json"
warnings = {}

def load_data():
    global warnings
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            warnings.update(json.load(f))

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(warnings, f, indent=2)

def log_warning(guild, member, reason, message_content, warning_count):
    os.makedirs("logs", exist_ok=True)
    today = date.today().isoformat()
    log_file = f"logs/{today}.txt"
    clean_content = message_content.replace("\n", " ")[:500]
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(
            f"[{datetime.utcnow().isoformat()} UTC]\n"
            f"Server: {guild.name} ({guild.id})\n"
            f"User: {member} ({member.id})\n"
            f"Warnings: {warning_count}/{MAX_WARNINGS}\n"
            f"Reason: {reason}\n"
            f"Message: {clean_content}\n"
            f"{'-'*40}\n"
        )

def add_warning(member, guild, reason, message_content):
    gid = str(guild.id)
    uid = str(member.id)
    warnings.setdefault(gid, {})
    warnings[gid].setdefault(uid, {"user": str(member), "count":0, "reasons":[]})

    warnings[gid][uid]["count"] += 1
    warnings[gid][uid]["reasons"].append({
        "reason": reason,
        "message": message_content,
        "time": datetime.utcnow().isoformat()
    })
    save_data()
    log_warning(guild, member, reason, message_content, warnings[gid][uid]["count"])
    return warnings[gid][uid]["count"]

@bot.event
async def on_ready():
    load_data()
    print(f"Bot logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot or not isinstance(message.author, discord.Member):
        return

    content = message.content.lower()
    reason = None

    if profanity.contains_profanity(content):
        reason = "Profanity / slur detected"

    for word in NSFW_KEYWORDS:
        if word in content:
            reason = "NSFW / condo-related keyword detected"

    if INVITE_REGEX.search(content):
        reason = "Suspicious Discord invite detected"

    if reason:
        count = add_warning(message.author, message.guild, reason, message.content)
        await message.delete()
        await message.channel.send(
            f"⚠️ {message.author.mention} warning **{count}/{MAX_WARNINGS}**: {reason}",
            delete_after=6
        )

        if count >= MAX_WARNINGS:
            owner = message.guild.owner
            if owner:
                try:
                    await owner.send(
                        f"🚨 AUTO-BAN ALERT\nServer: {message.guild.name}\n"
                        f"User: {message.author} ({message.author.id})\n"
                        f"Warnings: {count}/{MAX_WARNINGS}\nReason: Repeated violations"
                    )
                except:
                    pass
            await message.guild.ban(message.author, reason="Reached maximum warnings")

    await bot.process_commands(message)

@bot.command()
@commands.has_permissions(kick_members=True)
async def warnings_cmd(ctx, member: discord.Member):
    gid = str(ctx.guild.id)
    uid = str(member.id)
    if gid not in warnings or uid not in warnings[gid]:
        await ctx.send("User has no warnings.")
        return
    data = warnings[gid][uid]
    msg = f"⚠️ **{member}** — {data['count']} warnings\n"
    for r in data["reasons"]:
        msg += f"- {r['reason']} ({r['time']})\n"
    await ctx.send(msg)

@bot.command()
@commands.has_permissions(administrator=True)
async def export(ctx):
    gid = str(ctx.guild.id)
    with open(f"flagged_{gid}.txt", "w", encoding="utf-8") as f:
        if gid in warnings:
            for u in warnings[gid].values():
                f.write(f"{u['user']} — {u['count']} warnings\n")
                for r in u["reasons"]:
                    f.write(f"  - {r['reason']}\n")
                f.write("\n")
    await ctx.send("📄 Exported flagged users for this server.")

@bot.command()
@commands.has_permissions(administrator=True)
async def todaylog(ctx):
    today = date.today().isoformat()
    path = f"logs/{today}.txt"
    if not os.path.exists(path):
        await ctx.send("No logs for today.")
        return
    await ctx.send(file=discord.File(path))

bot.run(BOT_TOKEN)