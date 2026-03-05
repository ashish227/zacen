import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

from utils.database import init_db
from utils.pokemon_validator import validator

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix=".", intents=intents, help_command=None)

COGS = [
    "cogs.poketwo_listener",
    "cogs.user_commands",
    "cogs.help",
    "cogs.channel_manager",
]


@bot.event
async def on_ready():
    print(f"[BOT] Logged in as {bot.user} ({bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"[BOT] Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"[BOT] Slash sync failed: {e}")


async def main():
    async with bot:
        init_db()

        # Instant — no network, no background task
        validator.load()

        for cog in COGS:
            try:
                await bot.load_extension(cog)
                print(f"[COG] Loaded {cog}")
            except Exception as e:
                print(f"[COG] Failed to load {cog}: {e}")

        await bot.start(TOKEN)


asyncio.run(main())