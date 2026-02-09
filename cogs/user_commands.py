import discord
from discord.ext import commands

from utils.database import (
    add_shiny,
    remove_shiny,
    get_shinies,
    add_collection,
    remove_collection,
    get_collections,
)


class UserCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.group(name="sh", aliases=["shinyhunt"], invoke_without_command=True)
    async def shiny_group(self, ctx: commands.Context):
        shinies = get_shinies(ctx.author.id)
        if not shinies:
            await ctx.send("You are not shiny hunting any Pokémon.")
        else:
            await ctx.send(
                "**Your shiny hunts:**\n" + ", ".join(sorted(shinies))
            )

    @shiny_group.command(name="add")
    async def shiny_add(self, ctx: commands.Context, *, names: str):
        pokemon_list = [p.strip().lower() for p in names.split(",") if p.strip()]
        for p in pokemon_list:
            add_shiny(ctx.author.id, p)

        await ctx.send(
            f"Added to shiny hunt: {', '.join(pokemon_list)}"
        )

    @shiny_group.command(name="remove")
    async def shiny_remove(self, ctx: commands.Context, *, names: str):
        pokemon_list = [p.strip().lower() for p in names.split(",") if p.strip()]
        for p in pokemon_list:
            remove_shiny(ctx.author.id, p)

        await ctx.send(
            f"Removed from shiny hunt: {', '.join(pokemon_list)}"
        )

    @shiny_group.command(name="list")
    async def shiny_list(self, ctx: commands.Context):
        shinies = get_shinies(ctx.author.id)
        if not shinies:
            await ctx.send("You are not shiny hunting any Pokémon.")
        else:
            await ctx.send(
                "**Your shiny hunts:**\n" + ", ".join(sorted(shinies))
            )

    @commands.group(name="cl", aliases=["collection"], invoke_without_command=True)
    async def collection_group(self, ctx: commands.Context):
        collections = get_collections(ctx.author.id)
        if not collections:
            await ctx.send("Your collection list is empty.")
        else:
            await ctx.send(
                "**Your collection list:**\n" + ", ".join(sorted(collections))
            )

    @collection_group.command(name="add")
    async def collection_add(self, ctx: commands.Context, *, names: str):
        pokemon_list = [p.strip().lower() for p in names.split(",") if p.strip()]
        for p in pokemon_list:
            add_collection(ctx.author.id, p)

        await ctx.send(
            f"Added to collection: {', '.join(pokemon_list)}"
        )

    @collection_group.command(name="remove")
    async def collection_remove(self, ctx: commands.Context, *, names: str):
        pokemon_list = [p.strip().lower() for p in names.split(",") if p.strip()]
        for p in pokemon_list:
            remove_collection(ctx.author.id, p)

        await ctx.send(
            f"Removed from collection: {', '.join(pokemon_list)}"
        )

    @collection_group.command(name="list")
    async def collection_list(self, ctx: commands.Context):
        collections = get_collections(ctx.author.id)
        if not collections:
            await ctx.send("Your collection list is empty.")
        else:
            await ctx.send(
                "**Your collection list:**\n" + ", ".join(sorted(collections))
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(UserCommands(bot))
