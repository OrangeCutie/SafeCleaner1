import discord
from discord.ext import commands
import os
import json
from datetime import datetime, timezone
import openai
from better_profanity import profanity

# Load environment variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

if BOT_TOKEN is None or OPENAI_API_KEY is None:
    raise ValueError("BOT_TOKEN or OPENAI_API_KEY is not set in environment variables.")

openai.api_key = OPENAI_API_KEY
profanity.load_censor_words()  # Load default bad words

intents = discord.Intents.default()
intents.members = True
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Load or create warnings.json
WARNINGS_FILE = "warnings.json"
if not os.path.exists(WARNINGS_FILE):
    with open(WARNINGS_FILE, "w") as f:
        json.dump({}, f)

def load_warnings():
    with open(WARNINGS_FILE, "r") as f:
        return json.load(f)

def save_warnings(warnings):
    with open(WARNINGS_FILE, "w") as f:
        json.dump(warnings, f, indent=4)

# ----- Commands -----
@bot.command(name="warn")
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, reason=None):
    warnings = load_warnings()
    user_id = str(member.id)

    if user_id not in warnings:
        warnings[user_id] = []

    warnings[user_id].append({
        "reason": reason if reason else "No reason provided",
        "moderator": ctx.author.name,
        "time": datetime.now(timezone.utc).isoformat()
    })

    save_warnings(warnings)
    await ctx.send(f"{member.mention} has been warned. Total warnings: {len(warnings[user_id])}")

@bot.command(name="seewarnings")
async def seewarnings(ctx, member: discord.Member):
    warnings = load_warnings()
    user_id = str(member.id)

    if user_id not in warnings or len(warnings[user_id]) == 0:
        await ctx.send(f"{member.mention} has no warnings.")
        return

    msg = f"Warnings for {member.mention}:\n"
    for i, w in enumerate(warnings[user_id], start=1):
        msg += f"{i}. {w['reason']} (by {w['moderator']} at {w['time']})\n"

    await ctx.send(msg)

@bot.command(name="unban")
@commands.has_permissions(ban_members=True)
async def unban(ctx, *, member_name):
    banned_users = await ctx.guild.bans()
    name, discrim = member_name.split("#")
    for ban_entry in banned_users:
        user = ban_entry.user
        if (user.name, user.discriminator) == (name, discrim):
            await ctx.guild.unban(user)
            await ctx.send(f"{user.mention} has been unbanned.")
            return
    await ctx.send(f"No banned user found with name {member_name}.")

# ----- AI Reply & Profanity Handling -----
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Check for profanity
    if profanity.contains_profanity(message.content):
        warnings = load_warnings()
        user_id = str(message.author.id)

        if user_id not in warnings:
            warnings[user_id] = []

        warnings[user_id].append({
            "reason": "Used inappropriate language",
            "moderator": bot.user.name,
            "time": datetime.now(timezone.utc).isoformat()
        })

        save_warnings(warnings)
        try:
            await message.delete()
            await message.channel.send(f"{message.author.mention}, inappropriate language is not allowed. Warning added.")
        except discord.errors.Forbidden:
            await message.channel.send(f"{message.author.mention}, I cannot delete messages. But warning is recorded.")

    # Handle AI ping
    if bot.user in message.mentions:
        prompt = message.content.replace(f"<@{bot.user.id}>", "").strip()
        if prompt:
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=150
                )
                reply = response.choices[0].message.content
                await message.reply(reply)
            except Exception as e:
                await message.reply(f"AI error: {str(e)}")

    await bot.process_commands(message)

# ----- Error Handling -----
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(f"You don't have permission to run this command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing arguments. Usage: {ctx.command}")
    else:
        await ctx.send(f"An error occurred: {error}")

# ----- Ready Event -----
@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}!")

# Run the bot
bot.run(BOT_TOKEN)
