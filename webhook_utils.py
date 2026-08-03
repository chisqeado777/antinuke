"""
webhook_utils.py — Envía todos los mensajes del bot a través de un webhook
(con el mismo nombre y avatar del bot) en vez de usar el bot directamente.

Los DMs no soportan webhooks (limitación de la API de Discord), así que ahí
siempre se cae de vuelta al envío normal.
"""

import discord
import logging

log = logging.getLogger("antinuke.webhook")

WEBHOOK_NAME = "AntiNuke Webhook"

# Cache en memoria: channel_id -> discord.Webhook
_webhook_cache: dict[int, discord.Webhook] = {}

# Tipos de canal que soportan webhooks
_WEBHOOK_CAPABLE = (discord.TextChannel, discord.VoiceChannel, discord.StageChannel)


def _base_channel(channel):
    """Para hilos, el webhook vive en el canal padre."""
    if isinstance(channel, discord.Thread):
        return channel.parent
    return channel


async def get_channel_webhook(channel) -> discord.Webhook | None:
    """Obtiene (o crea) el webhook del bot para este canal, cacheado."""
    base = _base_channel(channel)
    if base is None or not isinstance(base, _WEBHOOK_CAPABLE):
        return None

    if base.id in _webhook_cache:
        return _webhook_cache[base.id]

    try:
        webhooks = await base.webhooks()
        webhook = discord.utils.get(webhooks, name=WEBHOOK_NAME)
        if webhook is None:
            webhook = await base.create_webhook(name=WEBHOOK_NAME, reason="Webhook para mensajes del bot")
    except (discord.Forbidden, discord.HTTPException):
        return None

    _webhook_cache[base.id] = webhook
    return webhook


async def send_via_webhook(channel, **kwargs):
    """
    Envía un mensaje a través del webhook del bot en ese canal, usando el
    nombre y avatar actuales del bot. Si no se puede (DM, permisos, etc.)
    cae de vuelta a channel.send normal. Devuelve el mensaje enviado.
    """
    if channel.guild is None:
        # DMs no soportan webhooks
        return await channel.send(**kwargs)

    webhook = await get_channel_webhook(channel)
    if webhook is None:
        return await channel.send(**kwargs)

    me = channel.guild.me
    kwargs.setdefault("username", me.display_name)
    kwargs.setdefault("avatar_url", me.display_avatar.url)
    kwargs.setdefault("wait", True)

    try:
        if isinstance(channel, discord.Thread):
            return await webhook.send(**kwargs, thread=channel)
        return await webhook.send(**kwargs)
    except (discord.NotFound, discord.Forbidden):
        _webhook_cache.pop(_base_channel(channel).id, None)
        kwargs.pop("username", None)
        kwargs.pop("avatar_url", None)
        kwargs.pop("wait", None)
        return await channel.send(**kwargs)


async def edit_via_webhook(channel, message_id: int, **kwargs):
    """Edita un mensaje que fue enviado por el webhook del bot en este canal."""
    webhook = await get_channel_webhook(channel)
    if webhook is None:
        msg = await channel.fetch_message(message_id)
        return await msg.edit(**kwargs)
    try:
        if isinstance(channel, discord.Thread):
            return await webhook.edit_message(message_id, **kwargs, thread=channel)
        return await webhook.edit_message(message_id, **kwargs)
    except discord.NotFound:
        msg = await channel.fetch_message(message_id)
        return await msg.edit(**kwargs)
