"""
cogs/user_commands.py

Commands:
  .sh [pokemon]              — set/view shiny hunt (single, confirm on change)
  .sh clear / .sh remove     — stop shiny hunt
  .cl add/remove/list/clear  — collection management
  .afk                       — ping control panel (master off = all pings off)
  .shiny on/off              — shortcut toggle shiny pings
  .cltoggle on/off           — shortcut toggle collection pings
  .info <pokemon>            — see hunters/collectors
  .gp [add/remove/clear/list]— global role pings (admin)
  .pings on/off              — per-channel ping toggle (admin)

AFK behaviour:
  AFK ON  = master kill switch, disables ALL pings regardless of toggles
  AFK OFF = restore individual toggle control
  Individual toggles: .shiny / .cltoggle / role pings work independently
"""

import discord
from discord.ext import commands
from discord import app_commands

from utils.database import (
    get_shiny, set_shiny, clear_shiny, get_all_shiny_hunters,
    add_collection, remove_collection, clear_collections, get_collections, get_all_collectors,
    set_shiny_enabled, is_shiny_enabled,
    set_collection_enabled, is_collection_enabled,
    set_role_ping_enabled, is_role_ping_enabled,
    set_afk, is_afk,
    add_role_ping, remove_role_ping, clear_role_pings,
    get_role_ping_list, get_all_role_pings,
    set_pings_enabled,
)
from utils.pokemon_validator import validator

MAX_FIELD = 1000


# ------------------------------------------------------------------ #
#  Helpers
# ------------------------------------------------------------------ #

def paginate(items: list[str], limit: int = MAX_FIELD) -> list[str]:
    chunks, cur = [], ""
    for item in items:
        add = f", {item}" if cur else item
        if len(cur) + len(add) > limit:
            chunks.append(cur)
            cur = item
        else:
            cur += add
    if cur:
        chunks.append(cur)
    return chunks or ["None"]


def result_embed(
    title: str,
    added: list[str] = None,
    skipped: list[str] = None,
    removed: list[str] = None,
    invalid: list[str] = None,
    color: discord.Color = discord.Color.blurple(),
) -> discord.Embed:
    embed = discord.Embed(title=title, color=color)
    if added:
        for i, chunk in enumerate(paginate(added)):
            embed.add_field(name="✅ Added" if i == 0 else "✅ (cont.)", value=chunk, inline=False)
    if skipped:
        for i, chunk in enumerate(paginate(skipped)):
            embed.add_field(name="⚠️ Already registered" if i == 0 else "⚠️ (cont.)", value=chunk, inline=False)
    if removed:
        for i, chunk in enumerate(paginate(removed)):
            embed.add_field(name="❌ Removed" if i == 0 else "❌ (cont.)", value=chunk, inline=False)
    if invalid:
        for i, chunk in enumerate(paginate(invalid)):
            embed.add_field(name="🚫 Invalid Pokémon" if i == 0 else "🚫 (cont.)", value=chunk, inline=False)
    if not embed.fields:
        embed.description = "Nothing to show."
    return embed


# ------------------------------------------------------------------ #
#  Confirm View
# ------------------------------------------------------------------ #

class ConfirmView(discord.ui.View):
    def __init__(self, user_id: int, timeout: float = 30):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.confirmed: bool | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your prompt.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = False
        self.stop()
        await interaction.response.defer()

    async def on_timeout(self):
        self.confirmed = False
        for item in self.children:
            item.disabled = True


# ------------------------------------------------------------------ #
#  AFK / Ping Control Panel
# ------------------------------------------------------------------ #

