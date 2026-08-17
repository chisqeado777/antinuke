"""
embeds.py — Crear y editar embeds personalizados con el mismo motor de
sintaxis $v{} que usa ,welcome add (ver embed_scripting.py).

Comandos:
  ,createembed <código>              — crea y envía un embed en el canal actual
  ,editembed <link_mensaje> <código> — edita un embed que el bot mandó antes
"""

import discord
from discord.ext import commands
import re
from embed_scripting import parse_code, validate_code, build_message
from webhook_utils import edit_via_webhook

MESSAGE_LINK_RE = re.compile(r"channels/(\d+)/(\d+)/(\d+)")


class Embeds(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="createembed", aliases=["ce"])
    @commands.has_permissions(manage_guild=True)
    async def createembed(self, ctx: commands.Context, *, code: str):
        parsed = parse_code(code)
        warnings = validate_code(code)
        embed, content, view = build_message(parsed, member=ctx.author, guild=ctx.guild, channel=ctx.channel)

        if embed is None and not content:
            return await ctx.send(embed=discord.Embed(
                description="No se detectó ningún campo válido. Usa `,help embeds` para ver la sintaxis.",
                color=0xed4245,
            ))

        kwargs = {}
        if content:
            kwargs["content"] = content
        if embed:
            kwargs["embed"] = embed
        if view:
            kwargs["view"] = view
        await ctx.send(**kwargs)

        if warnings:
            await ctx.send(embed=discord.Embed(
                title="⚠️ Revisa esto",
                description="\n".join(f"• {w}" for w in warnings),
                color=0xfee75c,
            ))

    @commands.command(name="editembed", aliases=["edite"])
    @commands.has_permissions(manage_guild=True)
    async def editembed(self, ctx: commands.Context, message_link: str, *, code: str):
        match = MESSAGE_LINK_RE.search(message_link)
        if not match:
            return await ctx.send(embed=discord.Embed(
                description="Ese no es un link de mensaje válido. Debe verse como "
                            "`https://discord.com/channels/.../.../...`",
                color=0xed4245,
            ))

        guild_id, channel_id, message_id = map(int, match.groups())
        if guild_id != ctx.guild.id:
            return await ctx.send(embed=discord.Embed(
                description="Ese mensaje no pertenece a este servidor.",
                color=0xed4245,
            ))

        channel = ctx.guild.get_channel(channel_id)
        if not channel:
            return await ctx.send(embed=discord.Embed(description="No encuentro ese canal.", color=0xed4245))

        parsed = parse_code(code)
        warnings = validate_code(code)
        embed, content, view = build_message(parsed, member=ctx.author, guild=ctx.guild, channel=channel)

        kwargs = {}
        if content is not None:
            kwargs["content"] = content
        if embed:
            kwargs["embed"] = embed
        if view:
            kwargs["view"] = view

        try:
            await edit_via_webhook(channel, message_id, **kwargs)
        except discord.NotFound:
            return await ctx.send(embed=discord.Embed(
                description="No pude editar ese mensaje — probablemente no fue enviado por este bot.",
                color=0xed4245,
            ))
        except discord.HTTPException as e:
            return await ctx.send(embed=discord.Embed(description=f"No se pudo editar: {e}", color=0xed4245))

        await ctx.send(embed=discord.Embed(description="Embed actualizado.", color=0x57f287))
        if warnings:
            await ctx.send(embed=discord.Embed(
                title="⚠️ Revisa esto",
                description="\n".join(f"• {w}" for w in warnings),
                color=0xfee75c,
            ))


async def setup(bot: commands.Bot):
    await bot.add_cog(Embeds(bot))
