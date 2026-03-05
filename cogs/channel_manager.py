"""
cogs/channel_manager.py

.createchannels <start> <end>  — create numbered channels in groups of 50
.deletechannels <start> <end>  — delete numbered channels, remove empty categories
"""

import discord
from discord.ext import commands


class ChannelManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def createchannels(self, ctx: commands.Context, start: int, end: int):
        if start < 1 or end < start or (end - start + 1) > 500:
            await ctx.send("❌ Invalid range. Max 500 channels at a time.")
            return

        guild = ctx.guild
        existing_categories = {c.name: c for c in guild.categories}
        existing_channels = {c.name for c in guild.text_channels}

        msg = await ctx.send(f"⏳ Creating channels {start}–{end}...")
        created = 0

        # Group into blocks of 50
        i = start
        while i <= end:
            block_start = ((i - 1) // 50) * 50 + 1
            block_end = block_start + 49
            category_name = f"{block_start}-{block_end}"

            if category_name in existing_categories:
                category = existing_categories[category_name]
            else:
                category = await guild.create_category(category_name)
                existing_categories[category_name] = category

            while i <= end and i <= block_end:
                if str(i) not in existing_channels:
                    await guild.create_text_channel(name=str(i), category=category)
                    existing_channels.add(str(i))
                    created += 1
                i += 1

        await msg.edit(content=f"✅ Done! Created **{created}** channels ({start}–{end}).")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def deletechannels(self, ctx: commands.Context, start: int, end: int):
        if start < 1 or end < start or (end - start + 1) > 500:
            await ctx.send("❌ Invalid range. Max 500 channels at a time.")
            return

        guild = ctx.guild
        channel_map = {c.name: c for c in guild.text_channels}

        msg = await ctx.send(f"⏳ Deleting channels {start}–{end}...")
        deleted = 0

        for i in range(start, end + 1):
            ch = channel_map.get(str(i))
            if ch:
                await ch.delete(reason=f"deletechannels {start}-{end}")
                deleted += 1

        # Remove empty categories that were in this range
        block_starts = set()
        for i in range(start, end + 1):
            block_starts.add(((i - 1) // 50) * 50 + 1)

        for block_start in block_starts:
            block_end = block_start + 49
            cat_name = f"{block_start}-{block_end}"
            for cat in guild.categories:
                if cat.name == cat_name and len(cat.channels) == 0:
                    await cat.delete(reason="Empty after deletechannels")

        await msg.edit(content=f"✅ Done! Deleted **{deleted}** channels ({start}–{end}).")


async def setup(bot):
    await bot.add_cog(ChannelManager(bot))