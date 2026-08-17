"""
imagedrop.py — Manda fotos/gifs (ej. links de Pinterest) por DM al bot y los
reenvía automáticamente al canal configurado del servidor. También funciona
como comando dentro del server.

Comandos (dentro del servidor):
  ,setpostchannel #canal        — define a qué canal se reenvían los links (manage_guild)
  ,posters add/remove/list <@usuario>  — quién más puede usar esto por DM, además
                                          de quien tenga manage_guild (manage_guild)
  ,post <link1> <link2> ...     — postea hasta 5 links directamente desde el server

Uso por DM:
  Mándale al bot un mensaje privado con hasta 5 links (Pinterest, imágenes
  directas, gifs, lo que sea) y los reenvía al canal configurado. Si el bot
  está en varios servidores donde tienes permiso, los postea en todos.
"""

import discord
from discord.ext import commands
from config import db
from webhook_utils import send_via_webhook
import re
import logging

log = logging.getLogger("antinuke.imagedrop")

URL_RE = re.compile(r"https?://\S+")
MAX_LINKS = 5


def _extract_links(text: str) -> list[str]:
    return URL_RE.findall(text)[:MAX_LINKS]


def _is_allowed(member: discord.Member, config: dict) -> bool:
    if member.guild_permissions.manage_guild:
        return True
    return member.id in config.get("posters", [])


class ImageDrop(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── DM listener ──────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is not None:
            return  # solo nos interesan los DMs

        links = _extract_links(message.content)
        if not links:
            return

        posted_to = []
        for guild in self.bot.guilds:
            member = guild.get_member(message.author.id)
            if member is None:
                continue

            config = db.get_guild(guild.id)
            channel_id = config.get("post_channel_id")
            if not channel_id:
                continue
            if not _is_allowed(member, config):
                continue

            channel = guild.get_channel(channel_id)
            if not channel:
                continue

            try:
                await send_via_webhook(channel, content="\n".join(links))
                posted_to.append(f"**{guild.name}** → {channel.mention}")
            except (discord.Forbidden, discord.HTTPException) as e:
                log.warning(f"[{guild.name}] No se pudo postear el drop de imágenes: {e}")

        if posted_to:
            try:
                await message.channel.send(embed=discord.Embed(
                    description=f"✅ Mandé `{len(links)}` link(s) a:\n" + "\n".join(posted_to),
                    color=0x57f287,
                ))
            except (discord.Forbidden, discord.HTTPException):
                pass

    # ── Configuración ────────────────────────────────────────────────────────

    @commands.command(name="setpostchannel")
    @commands.has_permissions(manage_guild=True)
    async def setpostchannel(self, ctx: commands.Context, channel: discord.TextChannel):
        config = db.get_guild(ctx.guild.id)
        config["post_channel_id"] = channel.id
        db.update_guild(ctx.guild.id, config)
        await ctx.send(embed=discord.Embed(
            description=f"✅ A partir de ahora, los links que me mandes por DM (o con `,post`) se van a {channel.mention}.",
            color=0x57f287,
        ))

    @commands.group(name="posters", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def posters(self, ctx: commands.Context):
        config = db.get_guild(ctx.guild.id)
        ids = config.get("posters", [])
        if not ids:
            desc = "Nadie más tiene acceso — solo quienes ya tienen `Gestionar Servidor`."
        else:
            desc = "\n".join(f"<@{uid}>" for uid in ids)
        await ctx.send(embed=discord.Embed(title="Posters autorizados", description=desc, color=0x2b2d31))

    @posters.command(name="add")
    @commands.has_permissions(manage_guild=True)
    async def posters_add(self, ctx: commands.Context, member: discord.Member):
        config = db.get_guild(ctx.guild.id)
        ids = config.get("posters", [])
        if member.id in ids:
            return await ctx.send(embed=discord.Embed(description=f"{member.mention} ya tenía acceso.", color=0x2b2d31))
        ids.append(member.id)
        config["posters"] = ids
        db.update_guild(ctx.guild.id, config)
        await ctx.send(embed=discord.Embed(
            description=f"✅ {member.mention} ahora puede mandar links por DM y se postearán en el canal configurado.",
            color=0x57f287,
        ))

    @posters.command(name="remove")
    @commands.has_permissions(manage_guild=True)
    async def posters_remove(self, ctx: commands.Context, member: discord.Member):
        config = db.get_guild(ctx.guild.id)
        ids = config.get("posters", [])
        if member.id not in ids:
            return await ctx.send(embed=discord.Embed(description=f"{member.mention} no estaba en la lista.", color=0xed4245))
        ids.remove(member.id)
        config["posters"] = ids
        db.update_guild(ctx.guild.id, config)
        await ctx.send(embed=discord.Embed(description=f"✅ Se quitó el acceso de {member.mention}.", color=0x57f287))

    # ── Comando directo desde el server ─────────────────────────────────────

    @commands.command(name="post")
    async def post(self, ctx: commands.Context, *, links_text: str):
        config = db.get_guild(ctx.guild.id)
        if not _is_allowed(ctx.author, config):
            return await ctx.send(embed=discord.Embed(
                description="No tienes permiso para usar esto (necesitas `Gestionar Servidor` o estar en `,posters`).",
                color=0xed4245,
            ))

        channel_id = config.get("post_channel_id")
        if not channel_id:
            return await ctx.send(embed=discord.Embed(
                description="Primero define el canal con `,setpostchannel #canal`.",
                color=0xed4245,
            ))
        channel = ctx.guild.get_channel(channel_id)
        if not channel:
            return await ctx.send(embed=discord.Embed(description="El canal configurado ya no existe.", color=0xed4245))

        links = _extract_links(links_text)
        if not links:
            return await ctx.send(embed=discord.Embed(description="No detecté ningún link ahí.", color=0xed4245))

        await send_via_webhook(channel, content="\n".join(links))
        await ctx.send(embed=discord.Embed(
            description=f"✅ Mandé `{len(links)}` link(s) a {channel.mention}.",
            color=0x57f287,
        ))


async def setup(bot: commands.Bot):
    await bot.add_cog(ImageDrop(bot))
