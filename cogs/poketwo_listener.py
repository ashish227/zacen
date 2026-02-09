import discord
from discord.ext import commands

from utils.pokemon_api import identify_pokemon
from utils.database import (
    get_all_shiny_hunters,
    get_all_collectors,
    is_afk,
)

POKETWO_ID = 716390085896962058


class PoketwoListener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore ourselves
        if message.author.id == self.bot.user.id:
            return

        # Only listen to Pokétwo
        if message.author.id != POKETWO_ID:
            return

        if not message.embeds:
            return

        embed = message.embeds[0]

        if not embed.title:
            return

        if "A new wild pokémon has appeared!" not in embed.title:
            return

        if not embed.image or not embed.image.url:
            return

        image_url = embed.image.url
        print(f"[SPAWN] Image detected: {image_url}")

        pokemon = identify_pokemon(image_url)
        print(f"[API] Result: {pokemon}")

        if not pokemon:
            print("[HINT] No Pokémon identified, skipping reply")
            return

        # 🔑 normalize once
        pokemon = pokemon.strip().lower()

        # ---- DB LOOKUPS ----
        shiny_users = get_all_shiny_hunters(pokemon)
        collection_users = get_all_collectors(pokemon)

        ping_ids = set(shiny_users + collection_users)

        mentions = []
        for user_id in ping_ids:
            if not is_afk(user_id):
                mentions.append(f"<@{user_id}>")

        # ---- BUILD ONE MESSAGE ----
        content = pokemon

        if mentions:
            content += "\n" + " ".join(mentions)

        # ---- SEND ONCE ----
        try:
            await message.reply(content)
            print(f"[HINT] Sent: {content}")
        except Exception as e:
            print("[DISCORD ERROR]", e)


async def setup(bot: commands.Bot):
    await bot.add_cog(PoketwoListener(bot))
