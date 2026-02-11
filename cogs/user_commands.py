import discord
from discord.ext import commands
import sqlite3

from utils.database import (
    add_shiny,
    remove_shiny,
    get_shinies,
    add_collection,
    remove_collection,
    get_collections,
    get_all_shiny_hunters,
    get_all_collectors,
    set_shiny_enabled,
    set_collection_enabled,
)

MAX_MESSAGE_LEN = 1900


def chunk_text(text: str, limit: int = MAX_MESSAGE_LEN):
    chunks = []
    current = ""

    for part in text.split(", "):
        if len(current) + len(part) + 2 > limit:
            chunks.append(current)
            current = part
        else:
            current = part if not current else f"{current}, {part}"

    if current:
        chunks.append(current)

    return chunks


class UserCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ---------------- SHINY HUNT ----------------

    @commands.group(name="sh", aliases=["shinyhunt"], invoke_without_command=True)
    async def shiny_group(self, ctx: commands.Context):
        await self.shiny_list(ctx)

    @shiny_group.command(name="add")
    async def shiny_add(self, ctx: commands.Context, *, names: str):
        pokemon_list = [p.strip().lower() for p in names.split(",") if p.strip()]
        added, skipped = [], []

        for p in pokemon_list:
            try:
                add_shiny(ctx.author.id, p)
                added.append(p)
            except sqlite3.IntegrityError:
                skipped.append(p)

        if added:
            await ctx.send(f"✨ Added to shiny hunt:\n{', '.join(added)}")
        if skipped:
            await ctx.send(f"⚠️ Already in shiny hunt:\n{', '.join(skipped)}")

    @shiny_group.command(name="remove")
    async def shiny_remove(self, ctx: commands.Context, *, names: str):
        pokemon_list = [p.strip().lower() for p in names.split(",") if p.strip()]
        for p in pokemon_list:
            remove_shiny(ctx.author.id, p)

        await ctx.send(f"❌ Removed from shiny hunt:\n{', '.join(pokemon_list)}")

    @shiny_group.command(name="list")
    async def shiny_list(self, ctx: commands.Context):
        shinies = sorted(get_shinies(ctx.author.id))
        if not shinies:
            await ctx.send("You are not shiny hunting any Pokémon.")
            return

        await ctx.send("✨ **Your shiny hunts:**")
        for chunk in chunk_text(", ".join(shinies)):
            await ctx.send(chunk)

    # ---------------- COLLECTION ----------------

    @commands.group(name="cl", aliases=["collection"], invoke_without_command=True)
    async def collection_group(self, ctx: commands.Context):
        await self.collection_list(ctx)

    @collection_group.command(name="add")
    async def collection_add(self, ctx: commands.Context, *, names: str):
        pokemon_list = [p.strip().lower() for p in names.split(",") if p.strip()]
        added, skipped = [], []

        for p in pokemon_list:
            try:
                add_collection(ctx.author.id, p)
                added.append(p)
            except sqlite3.IntegrityError:
                skipped.append(p)

        if added:
            await ctx.send(f"📦 Added to collection:\n{', '.join(added)}")
        if skipped:
            await ctx.send(f"⚠️ Already in collection:\n{', '.join(skipped)}")

    @collection_group.command(name="remove")
    async def collection_remove(self, ctx: commands.Context, *, names: str):
        pokemon_list = [p.strip().lower() for p in names.split(",") if p.strip()]
        for p in pokemon_list:
            remove_collection(ctx.author.id, p)

        await ctx.send(f"❌ Removed from collection:\n{', '.join(pokemon_list)}")

    @collection_group.command(name="list")
    async def collection_list(self, ctx: commands.Context):
        collections = sorted(get_collections(ctx.author.id))
        if not collections:
            await ctx.send("Your collection list is empty.")
            return

        await ctx.send("📦 **Your collection list:**")
        for chunk in chunk_text(", ".join(collections)):
            await ctx.send(chunk)

    # ---------------- TOGGLES ----------------

    @commands.command(name="shiny")
    async def shiny_toggle(self, ctx: commands.Context, state: str):
        state = state.lower()
        if state not in ("on", "off"):
            await ctx.send("Usage: `.shiny on` or `.shiny off`")
            return

        set_shiny_enabled(ctx.author.id, state == "on")
        await ctx.send(f"✨ Shiny pings turned **{state.upper()}**")

    @commands.command(name="cltoggle")
    async def collection_toggle(self, ctx: commands.Context, state: str):
        state = state.lower()
        if state not in ("on", "off"):
            await ctx.send("Usage: `.cltoggle on` or `.cltoggle off`")
            return

        set_collection_enabled(ctx.author.id, state == "on")
        await ctx.send(f"📦 Collection pings turned **{state.upper()}**")

    # ---------------- INFO ----------------

    @commands.command(name="info")
    async def pokemon_info(self, ctx: commands.Context, *, name: str):
        pokemon = name.strip().lower()

        shiny = get_all_shiny_hunters(pokemon)
        collectors = get_all_collectors(pokemon)

        def fmt(ids):
            return "None" if not ids else " ".join(f"<@{uid}>" for uid in ids)

        embed = discord.Embed(
            title=f"{pokemon.title()}",
            color=discord.Color.blurple()
        )
        embed.add_field(name="✨ Shiny Hunters", value=fmt(shiny), inline=False)
        embed.add_field(name="📦 Collectors", value=fmt(collectors), inline=False)

        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(UserCommands(bot))
