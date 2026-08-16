"""
activity_logs.py — Registra en tiempo real eventos de mensajes, miembros,
voz e invitaciones hacia sus canales de logs correspondientes (creados con
,setuplogs). No requiere configuración extra: en cuanto los canales de logs
existan, estos eventos empiezan a mandarse solos.

Nota sobre mensajes: Discord solo entrega el contenido de un mensaje
eliminado/editado si el bot ya lo tenía en caché (lo vio pasar mientras
estaba online). Mensajes de antes de que el bot arrancara no se pueden
recuperar — es una limitación de la API de Discord, no del bot.
"""

import discord
from discord.ext import commands
from logger import send_log
import logging

log = logging.getLogger("antinuke.activity_logs")


class ActivityLogs(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Mensajes ─────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        content = message.content or "*(sin texto — puede ser una imagen, embed o adjunto)*"
        if len(content) > 950:
            content = content[:950] + "..."
        await send_log(
            message.guild,
            action="delete",
            target=message.author,
            moderator=None,
            reason=f"Mensaje eliminado en {message.channel.mention}",
            module="Mensaje Eliminado",
            category="messages",
            extra_fields=[("Contenido", f"```{content}```", False)],
        )

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if not before.guild or before.author.bot or before.content == after.content:
            return
        antes = (before.content or "*vacío*")[:450]
        despues = (after.content or "*vacío*")[:450]
        await send_log(
            before.guild,
            action="edit",
            target=before.author,
            moderator=None,
            reason=f"Mensaje editado en {before.channel.mention}",
            module="Mensaje Editado",
            category="messages",
            extra_fields=[("Antes", f"```{antes}```", False), ("Después", f"```{despues}```", False)],
        )

    # ── Miembros ─────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await send_log(
            member.guild,
            action="join",
            target=member,
            moderator=None,
            reason="Un nuevo miembro se unió al servidor",
            module="Miembro Ingresó",
            category="members",
            extra_fields=[("Cuenta creada", discord.utils.format_dt(member.created_at, "R"), True)],
        )

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        await send_log(
            member.guild,
            action="leave",
            target=member,
            moderator=None,
            reason="Un miembro salió del servidor",
            module="Miembro Salió",
            category="members",
        )

    # ── Voz ──────────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if before.channel == after.channel:
            return
        if before.channel is None and after.channel is not None:
            reason = f"Se unió a {after.channel.mention}"
        elif before.channel is not None and after.channel is None:
            reason = f"Salió de {before.channel.mention}"
        else:
            reason = f"Se movió de {before.channel.mention} a {after.channel.mention}"
        await send_log(
            member.guild,
            action="voice",
            target=member,
            moderator=None,
            reason=reason,
            module="Actividad de Voz",
            category="voice",
        )

    # ── Invitaciones ─────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        await send_log(
            invite.guild,
            action="invite_create",
            target=invite.inviter,
            moderator=None,
            reason=f"Invitación creada: `{invite.code}` en {invite.channel.mention}",
            module="Invitación Creada",
            category="invites",
        )

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        await send_log(
            invite.guild,
            action="invite_delete",
            target=None,
            moderator=None,
            reason=f"Invitación eliminada: `{invite.code}`",
            module="Invitación Eliminada",
            category="invites",
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(ActivityLogs(bot))

import discord
from discord.ext import commands
import asyncio
import os
import logging
from config import db, DEFAULT_PREFIX
from webhook_utils import send_via_webhook

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger("antinuke")


class WebhookContext(commands.Context):
    """Context que reenvía ctx.send() a través del webhook del bot.
    En DMs no hay webhook posible, así que ahí se manda normal."""

    async def send(self, content=None, **kwargs):
        if self.guild is None:
            return await super().send(content, **kwargs)
        if content is not None:
            kwargs["content"] = content
        return await send_via_webhook(self.channel, **kwargs)


class AntiNukeBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(
            command_prefix=self.get_prefix,
            intents=intents,
            help_command=None,
            case_insensitive=True,
            owner_ids=self._load_owners(),
        )
        self.db = db

    def _load_owners(self):
        owners = os.getenv("OWNER_IDS", "")
        if not owners:
            return set()
        return set(int(x.strip()) for x in owners.split(",") if x.strip().isdigit())

    async def get_prefix(self, message):
        if not message.guild:
            return [","]
        guild_data = db.get_guild(message.guild.id)
        prefix = guild_data.get("prefix", DEFAULT_PREFIX)
        return commands.when_mentioned_or(prefix)(self, message)

    async def get_context(self, message, *, cls=WebhookContext):
        return await super().get_context(message, cls=cls)

    async def setup_hook(self):
        cogs = [
            "backup",
            "antinuke",
            "whitelist",
            "settings",
            "vc_tracker",
            "welcome",
            "invites",
            "giveaway",
            "help",
            "lockdown",
            "unban",
            "voice",
            "autosetup",
            "activity_logs",
        ]
        for cog in cogs:
            try:
                await self.load_extension(cog)
                log.info(f"Loaded cog: {cog}")
            except Exception as e:
                import traceback
                log.error(f"Failed to load {cog}:\n{traceback.format_exc()}")

    async def on_message(self, message):
        if message.author.bot:
            return

        if message.guild and message.content.strip() in (
            f"<@{self.user.id}>", f"<@!{self.user.id}>"
        ):
            guild_data = db.get_guild(message.guild.id)
            prefix = guild_data.get("prefix", DEFAULT_PREFIX)
            embed = discord.Embed(
                description=f"Mi prefijo en este servidor es `{prefix}`\n"
                            f"Usa `{prefix}help` para ver todos los comandos.",
                color=0x2b2d31,
            )
            if message.guild.icon:
                embed.set_thumbnail(url=message.guild.icon.url)
            await message.channel.send(embed=embed)  # respuesta normal, sin webhook
            return

        await self.process_commands(message)

    async def on_ready(self):
        log.info(f"Logged in as {self.user} ({self.user.id})")
        await self.change_presence(
            status=discord.Status.dnd,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{len(self.guilds)} servers | ,help"
            )
        )

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(embed=discord.Embed(
                description="No tienes permisos suficientes.",
                color=0x2b2d31
            ))
        elif isinstance(error, commands.NotOwner):
            await ctx.send(embed=discord.Embed(
                description="Este comando es solo para el owner.",
                color=0x2b2d31
            ))
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(embed=discord.Embed(
                description=f"Argumento faltante: `{error.param.name}`",
                color=0x2b2d31
            ))
        else:
            log.error(f"Error en {ctx.command}: {error}")
            await ctx.send(embed=discord.Embed(
                description=f"Ocurrió un error ejecutando el comando: `{error}`",
                color=0xed4245,
            ))


async def main():
    token = os.getenv("TOKEN")
    if not token:
        log.critical("TOKEN environment variable not set.")
        return

    bot = AntiNukeBot()
    async with bot:
        await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
