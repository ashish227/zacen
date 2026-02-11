from discord.ext import commands
import discord


class ChannelManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def createchannels(self, ctx):
        guild = ctx.guild

        existing_categories = {c.name: c for c in guild.categories}
        existing_channels = {c.name for c in guild.text_channels}

        for block in range(4):
            start = block * 50 + 1
            end = start + 49
            category_name = f"{start}-{end}"

            if category_name in existing_categories:
                category = existing_categories[category_name]
            else:
                category = await guild.create_category(category_name)

            for i in range(start, end + 1):
                channel_name = str(i)
                if channel_name not in existing_channels:
                    await guild.create_text_channel(
                        name=channel_name, category=category
                    )

        await ctx.send("✅ Channels created or verified.")


def setup(bot):
    bot.add_cog(ChannelManager(bot))
