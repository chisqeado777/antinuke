"""
jail.py — Sistema de aislamiento (cuarentena).

Comandos:
  ,setupjail            — crea el rol "Aislado" y el canal de cuarentena,
                           y bloquea ese rol en todos los canales existentes.
  ,jail <usuario> [razón]    — le quita todos los roles y lo manda al canal de cuarentena.
  ,unjail <usuario> [razón]  — le devuelve los roles que tenía antes de ser aislado.

Requiere haber corrido ,setuplogs antes para que las acciones de jail/unjail
se registren en el canal de logs de la categoría "jail".
"""

import discord
from discord.ext import commands
from config import db
from logger import send_log
import logging

log = logging.getLogger("antinuke.jail")

JAIL_CATEGORY_NAME = "🔒 Cuarentena"
JAIL_ROLE_NAME = "Aislado"
JAIL_CHANNEL_NAME = "⛓️│aislado"


def _hierarchy_error(ctx: commands.Context, target: discord.Member) -> str | None:
    if target.id == ctx.author.id:
        return "No puedes hacerte esto a ti mismo."
    if target.id == ctx.bot.user.id:
        return "No puedo hacerme esto a mí mismo."
    if target.id == ctx.guild.owner_id:
        return "No puedo aislar al dueño del servidor."
    if ctx.author.id != ctx.guild.owner_id and target.top_role >= ctx.author.top_role:
        return "No puedes aislar a alguien con un rol igual o superior al tuyo."
    if target.top_role >= ctx.guild.me.top_role:
        return "Mi rol está por debajo (o igual) del rol de ese usuario, no puedo hacer nada."
    return None


