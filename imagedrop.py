"""
imagedrop.py — Manda fotos/gifs (ej. links de Pinterest) por DM al bot y los
reenvía al canal que elijas con botones. Puedes tener varios canales
nombrados (ej. "pfp", "banners", "aesthetic") y el bot te pregunta cuál usar
cada vez que le mandas links.

Comandos (dentro del servidor):
  ,addpostchannel <nombre> <#canal>    — agrega/actualiza un canal de destino (manage_guild)
  ,removepostchannel <nombre>          — elimina uno (manage_guild)
  ,postchannels                        — lista los canales configurados
  ,posters add/remove/list <@usuario>  — quién más puede usar esto por DM,
                                          además de quien tenga manage_guild (manage_guild)
  ,post <link1> <link2> ...            — postea hasta 5 links desde el server (te pregunta el canal)

Uso por DM:
  Mándale al bot un mensaje privado con hasta 5 links y te pregunta con
  botones a cuál canal mandarlos.
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
BUTTON_TIMEOUT = 120


def _extract_links(text: str) -> list[str]:
    return URL_RE.findall(text)[:MAX_LINKS]


def _is_allowed(member: discord.Member, config: dict) -> bool:
    if member.guild_permissions.manage_guild:
        return True
    return member.id in config.get("posters", [])


def _get_post_channels(config: dict) -> dict:
    """Compatibilidad: la versión vieja guardaba un solo 'post_channel_id'."""
    channels = dict(config.get("post_channels", {}))
    legacy_id = config.get("post_channel_id")
    if legacy_id and not channels:
        channels["general"] = legacy_id
    return channels


class ChannelPickView(discord.ui.View):
    """Botones para elegir a cuál canal mandar la tanda de links."""

    def __init__(self, author_id: int, links: list[str], options: list[tuple[str, discord.TextChannel]]):
        super().__init__(timeout=BUTTON_TIMEOUT)
        self.author_id = author_id
        self.links = links
        for label, channel in options[:25]:
            button = discord.ui.Button(label=label, style=discord.ButtonStyle.primary)
            button.callback = self._make_callback(channel)
            self.add_item(button)

    def _make_callback(self, channel: discord.TextChannel):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.author_id:
                return await interaction.response.send_message("Esto no es para ti.", ephemeral=True)

            try:
                await send_via_webhook(channel, content="\n".join(self.links))
            except (discord.Forbidden, discord.HTTPException) as e:
                log.warning(f"No se pudo postear en {channel}: {e}")
                return await interaction.response.edit_message(
                    content=f"❌ No pude mandar los links a {channel.mention}.", embed=None, view=None,
                )

            for item in self.children:
                item.disabled = True
            await interaction.response.edit_message(
                content=None,
                embed=discord.Embed(
                    description=f"✅ Mandé `{len(self.links)}` link(s) a {channel.mention}.",
                    color=0x57f287,
                ),
                view=self,
            )
            self.stop()

        return callback

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


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

        options = []
        multi_guild = len([g for g in self.bot.guilds if g.get_member(message.author.id)]) > 1
        for guild in self.bot.guilds:
            member = guild.get_member(message.author.id)
            if member is None:
                continue
            config = db.get_guild(guild.id)
            if not _is_allowed(member, config):
                continue
            for name, cid in _get_post_channels(config).items():
                channel = guild.get_channel(cid)
                if channel is None:
                    continue
                label = f"{name} — {guild.name}" if multi_guild else name
                options.append((label[:80], channel))

        if not options:
            return  # nadie configuró canales, o no tiene permiso — ignoramos en silencio

        view = ChannelPickView(message.author.id, links, options)
        await message.channel.send(
            embed=discord.Embed(
                description=f"¿A cuál canal mando estos `{len(links)}` link(s)?",
                color=0x2b2d31,
            ),
            view=view,
        )

    # ── Configuración de canales ─────────────────────────────────────────────

    @commands.command(name="addpostchannel")
    @commands.has_permissions(manage_guild=True)
    async def addpostchannel(self, ctx: commands.Context, name: str, channel: discord.TextChannel):
        name = name.lower().strip()
        config = db.get_guild(ctx.guild.id)
        channels = _get_post_channels(config)
        channels[name] = channel.id
        config["post_channels"] = channels
        config.pop("post_channel_id", None)  # ya migrado
        db.update_guild(ctx.guild.id, config)
        await ctx.send(embed=discord.Embed(
            description=f"✅ Canal `{name}` → {channel.mention}. Cuando mandes links, el bot te preguntará si quieres usar este.",
            color=0x57f287,
        ))

    @commands.command(name="removepostchannel")
    @commands.has_permissions(manage_guild=True)
    async def removepostchannel(self, ctx: commands.Context, name: str):
        name = name.lower().strip()
        config = db.get_guild(ctx.guild.id)
        channels = _get_post_channels(config)
        if name not in channels:
            return await ctx.send(embed=discord.Embed(description=f"No existe un canal llamado `{name}`.", color=0xed4245))
        del channels[name]
        config["post_channels"] = channels
        db.update_guild(ctx.guild.id, config)
        await ctx.send(embed=discord.Embed(description=f"✅ Se eliminó `{name}`.", color=0x57f287))

    @commands.command(name="postchannels")
    async def postchannels(self, ctx: commands.Context):
        config = db.get_guild(ctx.guild.id)
        channels = _get_post_channels(config)
        if not channels:
            desc = "No hay canales configurados. Usa `,addpostchannel <nombre> #canal`."
        else:
            desc = "\n".join(f"`{name}` → <#{cid}>" for name, cid in channels.items())
        await ctx.send(embed=discord.Embed(title="Canales de destino", description=desc, color=0x2b2d31))

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
            description=f"✅ {member.mention} ahora puede mandar links por DM.",
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

        channels = _get_post_channels(config)
        if not channels:
            return await ctx.send(embed=discord.Embed(
                description="Primero agrega al menos un canal con `,addpostchannel <nombre> #canal`.",
                color=0xed4245,
            ))

        links = _extract_links(links_text)
        if not links:
            return await ctx.send(embed=discord.Embed(description="No detecté ningún link ahí.", color=0xed4245))

        options = []
        for name, cid in channels.items():
            channel = ctx.guild.get_channel(cid)
            if channel:
                options.append((name, channel))

        view = ChannelPickView(ctx.author.id, links, options)
        await ctx.send(
            embed=discord.Embed(description=f"¿A cuál canal mando estos `{len(links)}` link(s)?", color=0x2b2d31),
            view=view,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(ImageDrop(bot))
