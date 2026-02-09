from utils.database import init_db
import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix=".", intents=intents)


@bot.event
async def on_ready():
    init_db()
    print(f"Logged in as {bot.user}")


async def main():
    async with bot:
        await bot.load_extension("cogs.poketwo_listener")
        await bot.load_extension("cogs.user_commands")
        await bot.start(TOKEN)


asyncio.run(main())
