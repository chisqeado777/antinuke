"""
autoresponder.py — Respuestas automáticas a palabras/frases exactas,
con soporte para texto simple o embeds (mismo motor $v{} de embed_scripting.py).

Comandos:
  ,autoresponder add <trigger> | <respuesta o código de embed>
  ,autoresponder remove <trigger>
  ,autoresponder list
  ,autoresponder clear

El trigger debe coincidir EXACTO (sin importar mayúsculas/minúsculas) con el
mensaje completo — así se evita que se dispare por accidente en medio de una
conversación normal.
"""

import discord
from discord.ext import commands
from config import db
from embed_scripting import parse_code, build_message
import logging

log = logging.getLogger("antinuke.autoresponder")


def _get_autoresponders(guild_id: int) -> list:
    config = db.get_guild(guild_id)
    return config.get("autoresponders", [])


def _save_autoresponders(guild_id: int, entries: list):
    config = db.get_guild(guild_id)
    config["autoresponders"] = entries
    db.update_guild(guild_id, config)


class AutoResponder(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        config = db.get_guild(message.guild.id)
        prefix = config.get("prefix", ",")
        if message.content.startswith(prefix):
            return  # no interferir con comandos

        entries = config.get("autoresponders", [])
        if not entries:
            return

        content_lower = message.content.strip().lower()
        for entry in entries:
            if entry["trigger"].strip().lower() == content_lower:
                parsed = parse_code(entry["response"])
                # Si no hay ningún bloque $v{}, se trata como texto plano
                if not parsed.get("message") and not any(
                    parsed.get(k) for k in ("title", "description", "author", "footer", "thumbnail", "image", "color")
                ) and not parsed.get("fields") and not parsed.get("buttons"):
                    text = (
                        entry["response"]
                        .replace("{user.mention}", message.author.mention)
                        .replace("{user.tag}", str(message.author))
                        .replace("{guild.name}", message.guild.name)
                    )
                    await message.channel.send(text)
                    return

                embed, content, view = build_message(parsed, member=message.author, channel=message.channel)
                kwargs = {}
                if content:
                    kwargs["content"] = content
                if embed:
                    kwargs["embed"] = embed
                if view:
                    kwargs["view"] = view
                await message.channel.send(**kwargs)
                return

    @commands.group(name="autoresponder", aliases=["ar"], invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def autoresponder(self, ctx: commands.Context):
        await ctx.send(embed=discord.Embed(
            description=(
                "`,autoresponder add <trigger> | <respuesta>` — texto simple o código `{embed}$v{...}`\n"
                "`,autoresponder remove <trigger>`\n"
                "`,autoresponder list`\n"
                "`,autoresponder clear`"
            ),
            color=0x2b2d31,
        ))

    @autoresponder.command(name="add")
    @commands.has_permissions(manage_guild=True)
    async def autoresponder_add(self, ctx: commands.Context, *, args: str):
        if "|" not in args:
            return await ctx.send(embed=discord.Embed(
                description="Formato: `,autoresponder add <trigger> | <respuesta>`",
                color=0xed4245,
            ))
        trigger, _, response = args.partition("|")
        trigger = trigger.strip()
        response = response.strip()
        if not trigger or not response:
            return await ctx.send(embed=discord.Embed(
                description="Tanto el trigger como la respuesta son obligatorios.",
                color=0xed4245,
            ))

        entries = _get_autoresponders(ctx.guild.id)
        entries = [e for e in entries if e["trigger"].lower() != trigger.lower()]  # reemplaza si ya existía
        entries.append({"trigger": trigger, "response": response})
        _save_autoresponders(ctx.guild.id, entries)

        await ctx.send(embed=discord.Embed(
            description=f"Autoresponder agregado. Cuando alguien escriba exactamente `{trigger}`, respondo.",
            color=0x57f287,
        ))

    @autoresponder.command(name="remove")
    @commands.has_permissions(manage_guild=True)
    async def autoresponder_remove(self, ctx: commands.Context, *, trigger: str):
        entries = _get_autoresponders(ctx.guild.id)
        new_entries = [e for e in entries if e["trigger"].lower() != trigger.strip().lower()]
        if len(new_entries) == len(entries):
            return await ctx.send(embed=discord.Embed(
                description=f"No encontré un autoresponder con el trigger `{trigger}`.",
                color=0xed4245,
            ))
        _save_autoresponders(ctx.guild.id, new_entries)
        await ctx.send(embed=discord.Embed(description=f"Autoresponder `{trigger}` eliminado.", color=0xed4245))

    @autoresponder.command(name="list")
    @commands.has_permissions(manage_guild=True)
    async def autoresponder_list(self, ctx: commands.Context):
        entries = _get_autoresponders(ctx.guild.id)
        if not entries:
            return await ctx.send(embed=discord.Embed(description="No hay autoresponders configurados.", color=0x2b2d31))

        lines = [f"**{i}.** `{e['trigger']}`" for i, e in enumerate(entries, 1)]
        await ctx.send(embed=discord.Embed(
            title="Autoresponders",
            description="\n".join(lines),
            color=0x2b2d31,
        ))

    @autoresponder.command(name="clear")
    @commands.has_permissions(manage_guild=True)
    async def autoresponder_clear(self, ctx: commands.Context):
        _save_autoresponders(ctx.guild.id, [])
        await ctx.send(embed=discord.Embed(description="Todos los autoresponders eliminados.", color=0xed4245))


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoResponder(bot))
