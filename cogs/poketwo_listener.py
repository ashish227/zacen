import time
import discord
from discord.ext import commands

from utils.pokemon_api import identify_pokemon
from utils.database import (
    get_all_shiny_hunters,
    get_all_collectors,
    is_afk,
    is_shiny_enabled,
    is_collection_enabled,
)

POKETWO_ID = 716390085896962058
PROCESS_TTL = 600  # 10 minutes


class PoketwoListener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # image_url -> timestamp
        self.processed_images: dict[str, float] = {}
        self.processing_images: set[str] = set()

    def _cleanup_old(self):
        now = time.time()
        expired = [
            url for url, ts in self.processed_images.items()
            if now - ts > PROCESS_TTL
        ]
        for url in expired:
            del self.processed_images[url]

    async def process_spawn(self, message: discord.Message):
        self._cleanup_old()

        if not message.embeds:
            return

        for embed in message.embeds:
            if not embed.title:
                continue

            title = embed.title.lower()
            if "wild" not in title or "appeared" not in title:
                continue

            if not embed.image or not embed.image.url:
                continue

            image_url = embed.image.url

            if image_url in self.processed_images:
                continue

            if image_url in self.processing_images:
                continue

            self.processing_images.add(image_url)
            hint_sent = False

            try:
                print(f"[SPAWN] Image detected: {image_url}")

                pokemon = await identify_pokemon(image_url)
                if not pokemon:
                    print("[HINT] No Pokémon identified")
                    continue

                pokemon = pokemon.strip().lower()
                print(f"[API] Result: {pokemon}")

                shiny_users = get_all_shiny_hunters(pokemon)
                collection_users = get_all_collectors(pokemon)

                ping_ids = set()

                for uid in shiny_users:
                    if is_shiny_enabled(uid) and not is_afk(uid):
                        ping_ids.add(uid)

                for uid in collection_users:
                    if is_collection_enabled(uid) and not is_afk(uid):
                        ping_ids.add(uid)

                content = pokemon
                if ping_ids:
                    mentions = " ".join(f"<@{uid}>" for uid in ping_ids)
                    content += "\n" + mentions

                await message.reply(content)
                print(f"[HINT] Sent: {pokemon}")

                hint_sent = True

            except Exception as e:
                print("[PROCESS ERROR]", e)

            finally:
                self.processing_images.discard(image_url)
                if hint_sent:
                    self.processed_images[image_url] = time.time()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id != POKETWO_ID:
            return
        await self.process_spawn(message)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if after.author.id != POKETWO_ID:
            return
        await self.process_spawn(after)


async def setup(bot: commands.Bot):
    await bot.add_cog(PoketwoListener(bot))
