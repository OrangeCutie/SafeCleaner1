import discord
from discord.ext import commands
from better_profanity import profanity
import os
import openai

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Load environment variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# Profanity setup
profanity.load_censor_words()  # can customize your list if needed

# Simple warnings system (memory for example)
warnings = {}

# --- Events ---
@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Profanity filter
    if profanity.contains_profanity(message.content):
        await message.delete()
        user_id = message.author.id
        warnings[user_id] = warnings.get(user_id, 0) + 1
        await message.channel.send(
            f"{message.author.mention}, watch your language! Warnings: {warnings[user_id]}"
        )
        return

    await bot.process_commands(message)

# --- Commands ---
@bot.command()
async def seewarnings(ctx, member: discord.Member):
    count = warnings.get(member.id, 0)
    await ctx.send(f"{member.display_name} has {count} warnings.")

@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, *, member_name):
    banned_users = await ctx.guild.bans()
    for ban_entry in banned_users:
        user = ban_entry.user
        if user.name == member_name:
            await ctx.guild.unban(user)
            await ctx.send(f"Unbanned {user.name}")
            return
    await ctx.send(f"User {member_name} not found.")

@bot.command()
async def ask(ctx, *, question):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role":"user", "content":question}]
    )
    answer = response.choices[0].message.content
    await ctx.send(answer)

# --- Run Bot ---
bot.run(DISCORD_TOKEN)
