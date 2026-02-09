from discord.ext import commands
from utils.pokemon_api import identify_pokemon

POKETWO_ID = 716390085896962058

class PoketwoListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.author or message.author.id != POKETWO_ID:
            return

        if not message.embeds:
            return

        embed = message.embeds[0]

        if (
            embed.title
            and "A new wild pokémon has appeared!" in embed.title
            and embed.image
            and embed.image.url
        ):
            pokemon = await identify_pokemon(embed.image.url)

            if not pokemon:
                return

            await message.reply(pokemon, mention_author=False)

def setup(bot):
    bot.add_cog(PoketwoListener(bot))
