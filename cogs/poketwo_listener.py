"""
cogs/poketwo_listener.py

Listens for Pokétwo spawns, identifies via API, always hints (lowercase).
Pings format (only when there are hunters/collectors):
    pikachu
    shiny hunts: @user1 @user2
    collection pings: @user3 @role1
"""

import asyncio
import time
import discord
from discord.ext import commands

from utils.pokemon_api import identify_pokemon
from utils.database import (
    get_all_shiny_hunters,
    get_all_collectors,
    get_role_pings,
    is_afk,
    is_shiny_enabled,
    is_collection_enabled,
    is_pings_enabled,
)

POKETWO_ID = 716390085896962058
PROCESSED_TTL = 600
MAX_CONCURRENT = 20
API_RETRIES = 3
RETRY_DELAY = 1.0


class PoketwoListener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.processed: dict[tuple[int, int], float] = {}
        self.processing: set[tuple[int, int]] = set()
        self._sem = asyncio.Semaphore(MAX_CONCURRENT)

    def _cleanup(self):
        now = time.time()
        for k in [k for k, ts in self.processed.items() if now - ts > PROCESSED_TTL]:
            del self.processed[k]

    def _is_spawn(self, embed: discord.Embed) -> bool:
        if not embed.title:
            return False
        t = embed.title.lower()
        return "wild" in t and "appeared" in t

    def _get_image(self, embed: discord.Embed) -> str | None:
        return embed.image.url if embed.image and embed.image.url else None

    async def _identify_with_retry(self, image_url: str) -> str | None:
        for attempt in range(1, API_RETRIES + 1):
            result = await identify_pokemon(image_url)
            if result:
                return result
            if attempt < API_RETRIES:
                print(f"[RETRY] Attempt {attempt} failed, retrying in {RETRY_DELAY}s...")
                await asyncio.sleep(RETRY_DELAY)
        return None

    async def process_spawn(self, message: discord.Message):
        if not message.embeds:
            return

        spawn_embed = next((e for e in message.embeds if self._is_spawn(e)), None)
        if not spawn_embed:
            return

        image_url = self._get_image(spawn_embed)
        if not image_url:
            return

        key = (message.channel.id, message.id)
        self._cleanup()

        if key in self.processed or key in self.processing:
            return

        self.processing.add(key)

        try:
            async with self._sem:
                print(f"[SPAWN] ch={message.channel.id} msg={message.id}")

                pokemon = await self._identify_with_retry(image_url)

                if not pokemon:
                    print(f"[FAIL] Could not identify in ch={message.channel.id}")
                    await message.reply("❓")
                    return

                pokemon_lower = pokemon.strip().lower()
                print(f"[IDENTIFIED] {pokemon_lower}")

                # Always hint first line — always lowercase
                lines = [pokemon_lower]

                # Only add pings if channel allows it
                if is_pings_enabled(message.channel.id):
                    # Shiny hunters
                    shiny_mentions = [
                        f"<@{uid}>"
                        for uid in get_all_shiny_hunters(pokemon_lower)
                        if is_shiny_enabled(uid) and not is_afk(uid)
                    ]

                    # Collectors
                    collection_mentions = [
                        f"<@{uid}>"
                        for uid in get_all_collectors(pokemon_lower)
                        if is_collection_enabled(uid) and not is_afk(uid)
                    ]

                    # Role pings
                    if message.guild:
                        for rid in get_role_pings(message.guild.id, pokemon_lower):
                            collection_mentions.append(f"<@&{rid}>")

                    # Only add ping lines if there's actually someone to ping
                    if shiny_mentions:
                        lines.append(f"shiny hunts: {' '.join(shiny_mentions)}")
                    if collection_mentions:
                        lines.append(f"collection pings: {' '.join(collection_mentions)}")

                await message.reply("\n".join(lines))
                print(f"[HINT] '{pokemon_lower}' in ch={message.channel.id}")
                self.processed[key] = time.time()

        except Exception as e:
            print(f"[ERROR] process_spawn: {e}")
        finally:
            self.processing.discard(key)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id != POKETWO_ID:
            return
        asyncio.create_task(self.process_spawn(message))


async def setup(bot: commands.Bot):
    await bot.add_cog(PoketwoListener(bot))