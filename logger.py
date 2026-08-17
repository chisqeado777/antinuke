import discord
from datetime import datetime, timezone
from config import db
import logging
from webhook_utils import send_via_webhook

log = logging.getLogger("antinuke.logger")

PUNISHMENT_LABELS = {
    "ban": "Baneado",
    "kick": "Expulsado",
    "strip": "Roles Retirados",
    "mute": "Muteado en el Servidor",
}

# Categorías de log disponibles y el nombre de canal que les corresponde
# (usado por el comando de auto-configuración para crearlos y enlazarlos)
LOG_CATEGORIES = {
    "messages": "📩│logs-mensajes",
    "channels": "📁│logs-canales",
    "roles": "🎭│logs-roles",
    "tickets": "🎫│logs-tickets",
    "invites": "📨│logs-invitaciones",
    "members": "👤│logs-miembros",
    "voice": "🔊│logs-voz",
    "mod": "🔨│logs-moderacion",
    "emojis": "😀│logs-emojis",
    "jail": "🚨│logs-aislados",
}

# Emoji, color y descripción por categoría — usado para darle estilo a los
# embeds de log y como topic de los canales que crea ,setuplogs.
LOG_CATEGORY_META = {
    "messages": ("📩", 0x5865f2, "Mensajes editados y borrados"),
    "channels": ("📁", 0x3498db, "Canales creados, eliminados o modificados"),
    "roles": ("🎭", 0x9b59b6, "Roles creados, eliminados o con permisos modificados"),
    "tickets": ("🎫", 0x1abc9c, "Actividad del sistema de tickets"),
    "invites": ("📨", 0xf1c40f, "Invitaciones creadas o usadas"),
    "members": ("👤", 0x2ecc71, "Entradas, salidas y cambios de miembros"),
    "voice": ("🔊", 0xe67e22, "Actividad en canales de voz"),
    "mod": ("🔨", 0xed4245, "Acciones de moderación: kicks, baneos, mutes, warns"),
    "emojis": ("😀", 0x95a5a6, "Emojis creados o eliminados"),
    "jail": ("🚨", 0x992d22, "Usuarios aislados y liberados"),
}


def _resolve_log_channel(guild: discord.Guild, config: dict, category: str):
    """
    Busca el canal para esta categoría de log. Si no hay uno configurado
    específicamente, cae de vuelta al canal de logs general (legado).
    """
    log_channels = config.get("log_channels", {})
    channel_id = log_channels.get(category) or config.get("log_channel")
    if not channel_id:
        return None
    return guild.get_channel(int(channel_id))


async def send_log(
    guild: discord.Guild,
    *,
    action: str,
    target: discord.Member | discord.User | None,
    moderator: discord.Member | discord.User | None,
    reason: str,
    module: str,
    category: str = "mod",
    extra_fields: list[tuple] | None = None,
    color: int | None = None,
):
    """
    Envía un embed de log al canal correspondiente a la categoría indicada
    (mod, channels, roles, emojis, members, voice, invites, messages, jail).
    """
    config = db.get_guild(guild.id)
    channel = _resolve_log_channel(guild, config, category)
    if not channel:
        return

    embed_cfg = config.get("log_embed", {})
    footer_text = embed_cfg.get("footer_text", "Protección AntiNuke")
    show_thumbnail = embed_cfg.get("thumbnail", True)

    cat_emoji, cat_color, _ = LOG_CATEGORY_META.get(category, ("📋", 0x2b2d31, ""))
    embed_color = color or embed_cfg.get("color") or cat_color

    punishment = config.get("antinuke", {}).get("punishment", "ban")
    punishment_label = PUNISHMENT_LABELS.get(punishment, punishment.capitalize())

    now = datetime.now(timezone.utc)
    timestamp_str = f"<t:{int(now.timestamp())}:F>"

    embed = discord.Embed(color=embed_color, timestamp=now)
    embed.set_author(
        name=guild.name,
        icon_url=guild.icon.url if guild.icon else None
    )

    embed.title = f"{cat_emoji} {module}"

    if target:
        embed.add_field(
            name="Infractor",
            value=f"{target.mention} `{target}` (`{target.id}`)",
            inline=False
        )
    if moderator:
        embed.add_field(
            name="Acción Tomada Por",
            value=f"{moderator.mention} `{moderator}` (`{moderator.id}`)",
            inline=False
        )

    embed.add_field(name="Sanción Aplicada", value=f"`{punishment_label}`", inline=True)
    embed.add_field(name="Módulo", value=f"`{module}`", inline=True)
    embed.add_field(name="Detectado A Las", value=timestamp_str, inline=False)
    embed.add_field(name="Razón", value=f"```{reason}```", inline=False)

    if extra_fields:
        for name, value, inline in extra_fields:
            embed.add_field(name=name, value=value, inline=inline)

    # El avatar del infractor es más útil como thumbnail que el ícono del server
    if show_thumbnail:
        if target is not None and hasattr(target, "display_avatar"):
            embed.set_thumbnail(url=target.display_avatar.url)
        elif guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

    embed.set_footer(text=footer_text)

    try:
        await send_via_webhook(channel, embed=embed)
    except Exception as e:
        log.warning(f"No se pudo enviar el log en {guild.name}: {e}")
