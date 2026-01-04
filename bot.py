import discord
from discord.ext import commands
import os, json, re
from datetime import datetime
from better_profanity import profanity
from dotenv import load_dotenv
import openai
import asyncio

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_KEY

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

WARN_LIMIT = 4
DATA_FILE = "warnings.json"
LOG_DIR = "logs"
FILTER_DIR = "filter"

os.makedirs(LOG_DIR, exist_ok=True)

# ---------- LOAD FILTERS ----------
profanity.load_censor_words()
extra_words = []

for file in os.listdir(FILTER_DIR):
    if file.endswith(".txt"):
        with open(os.path.join(FILTER_DIR, file), encoding="utf-8") as f:
            extra_words.extend([w.strip() for w in f if w.strip()])

profanity.add_censor_words(extra_words)

# ---------- HELPERS ----------
def save_warnings(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_warnings():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE) as f:
        return json.load(f)

def normalize(text):
    return re.sub(r"[^a-zA-Z0-9]", "", text.lower())

# ---------- EVENTS ----------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = normalize(message.content)

    if profanity.contains_profanity(content):
        try:
            await message.delete()
        except:
            return

        data = load_warnings()
        uid = str(message.author.id)
        data.setdefault(uid, 0)
        data[uid] += 1
        save_warnings(data)

        log_file = f"{LOG_DIR}/{datetime.utcnow().date()}.txt"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{message.author} | Warn {data[uid]} | {message.content}\n")

        await message.channel.send(
            f"{message.author.mention} ⚠ Warning {data[uid]}/{WARN_LIMIT}"
        )

        if data[uid] >= WARN_LIMIT:
            try:
                await message.author.ban(reason="Too many warnings")
                await message.guild.owner.send(
                    f"🚫 {message.author} was banned for reaching {WARN_LIMIT} warnings."
                )
            except:
                pass

        return

    await bot.process_commands(message)

# ---------- COMMANDS ----------
@bot.command()
@commands.has_permissions(manage_guild=True)
async def warnings(ctx, member: discord.Member):
    data = load_warnings()
    await ctx.send(f"{member.mention} has {data.get(str(member.id), 0)} warnings.")

@bot.command()
@commands.has_permissions(manage_guild=True)
async def clearwarnings(ctx, member: discord.Member):
    data = load_warnings()
    data[str(member.id)] = 0
    save_warnings(data)
    await ctx.send(f"Warnings cleared for {member.mention}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int):
    user = await bot.fetch_user(user_id)
    await ctx.guild.unban(user)
    await ctx.send(f"Unbanned {user}")

# ---------- AI CHAT ----------
@bot.command()
async def ask(ctx, *, question):
    await ctx.send("🤖 Thinking...")
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role":"user","content": question}],
            max_tokens=300,
            temperature=0.7
        )
        answer = response['choices'][0]['message']['content'].strip()
        await ctx.send(f"💡 {answer}")
    except Exception as e:
        await ctx.send(f"⚠ Error: {str(e)}")

# ---------- RUN ----------
bot.run(TOKEN)
