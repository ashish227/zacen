"""
cogs/help.py

.help — interactive help with category buttons, one page per category.
"""

import discord
from discord.ext import commands
from discord import app_commands

# ------------------------------------------------------------------ #
#  Help content — edit this to update the manual
# ------------------------------------------------------------------ #

CATEGORIES = [
    {
        "label": "🎯 Hunting",
        "title": "🎯 Shiny Hunting",
        "color": discord.Color.gold(),
        "fields": [
            (".sh <pokemon>",       "Set your active shiny hunt.\nIf you already have one, shows a confirm prompt to switch."),
            (".sh",                 "View your current shiny hunt."),
            (".sh clear",           "Stop your current shiny hunt."),
            (".sh remove",          "Same as `.sh clear`."),
        ],
    },
    {
        "label": "📦 Collection",
        "title": "📦 Collection",
        "color": discord.Color.blue(),
        "fields": [
            (".cl add <pkm1, pkm2, ...>",    "Add one or more Pokémon to your collection list.\nInvalid names are rejected with a pretty summary."),
            (".cl remove <pkm1, pkm2, ...>", "Remove one or more Pokémon from your collection."),
            (".cl list",                     "View your full collection list with total count."),
            (".cl clear",                    "Wipe your entire collection (requires confirmation)."),
            (".cl",                          "Same as `.cl list`."),
        ],
    },
    {
        "label": "⚙️ Settings",
        "title": "⚙️ Ping Settings",
        "color": discord.Color.blurple(),
        "fields": [
            (".afk",              "Open the ping control panel.\nToggle ✨ Shiny, 📦 Collection, 🏷️ Role Pings, and 💤 AFK individually.\n**AFK ON = master off switch, disables all pings regardless of other toggles.**"),
            (".shiny on/off",     "Shortcut to toggle shiny hunt pings on or off."),
            (".cltoggle on/off",  "Shortcut to toggle collection pings on or off."),
        ],
    },
    {
        "label": "🏷️ Global Pings",
        "title": "🏷️ Global Role Pings",
        "color": discord.Color.purple(),
        "fields": [
            (".gp @role <pkm1, pkm2, ...>",        "Register a role to be pinged when those Pokémon spawn.\nAlso works as `.gp add @role <pokemon>`."),
            (".gp remove @role <pkm1, pkm2, ...>", "Remove specific Pokémon from a role's ping list."),
            (".gp clear @role",                    "Wipe all Pokémon pings for a role (requires confirmation)."),
            (".gp list @role",                     "Show all Pokémon registered for a specific role."),
            (".gp list",                           "Show all role pings registered in this server."),
        ],
    },
    {
        "label": "🔧 Admin",
        "title": "🔧 Admin Commands",
        "color": discord.Color.red(),
        "fields": [
            (".pings on/off",                "Toggle whether @mentions fire in this channel.\nHints always send regardless."),
            (".createchannels <start> <end>", "Create numbered text channels from <start> to <end>.\nAuto-grouped into categories of 50.\nExample: `.createchannels 1 100`"),
            (".deletechannels <start> <end>", "Delete numbered channels in the given range.\nRemoves empty categories automatically.\nExample: `.deletechannels 51 100`"),
        ],
    },
    {
        "label": "ℹ️ Info",
        "title": "ℹ️ Info",
        "color": discord.Color.green(),
        "fields": [
            (".info <pokemon>", "See who is shiny hunting and collecting a specific Pokémon.\nShows user mentions for hunters and collectors."),
        ],
    },
]


# ------------------------------------------------------------------ #
#  Help View
# ------------------------------------------------------------------ #

class HelpView(discord.ui.View):
    def __init__(self, author_id: int):
        super().__init__(timeout=120)
        self.author_id = author_id
        self.current = 0
        self._build_buttons()

    def _build_buttons(self):
        self.clear_items()
        for i, cat in enumerate(CATEGORIES):
            btn = discord.ui.Button(
                label=cat["label"],
                style=discord.ButtonStyle.primary if i == self.current else discord.ButtonStyle.secondary,
                row=i // 3,
                custom_id=str(i),
            )
            btn.callback = self._make_callback(i)
            self.add_item(btn)

    def _make_callback(self, index: int):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.author_id:
                await interaction.response.send_message("This isn't your help menu.", ephemeral=True)
                return
            self.current = index
            self._build_buttons()
            await interaction.response.edit_message(
                embed=self._make_embed(), view=self
            )
        return callback

    def _make_embed(self) -> discord.Embed:
        cat = CATEGORIES[self.current]
        embed = discord.Embed(
            title=cat["title"],
            color=cat["color"]
        )
        for name, value in cat["fields"]:
            embed.add_field(name=f"`{name}`", value=value, inline=False)
        embed.set_footer(text=f"Category {self.current + 1}/{len(CATEGORIES)} • expires in 120s")
        return embed

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


# ------------------------------------------------------------------ #
#  Cog
# ------------------------------------------------------------------ #

class Help(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="help", aliases=["h"])
    async def help_cmd(self, ctx: commands.Context):
        view = HelpView(ctx.author.id)
        await ctx.send(embed=view._make_embed(), view=view)

    @app_commands.command(name="help", description="Show bot commands and usage")
    async def help_slash(self, interaction: discord.Interaction):
        view = HelpView(interaction.user.id)
        await interaction.response.send_message(embed=view._make_embed(), view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))