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
        if message.author.id == self.bot.user.id:
            return

        if message.author.id != POKETWO_ID:
            return

        if not message.embeds:
            return

        embed = message.embeds[0]

        if not embed.title:
            return

        title = embed.title.lower()

        if "wild" not in title:
            return

        if not embed.image or not embed.image.url:
            return

        image_url = embed.image.url
        print(f"[SPAWN] Image detected: {image_url}")

        pokemon = identify_pokemon(image_url)
        print(f"[API] Result: {pokemon}")

        if not pokemon:
            print("[HINT] No Pokémon identified, skipping")
            return

        try:
            await message.reply(pokemon)
            print(f"[HINT] Sent hint: {pokemon}")
        except Exception as e:
            print("[DISCORD ERROR]", e)
            return

        shiny_users = get_all_shiny_hunters(pokemon)
        collection_users = get_all_collectors(pokemon)

        ping_ids = set(shiny_users + collection_users)

        if not ping_ids:
            return

        mentions = []
        for user_id in ping_ids:
            if not is_afk(user_id):
                mentions.append(f"<@{user_id}>")

        if mentions:
            try:
                await message.channel.send(" ".join(mentions))
            except Exception as e:
                print("[PING ERROR]", e)


async def setup(bot: commands.Bot):
    await bot.add_cog(PoketwoListener(bot))
