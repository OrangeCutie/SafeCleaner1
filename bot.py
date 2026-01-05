import discord
from discord.ext import commands
import sqlite3, os, time, re
from openai import OpenAI

client_ai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

BOT_TOKEN = os.getenv("BOT_TOKEN")
WARN_LIMIT = 4

db = sqlite3.connect("database.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS warnings(
 user_id TEXT,
 guild_id TEXT,
 reason TEXT,
 content TEXT,
 timestamp INTEGER
)
""")
db.commit()

def normalize(text):
    return re.sub(r'[^a-z0-9]', '', text.lower())

async def ai_toxicity(text):
    response = client_ai.responses.create(
        model="gpt-4.1-mini",
        input=f"Is this message toxic, hateful, sexual, racist, or harassing? Answer YES or NO.\n{text}"
    )
    return "YES" in response.output_text.upper()

def is_admin(member):
    return member.guild_permissions.administrator or member == member.guild.owner

@bot.event
async def on_ready():
    print("SafeCleaner online")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    toxic = await ai_toxicity(message.content)
    if not toxic:
        return

    await message.delete()

    cur.execute(
        "INSERT INTO warnings VALUES (?,?,?,?,?)",
        (str(message.author.id), str(message.guild.id),
         "AI Toxicity", message.content, int(time.time()))
    )
    db.commit()

    cur.execute(
        "SELECT COUNT(*) FROM warnings WHERE user_id=? AND guild_id=?",
        (str(message.author.id), str(message.guild.id))
    )
    count = cur.fetchone()[0]

    try:
        await message.author.send(
            f"You were warned in **{message.guild.name}** ({count}/{WARN_LIMIT})\nReason: Toxic content"
        )
    except:
        pass

    if count >= WARN_LIMIT:
        await message.author.ban(reason="Auto moderation (4 warnings)")

@bot.command()
async def warn(ctx, member: discord.Member, *, reason):
    if not is_admin(ctx.author):
        return
    cur.execute(
        "INSERT INTO warnings VALUES (?,?,?,?,?)",
        (str(member.id), str(ctx.guild.id),
         reason, "Manual warn", int(time.time()))
    )
    db.commit()
    await ctx.send(f"{member.mention} manually warned.")

@bot.command()
async def warnings(ctx, member: discord.Member):
    if not is_admin(ctx.author):
        return
    cur.execute(
        "SELECT reason, content FROM warnings WHERE user_id=? AND guild_id=?",
        (str(member.id), str(ctx.guild.id))
    )
    data = cur.fetchall()
    if not data:
        await ctx.send("No warnings.")
        return
    text = "\n".join([f"- {r}: {c}" for r,c in data])
    await ctx.send(text)

@bot.command()
async def resetwarnings(ctx, member: discord.Member):
    if not is_admin(ctx.author):
        return
    cur.execute(
        "DELETE FROM warnings WHERE user_id=? AND guild_id=?",
        (str(member.id), str(ctx.guild.id))
    )
    db.commit()
    await ctx.send("Warnings reset.")

bot.run(BOT_TOKEN)