class PingControlView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=120)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your panel.", ephemeral=True)
            return False
        return True

    def _make_embed(self, user_id: int) -> discord.Embed:
        def s(val: bool) -> str:
            return "🟢 ON" if val else "🔴 OFF"

        afk = is_afk(user_id)
        embed = discord.Embed(
            title="⚙️ Ping Settings",
            color=discord.Color.greyple() if afk else discord.Color.blurple()
        )
        embed.add_field(name="✨ Shiny Pings",     value=s(is_shiny_enabled(user_id)),      inline=True)
        embed.add_field(name="📦 Collection Pings", value=s(is_collection_enabled(user_id)), inline=True)
        embed.add_field(name="🏷️ Role Pings",       value=s(is_role_ping_enabled(user_id)),  inline=True)
        embed.add_field(
            name="💤 AFK Mode",
            value=f"{s(afk)}\n{'*(overrides all above)*' if afk else '*(master off switch)*'}",
            inline=False
        )
        embed.set_footer(text="AFK ON = all pings disabled regardless of toggles • expires 120s")
        return embed

    async def _toggle_and_update(self, interaction: discord.Interaction, toggle_fn, is_fn):
        current = is_fn(interaction.user.id)
        toggle_fn(interaction.user.id, not current)
        await interaction.response.edit_message(
            embed=self._make_embed(interaction.user.id), view=self
        )

    @discord.ui.button(label="✨ Shiny", style=discord.ButtonStyle.secondary, row=0)
    async def toggle_shiny(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._toggle_and_update(interaction, set_shiny_enabled, is_shiny_enabled)

    @discord.ui.button(label="📦 Collection", style=discord.ButtonStyle.secondary, row=0)
    async def toggle_collection(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._toggle_and_update(interaction, set_collection_enabled, is_collection_enabled)

    @discord.ui.button(label="🏷️ Role Pings", style=discord.ButtonStyle.secondary, row=0)
    async def toggle_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._toggle_and_update(interaction, set_role_ping_enabled, is_role_ping_enabled)

    @discord.ui.button(label="💤 AFK", style=discord.ButtonStyle.danger, row=1)
    async def toggle_afk(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._toggle_and_update(interaction, set_afk, is_afk)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


# ------------------------------------------------------------------ #
#  Cog
# ------------------------------------------------------------------ #

class UserCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================
    #  SHINY HUNT — single active hunt per user
    # ============================================================

    @commands.group(name="sh", aliases=["shinyhunt"], invoke_without_command=True)
    async def sh_group(self, ctx: commands.Context, *, pokemon: str = None):
        if pokemon:
            await self._sh_set(ctx, pokemon)
        else:
            await self._sh_view(ctx)

    async def _sh_view(self, ctx: commands.Context):
        current = get_shiny(ctx.author.id)
        embed = discord.Embed(title="✨ Your Shiny Hunt", color=discord.Color.gold())
        embed.description = (
            f"Currently hunting: **{current.title()}**" if current
            else "You are not currently shiny hunting."
        )
        await ctx.send(embed=embed)

    async def _sh_set(self, ctx: commands.Context, pokemon: str):
        if not validator.is_valid(pokemon):
            await ctx.send(embed=discord.Embed(
                description=f"🚫 `{pokemon}` is not a valid Pokémon.",
                color=discord.Color.red()
            ))
            return

        norm = validator.normalize(pokemon)
        current = get_shiny(ctx.author.id)

        if current == norm:
            await ctx.send(embed=discord.Embed(
                description=f"You're already hunting **{norm.title()}**!",
                color=discord.Color.gold()
            ))
            return

        if current:
            embed = discord.Embed(
                title="✨ Change Shiny Hunt?",
                description=f"**{current.title()}** → **{norm.title()}**",
                color=discord.Color.gold()
            )
            view = ConfirmView(ctx.author.id, timeout=30)
            msg = await ctx.send(embed=embed, view=view)
            await view.wait()

            for item in view.children:
                item.disabled = True

            if view.confirmed:
                set_shiny(ctx.author.id, norm)
                embed.description = f"✅ Shiny hunt changed: **{current.title()}** → **{norm.title()}**"
                embed.color = discord.Color.green()
            else:
                embed.description = f"❌ Cancelled. Still hunting **{current.title()}**."
                embed.color = discord.Color.red()

            await msg.edit(embed=embed, view=view)
        else:
            set_shiny(ctx.author.id, norm)
            await ctx.send(embed=discord.Embed(
                description=f"✨ Now shiny hunting **{norm.title()}**!",
                color=discord.Color.gold()
            ))

    @sh_group.command(name="clear")
    async def sh_clear(self, ctx: commands.Context):
        current = get_shiny(ctx.author.id)
        if not current:
            await ctx.send(embed=discord.Embed(
                description="You have no active shiny hunt.",
                color=discord.Color.red()
            ))
            return
        clear_shiny(ctx.author.id)
        await ctx.send(embed=discord.Embed(
            description=f"✅ Stopped hunting **{current.title()}**.",
            color=discord.Color.green()
        ))

    @sh_group.command(name="remove")
    async def sh_remove(self, ctx: commands.Context):
        await self.sh_clear(ctx)

    @app_commands.command(name="sh", description="Set or view your shiny hunt")
    @app_commands.describe(pokemon="Pokémon to hunt (leave empty to view current)")
    async def sh_slash(self, interaction: discord.Interaction, pokemon: str = None):
        ctx = await commands.Context.from_interaction(interaction)
        if pokemon:
            await self._sh_set(ctx, pokemon)
        else:
            await self._sh_view(ctx)

    # ============================================================
    #  COLLECTION
    # ============================================================

    @commands.group(name="cl", aliases=["collection"], invoke_without_command=True)
    async def cl_group(self, ctx: commands.Context):
        await self._cl_list(ctx)

    @cl_group.command(name="add")
    async def cl_add(self, ctx: commands.Context, *, names: str):
        raw = [p.strip() for p in names.split(",") if p.strip()]
        valid, invalid = validator.validate_bulk(raw)

        added, skipped = [], []
        for p in valid:
            try:
                add_collection(ctx.author.id, p)
                added.append(p.title())
            except Exception:
                skipped.append(p.title())

        await ctx.send(embed=result_embed(
            "📦 Collection — Add",
            added=added, skipped=skipped,
            invalid=[n.title() for n in invalid],
            color=discord.Color.blue()
        ))

    @cl_group.command(name="remove")
    async def cl_remove(self, ctx: commands.Context, *, names: str):
        raw = [p.strip() for p in names.split(",") if p.strip()]
        valid, invalid = validator.validate_bulk(raw)

        removed = []
        for p in valid:
            remove_collection(ctx.author.id, p)
            removed.append(p.title())

        await ctx.send(embed=result_embed(
            "📦 Collection — Remove",
            removed=removed,
            invalid=[n.title() for n in invalid],
            color=discord.Color.blue()
        ))

    @cl_group.command(name="clear")
    async def cl_clear(self, ctx: commands.Context):
        cols = get_collections(ctx.author.id)
        if not cols:
            await ctx.send(embed=discord.Embed(
                description="Your collection is already empty.",
                color=discord.Color.red()
            ))
            return

        embed = discord.Embed(
            title="📦 Clear Collection?",
            description=f"This will remove all **{len(cols)}** Pokémon from your collection.",
            color=discord.Color.orange()
        )
        view = ConfirmView(ctx.author.id, timeout=30)
        msg = await ctx.send(embed=embed, view=view)
        await view.wait()

        for item in view.children:
            item.disabled = True

        if view.confirmed:
            clear_collections(ctx.author.id)
            embed.description = f"✅ Cleared **{len(cols)}** Pokémon from your collection."
            embed.color = discord.Color.green()
        else:
            embed.description = "❌ Cancelled."
            embed.color = discord.Color.red()

        await msg.edit(embed=embed, view=view)

    @cl_group.command(name="list")
    async def cl_list(self, ctx: commands.Context):
        await self._cl_list(ctx)

    async def _cl_list(self, ctx: commands.Context):
        cols = sorted(get_collections(ctx.author.id))
        embed = discord.Embed(title="📦 Your Collection", color=discord.Color.blue())
        if not cols:
            embed.description = "Your collection is empty."
        else:
            for i, chunk in enumerate(paginate([c.title() for c in cols])):
                embed.add_field(name="Pokémon" if i == 0 else "​", value=chunk, inline=False)
            embed.set_footer(text=f"{len(cols)} Pokémon")
        await ctx.send(embed=embed)

    @app_commands.command(name="cl", description="View your collection list")
    async def cl_slash(self, interaction: discord.Interaction):
        ctx = await commands.Context.from_interaction(interaction)
        await self._cl_list(ctx)

    # ============================================================
    #  AFK CONTROL PANEL
    # ============================================================

    @commands.command(name="afk")
    async def afk_cmd(self, ctx: commands.Context):
        view = PingControlView(ctx.author.id)
        embed = view._make_embed(ctx.author.id)
        await ctx.send(embed=embed, view=view)

    @app_commands.command(name="afk", description="Open your ping settings control panel")
    async def afk_slash(self, interaction: discord.Interaction):
        view = PingControlView(interaction.user.id)
        embed = view._make_embed(interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # Shortcut toggles
    @commands.command(name="shiny")
    async def shiny_toggle(self, ctx: commands.Context, state: str):
        state = state.lower()
        if state not in ("on", "off"):
            await ctx.send("Usage: `.shiny on` or `.shiny off`")
            return
        set_shiny_enabled(ctx.author.id, state == "on")
        await ctx.send(embed=discord.Embed(
            description=f"✨ Shiny pings **{state.upper()}**",
            color=discord.Color.green() if state == "on" else discord.Color.red()
        ))

    @commands.command(name="cltoggle")
    async def cl_toggle(self, ctx: commands.Context, state: str):
        state = state.lower()
        if state not in ("on", "off"):
            await ctx.send("Usage: `.cltoggle on` or `.cltoggle off`")
            return
        set_collection_enabled(ctx.author.id, state == "on")
        await ctx.send(embed=discord.Embed(
            description=f"📦 Collection pings **{state.upper()}**",
            color=discord.Color.green() if state == "on" else discord.Color.red()
        ))

    # ============================================================
    #  INFO
    # ============================================================

    @commands.command(name="info")
    async def info_cmd(self, ctx: commands.Context, *, name: str):
        if not validator.is_valid(name):
            await ctx.send(embed=discord.Embed(
                description=f"🚫 `{name}` is not a valid Pokémon.",
                color=discord.Color.red()
            ))
            return
        norm = validator.normalize(name)
        shiny = get_all_shiny_hunters(norm)
        cols = get_all_collectors(norm)
        embed = discord.Embed(title=norm.title(), color=discord.Color.blurple())
        embed.add_field(
            name=f"✨ Shiny Hunters ({len(shiny)})",
            value=" ".join(f"<@{uid}>" for uid in shiny) or "None",
            inline=False
        )
        embed.add_field(
            name=f"📦 Collectors ({len(cols)})",
            value=" ".join(f"<@{uid}>" for uid in cols) or "None",
            inline=False
        )
        await ctx.send(embed=embed)

    @app_commands.command(name="info", description="See who is hunting or collecting a Pokémon")
    @app_commands.describe(pokemon="Pokémon name")
    async def info_slash(self, interaction: discord.Interaction, pokemon: str):
        ctx = await commands.Context.from_interaction(interaction)
        await self.info_cmd(ctx, name=pokemon)

    # ============================================================
    #  GLOBAL PINGS — .gp (admin only)
    # ============================================================

    @commands.group(name="gp", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def gp_group(self, ctx: commands.Context, role: discord.Role = None, *, names: str = None):
        if role and names:
            await self._gp_add(ctx, role, names)
        else:
            await ctx.send("Usage: `.gp @role pkm1, pkm2` or `.gp add/remove/list/clear`")

    async def _gp_add(self, ctx: commands.Context, role: discord.Role, names: str):
        raw = [p.strip() for p in names.split(",") if p.strip()]
        valid, invalid = validator.validate_bulk(raw)

        added, skipped = [], []
        for p in valid:
            try:
                add_role_ping(ctx.guild.id, role.id, p)
                added.append(p.title())
            except Exception:
                skipped.append(p.title())

        await ctx.send(embed=result_embed(
            f"🏷️ Global Pings — {role.name}",
            added=added, skipped=skipped,
            invalid=[n.title() for n in invalid],
            color=role.color or discord.Color.blurple()
        ))

    @gp_group.command(name="add")
    @commands.has_permissions(administrator=True)
    async def gp_add(self, ctx: commands.Context, role: discord.Role, *, names: str):
        await self._gp_add(ctx, role, names)

    @gp_group.command(name="remove")
    @commands.has_permissions(administrator=True)
    async def gp_remove(self, ctx: commands.Context, role: discord.Role, *, names: str):
        raw = [p.strip() for p in names.split(",") if p.strip()]
        valid, invalid = validator.validate_bulk(raw)

        removed = []
        for p in valid:
            remove_role_ping(ctx.guild.id, role.id, p)
            removed.append(p.title())

        await ctx.send(embed=result_embed(
            f"🏷️ Global Pings — {role.name} — Removed",
            removed=removed,
            invalid=[n.title() for n in invalid],
            color=discord.Color.red()
        ))

    @gp_group.command(name="clear")
    @commands.has_permissions(administrator=True)
    async def gp_clear(self, ctx: commands.Context, role: discord.Role):
        plist = get_role_ping_list(ctx.guild.id, role.id)
        if not plist:
            await ctx.send(embed=discord.Embed(
                description=f"{role.mention} has no pings registered.",
                color=discord.Color.red()
            ))
            return

        embed = discord.Embed(
            title=f"🏷️ Clear pings for {role.name}?",
            description=f"This will remove **{len(plist)}** Pokémon.",
            color=discord.Color.orange()
        )
        view = ConfirmView(ctx.author.id, timeout=30)
        msg = await ctx.send(embed=embed, view=view)
        await view.wait()

        for item in view.children:
            item.disabled = True

        if view.confirmed:
            clear_role_pings(ctx.guild.id, role.id)
            embed.description = f"✅ Cleared **{len(plist)}** Pokémon from {role.mention}."
            embed.color = discord.Color.green()
        else:
            embed.description = "❌ Cancelled."
            embed.color = discord.Color.red()

        await msg.edit(embed=embed, view=view)

    @gp_group.command(name="list")
    @commands.has_permissions(administrator=True)
    async def gp_list(self, ctx: commands.Context, role: discord.Role = None):
        if role:
            plist = sorted(get_role_ping_list(ctx.guild.id, role.id))
            embed = discord.Embed(
                title=f"🏷️ Global Pings — {role.name}",
                color=role.color or discord.Color.blurple()
            )
            if not plist:
                embed.description = "No Pokémon registered for this role."
            else:
                for i, chunk in enumerate(paginate([p.title() for p in plist])):
                    embed.add_field(name="Pokémon" if i == 0 else "​", value=chunk, inline=False)
                embed.set_footer(text=f"{len(plist)} Pokémon")
            await ctx.send(embed=embed)
        else:
            all_pings = get_all_role_pings(ctx.guild.id)
            if not all_pings:
                await ctx.send(embed=discord.Embed(
                    description="No global pings registered in this server.",
                    color=discord.Color.red()
                ))
                return

            grouped: dict[int, list[str]] = {}
            for role_id, pokemon in all_pings:
                grouped.setdefault(role_id, []).append(pokemon.title())

            embed = discord.Embed(title="🏷️ All Global Pings", color=discord.Color.blurple())
            for role_id, pokemon_list in grouped.items():
                role_obj = ctx.guild.get_role(role_id)
                role_name = role_obj.name if role_obj else f"Unknown ({role_id})"
                for i, chunk in enumerate(paginate(sorted(pokemon_list))):
                    embed.add_field(
                        name=role_name if i == 0 else "​",
                        value=chunk, inline=False
                    )
                    if len(embed.fields) >= 20:
                        await ctx.send(embed=embed)
                        embed = discord.Embed(title="🏷️ All Global Pings (cont.)", color=discord.Color.blurple())

            if embed.fields:
                await ctx.send(embed=embed)

    # ============================================================
    #  PINGS ON/OFF — per channel (admin)
    # ============================================================

    @commands.command(name="pings")
    @commands.has_permissions(administrator=True)
    async def pings_cmd(self, ctx: commands.Context, state: str):
        state = state.lower()
        if state not in ("on", "off"):
            await ctx.send("Usage: `.pings on` or `.pings off`")
            return
        set_pings_enabled(ctx.channel.id, state == "on")
        await ctx.send(embed=discord.Embed(
            description=f"🔔 Pings in {ctx.channel.mention} turned **{state.upper()}** (hints always send)",
            color=discord.Color.green() if state == "on" else discord.Color.red()
        ))

    @app_commands.command(name="pings", description="Toggle pings in this channel (hints always send)")
    @app_commands.describe(state="on or off")
    @app_commands.choices(state=[
        app_commands.Choice(name="on", value="on"),
        app_commands.Choice(name="off", value="off"),
    ])
    @app_commands.default_permissions(administrator=True)
    async def pings_slash(self, interaction: discord.Interaction, state: str):
        set_pings_enabled(interaction.channel_id, state == "on")
        await interaction.response.send_message(embed=discord.Embed(
            description=f"🔔 Pings turned **{state.upper()}** in this channel.",
            color=discord.Color.green() if state == "on" else discord.Color.red()
        ), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(UserCommands(bot))