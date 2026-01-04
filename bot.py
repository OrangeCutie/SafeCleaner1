import os
import discord
from discord.ext import commands
from better_profanity import profanity
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Discord bot setup
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# OpenAI setup
openai.api_key = OPENAI_API_KEY

# Profanity filter setup
profanity.load_censor_words()
custom_words = ["idiot", "nigga", "sh*t", "b*tch", "polishbadword1", "polishbadword2"] # expand as needed
profanity.add_censor_words(custom_words)

# Warnings storage
warnings = {}

# Events
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
        warnings[message.author.id] = warnings.get(message.author.id, 0) + 1
        await message.channel.send(f"{message.author.mention}, watch your language!")

    # AI response if bot mentioned
    if bot.user in message.mentions:
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": message.content}]
            )
            await message.channel.send(response['choices'][0]['message']['content'])
        except Exception as e:
            await message.channel.send(f"AI Error: {str(e)}")

    await bot.process_commands(message)

# Commands
@bot.command()
async def seewarnings(ctx, member: commands.MemberConverter):
    count = warnings.get(member.id, 0)
    await ctx.send(f"{member} has {count} warnings.")

@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, *, member_name):
    banned_users = await ctx.guild.bans()
    member_name, member_discriminator = member_name.split("#")

    for ban_entry in banned_users:
        user = ban_entry.user
        if (user.name, user.discriminator) == (member_name, member_discriminator):
            await ctx.guild.unban(user)
            await ctx.send(f"{user.mention} has been unbanned.")
            return
    await ctx.send(f"User {member_name} not found.")

# Run bot
bot.run(BOT_TOKEN)