class Jail(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── ,setupjail ───────────────────────────────────────────────────────────

    @commands.command(name="setupjail")
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_roles=True, manage_channels=True)
    async def setupjail(self, ctx: commands.Context):
        status = await ctx.send(embed=discord.Embed(
            description="Configurando el sistema de aislamiento...",
            color=0x2b2d31,
        ))

        config = db.get_guild(ctx.guild.id)
        jail_cfg = config.get("jail", {})

        # Rol "Aislado"
        role = ctx.guild.get_role(jail_cfg.get("role_id")) if jail_cfg.get("role_id") else None
        if role is None:
            role = discord.utils.get(ctx.guild.roles, name=JAIL_ROLE_NAME)
        if role is None:
            role = await ctx.guild.create_role(
                name=JAIL_ROLE_NAME, permissions=discord.Permissions.none(),
                reason="AntiNuke: setup de cuarentena",
            )

        # Categoría y canal de cuarentena
        category = discord.utils.get(ctx.guild.categories, name=JAIL_CATEGORY_NAME)
        if category is None:
            category = await ctx.guild.create_category(JAIL_CATEGORY_NAME, reason="AntiNuke: setup de cuarentena")

        jail_channel = ctx.guild.get_channel(jail_cfg.get("channel_id")) if jail_cfg.get("channel_id") else None
        if jail_channel is None:
            jail_channel = discord.utils.get(category.text_channels, name=JAIL_CHANNEL_NAME)
        if jail_channel is None:
            jail_channel = await ctx.guild.create_text_channel(
                JAIL_CHANNEL_NAME,
                category=category,
                topic="Canal para usuarios aislados. Solo ellos pueden verlo.",
                overwrites={
                    ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                    role: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                    ctx.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                },
                reason="AntiNuke: setup de cuarentena",
            )

        # Bloquear el rol "Aislado" en TODOS los demás canales existentes
        blocked = 0
        for channel in ctx.guild.channels:
            if channel.id == jail_channel.id or channel.category_id == category.id:
                continue
            try:
                await channel.set_permissions(role, view_channel=False, reason="AntiNuke: setup de cuarentena")
                blocked += 1
            except (discord.Forbidden, discord.HTTPException):
                continue

        config["jail"] = {"role_id": role.id, "channel_id": jail_channel.id}
        db.update_guild(ctx.guild.id, config)

        embed = discord.Embed(
            title="✅ Sistema de cuarentena listo",
            description=(
                f"Rol: {role.mention}\n"
                f"Canal: {jail_channel.mention}\n"
                f"Se bloqueó el acceso en `{blocked}` canal(es) existente(s).\n\n"
                f"Ahora puedes usar `,jail <usuario>` para aislar a alguien."
            ),
            color=0x57f287,
        )
        await status.edit(embed=embed)

    # ── ,jail ────────────────────────────────────────────────────────────────

    @commands.command(name="jail")
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def jail(self, ctx: commands.Context, member: discord.Member, *, reason: str = "Sin razón especificada"):
        config = db.get_guild(ctx.guild.id)
        jail_cfg = config.get("jail", {})
        role_id = jail_cfg.get("role_id")
        if not role_id:
            return await ctx.send(embed=discord.Embed(
                description="Primero corre `,setupjail` para configurar el sistema de aislamiento.",
                color=0xed4245,
            ))

        role = ctx.guild.get_role(role_id)
        if role is None:
            return await ctx.send(embed=discord.Embed(
                description="El rol de aislamiento ya no existe. Corre `,setupjail` de nuevo.",
                color=0xed4245,
            ))

        error = _hierarchy_error(ctx, member)
        if error:
            return await ctx.send(embed=discord.Embed(description=error, color=0xed4245))

        if role in member.roles:
            return await ctx.send(embed=discord.Embed(description=f"{member.mention} ya está aislado.", color=0xed4245))

        # Guardar los roles actuales (menos @everyone y roles administrados por integraciones)
        current_roles = [r.id for r in member.roles if not r.is_default() and not r.managed]
        backups = config.get("jail_backups", {})
        backups[str(member.id)] = current_roles
        config["jail_backups"] = backups
        db.update_guild(ctx.guild.id, config)

        keep_roles = [r for r in member.roles if r.managed]  # roles de bots/boost no se pueden quitar así
        try:
            await member.edit(roles=keep_roles + [role], reason=f"{ctx.author} ({ctx.author.id}): {reason}")
        except discord.Forbidden:
            return await ctx.send(embed=discord.Embed(description="No tengo permiso para modificar los roles de ese usuario.", color=0xed4245))

        try:
            await member.send(embed=discord.Embed(
                description=f"Fuiste aislado en **{ctx.guild.name}**.\n**Razón:** {reason}",
                color=0x992d22,
            ))
        except (discord.Forbidden, discord.HTTPException):
            pass

        await ctx.send(embed=discord.Embed(
            description=f"🚨 {member.mention} fue aislado.\n**Razón:** {reason}",
            color=0x57f287,
        ))
        await send_log(
            ctx.guild, action="jail", target=member, moderator=ctx.author,
            reason=reason, module="Aislamiento", category="jail",
        )

    # ── ,unjail ──────────────────────────────────────────────────────────────

    @commands.command(name="unjail")
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def unjail(self, ctx: commands.Context, member: discord.Member, *, reason: str = "Sin razón especificada"):
        config = db.get_guild(ctx.guild.id)
        jail_cfg = config.get("jail", {})
        role_id = jail_cfg.get("role_id")
        role = ctx.guild.get_role(role_id) if role_id else None

        if role is None or role not in member.roles:
            return await ctx.send(embed=discord.Embed(description=f"{member.mention} no está aislado.", color=0xed4245))

        backups = config.get("jail_backups", {})
        saved_ids = backups.pop(str(member.id), [])
        config["jail_backups"] = backups
        db.update_guild(ctx.guild.id, config)

        restored_roles = [ctx.guild.get_role(rid) for rid in saved_ids]
        restored_roles = [r for r in restored_roles if r is not None and r < ctx.guild.me.top_role]
        keep_roles = [r for r in member.roles if r.managed]

        try:
            await member.edit(roles=keep_roles + restored_roles, reason=f"{ctx.author} ({ctx.author.id}): {reason}")
        except discord.Forbidden:
            return await ctx.send(embed=discord.Embed(description="No tengo permiso para modificar los roles de ese usuario.", color=0xed4245))

        await ctx.send(embed=discord.Embed(
            description=f"✅ {member.mention} ya no está aislado. Se restauraron `{len(restored_roles)}` rol(es).",
            color=0x57f287,
        ))
        await send_log(
            ctx.guild, action="unjail", target=member, moderator=ctx.author,
            reason=reason, module="Fin de Aislamiento", category="jail",
        )

    # ── Protección automática de canales nuevos ────────────────────────────────

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        config = db.get_guild(channel.guild.id)
        jail_cfg = config.get("jail", {})
        role_id = jail_cfg.get("role_id")
        jail_channel_id = jail_cfg.get("channel_id")
        if not role_id or channel.id == jail_channel_id:
            return
        role = channel.guild.get_role(role_id)
        if role is None:
            return
        try:
            await channel.set_permissions(role, view_channel=False, reason="AntiNuke: protección automática de cuarentena")
        except (discord.Forbidden, discord.HTTPException):
            pass

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MissingPermissions):
            perms = ", ".join(error.missing_permissions)
            await ctx.send(embed=discord.Embed(description=f"Te falta el permiso `{perms}` para usar este comando.", color=0xed4245))
        elif isinstance(error, commands.BotMissingPermissions):
            perms = ", ".join(error.missing_permissions)
            await ctx.send(embed=discord.Embed(description=f"Me falta el permiso `{perms}` para hacer eso.", color=0xed4245))
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send(embed=discord.Embed(description="No encontré a ese usuario.", color=0xed4245))
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(embed=discord.Embed(description=f"Falta el argumento `{error.param.name}`.", color=0xed4245))
        else:
            log.error(f"Error en comando de jail: {error}")
            raise error


async def setup(bot: commands.Bot):
    await bot.add_cog(Jail(bot))
