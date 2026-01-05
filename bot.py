import discord
import json
import os
from moderation import behavior_score
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = discord.Client(intents=intents)

WARN_FILE = "warnings.json"

def load_warns():
    if not os.path.exists(WARN_FILE):
        return {}
    with open(WARN_FILE, "r") as f:
        return json.load(f)

def save_warns(data):
    with open(WARN_FILE, "w") as f:
        json.dump(data, f, indent=2)

def is_admin(member):
    return member.guild_permissions.administrator

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    warns = load_warns()
    uid = str(message.author.id)

    # ---- COMMANDS ----
    if message.content.startswith("!ping"):
        await message.channel.send("🏓 Pong")
        return

    if message.content.startswith("!warnings"):
        if not is_admin(message.author):
            return
        if not message.mentions:
            await message.channel.send("Mention a user.")
            return
        target = str(message.mentions[0].id)
        count = warns.get(target, 0)
        await message.channel.send(f"⚠️ Warnings: {count}/4")
        return

    if message.content.startswith("!resetwarnings"):
        if not is_admin(message.author):
            return
        if not message.mentions:
            return
        target = str(message.mentions[0].id)
        warns[target] = 0
        save_warns(warns)
        await message.channel.send("✅ Warnings reset.")
        return

    if message.content.startswith("!warn"):
        if not is_admin(message.author):
            return
        if not message.mentions:
            return
        target = str(message.mentions[0].id)
        warns[target] = warns.get(target, 0) + 1
        save_warns(warns)
        await message.channel.send("⚠️ Manual warning issued.")
        return

    if message.content.startswith("!unban"):
        if not is_admin(message.author):
            return
        parts = message.content.split()
        if len(parts) != 2:
            return
        user_id = int(parts[1])
        await message.guild.unban(discord.Object(id=user_id))
        await message.channel.send("✅ User unbanned.")
        return

    # ---- AUTO MODERATION ----
    score = behavior_score(message)

    if score >= 3:
        warns[uid] = warns.get(uid, 0) + 1
        save_warns(warns)

        await message.channel.send(
            f"{message.author.mention} ⚠️ Warning {warns[uid]}/4 (spam/abuse behavior)"
        )

        if warns[uid] == 3:
            await message.author.timeout(
                discord.utils.utcnow() + discord.timedelta(minutes=10),
                reason="Auto moderation"
            )

        if warns[uid] >= 4:
            await message.author.ban(reason="Auto moderation: 4 warnings")
            owner = message.guild.owner
            if owner:
                await owner.send(
                    f"🚨 {message.author} was banned after 4 warnings."
                )

bot.run(TOKEN)
