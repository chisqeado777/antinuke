"""
freefire.py — Búsqueda de jugadores de Free Fire por UID.

⚠️ Usa una API NO OFICIAL de comunidad (developers.freefirecommunity.com),
sin ninguna relación con Garena. Puede fallar o dejar de funcionar sin aviso.

Requiere la variable de entorno FREEFIRE_API_KEY (gratis en
https://developers.freefirecommunity.com, 100 solicitudes/hora).

Comandos:
  ,ffinfo <uid> [region]   — perfil: nivel, rango, clan, insignias
  ,ffstats <uid> [region]  — estadísticas de partidas: victorias, kills, headshots
  ,ffban <uid>             — verifica si la cuenta está baneada
"""

import discord
from discord.ext import commands
import aiohttp
import os
import logging

log = logging.getLogger("antinuke.freefire")

API_BASE = "https://developers.freefirecommunity.com/api/v1"
DEFAULT_REGION = "ind"
VALID_REGIONS = {"sg", "ind", "br"}


async def _fetch(endpoint: str, params: dict) -> dict | None:
    api_key = os.getenv("FREEFIRE_API_KEY")
    if not api_key:
        return {"__error__": "missing_key"}

    headers = {"x-api-key": api_key}
    url = f"{API_BASE}/{endpoint}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 404:
                    return {"__error__": "not_found"}
                if resp.status != 200:
                    return {"__error__": f"http_{resp.status}"}
                return await resp.json()
    except Exception as e:
        log.error(f"Free Fire API error: {e}")
        return {"__error__": "network"}


def _error_embed(error: str) -> discord.Embed:
    messages = {
        "missing_key": "El bot no tiene configurada la API key de Free Fire (`FREEFIRE_API_KEY` en Railway).",
        "not_found": "No encontré ningún jugador con ese UID.",
        "network": "No se pudo conectar con la API de Free Fire ahora mismo. Intenta de nuevo en un rato.",
    }
    text = messages.get(error, f"Error de la API: `{error}`")
    return discord.Embed(description=text, color=0xed4245)


class FreeFire(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="ffinfo")
    async def ffinfo(self, ctx: commands.Context, uid: str, region: str = DEFAULT_REGION):
        region = region.lower()
        if region not in VALID_REGIONS:
            return await ctx.send(embed=discord.Embed(
                description=f"Región inválida. Usa una de: {', '.join(VALID_REGIONS)}",
                color=0xed4245,
            ))

        data = await _fetch("info", {"region": region, "uid": uid})
        if data is None or "__error__" in data:
            return await ctx.send(embed=_error_embed(data.get("__error__", "unknown") if data else "unknown"))

        basic = data.get("basicInfo", data)
        embed = discord.Embed(
            title=basic.get("nickname", f"UID {uid}"),
            color=0x2b2d31,
        )
        embed.add_field(name="Nivel", value=str(basic.get("level", "—")), inline=True)
        embed.add_field(name="Rango BR", value=str(basic.get("rank", basic.get("brRank", "—"))), inline=True)
        embed.add_field(name="Región", value=region.upper(), inline=True)
        if basic.get("clanName") or basic.get("guildName"):
            embed.add_field(name="Clan", value=basic.get("clanName") or basic.get("guildName"), inline=True)
        embed.set_footer(text=f"UID: {uid} · Datos vía comunidad, no oficiales de Garena")
        await ctx.send(embed=embed)

    @commands.command(name="ffstats")
    async def ffstats(self, ctx: commands.Context, uid: str, region: str = DEFAULT_REGION):
        region = region.lower()
        if region not in VALID_REGIONS:
            return await ctx.send(embed=discord.Embed(
                description=f"Región inválida. Usa una de: {', '.join(VALID_REGIONS)}",
                color=0xed4245,
            ))

        data = await _fetch("stats", {"region": region, "uid": uid})
        if data is None or "__error__" in data:
            return await ctx.send(embed=_error_embed(data.get("__error__", "unknown") if data else "unknown"))

        embed = discord.Embed(title=f"Estadísticas — UID {uid}", color=0x2b2d31)
        squad = data.get("squad", {})
        embed.add_field(name="Partidas jugadas", value=str(squad.get("matches", "—")), inline=True)
        embed.add_field(name="Victorias", value=str(squad.get("wins", "—")), inline=True)
        embed.add_field(name="Kills", value=str(squad.get("kills", "—")), inline=True)
        embed.add_field(name="Headshots", value=str(squad.get("headshots", "—")), inline=True)
        embed.set_footer(text=f"Región: {region.upper()} · Datos vía comunidad, no oficiales de Garena")
        await ctx.send(embed=embed)

    @commands.command(name="ffban")
    async def ffban(self, ctx: commands.Context, uid: str):
        data = await _fetch("bancheck", {"uid": uid})
        if data is None or "__error__" in data:
            return await ctx.send(embed=_error_embed(data.get("__error__", "unknown") if data else "unknown"))

        banned = data.get("is_banned") or data.get("banned")
        embed = discord.Embed(
            title=f"Estado de la cuenta — UID {uid}",
            description="🔴 Esta cuenta está **baneada** (o fue reportada/suspendida por hacks)." if banned
                        else "🟢 Esta cuenta **no** tiene baneos ni reportes activos.",
            color=0xed4245 if banned else 0x57f287,
        )

        if banned:
            period = data.get("ban_period") or data.get("banPeriod") or data.get("period")
            reason = data.get("ban_reason") or data.get("banReason") or data.get("reason")
            date = data.get("ban_date") or data.get("banDate") or data.get("date")
            if period:
                embed.add_field(name="Duración del baneo", value=str(period), inline=True)
            if reason:
                embed.add_field(name="Motivo", value=str(reason), inline=True)
            if date:
                embed.add_field(name="Fecha", value=str(date), inline=True)

        embed.set_footer(text="Datos vía comunidad, no oficiales de Garena")
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(FreeFire(bot))
