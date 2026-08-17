"""
autosetup.py — Configura el bot automáticamente.

Comandos:
  ,autosetup normal   — preset equilibrado, pensado para la mayoría de servidores
  ,autosetup rapido    — protección máxima al instante, todo lo más estricto posible
  ,setuplogs           — crea (o reutiliza) la categoría "logs" con sus 10 canales
                         y los enlaza para que cada tipo de log llegue a su canal

Son comandos independientes: puedes correr uno sin el otro. Si corres
,autosetup sin haber corrido ,setuplogs antes, los logs caen de vuelta al
canal legado (,setlogs) hasta que configures los canales dedicados.
"""

import discord
from discord.ext import commands
from config import db
from logger import LOG_CATEGORIES, LOG_CATEGORY_META
import logging

log = logging.getLogger("antinuke.autosetup")

LOGS_CATEGORY_NAME = "logs"

# ── Presets ──────────────────────────────────────────────────────────────────

PRESET_NORMAL = {
    "enabled": True,
    "punishment": "strip",
    "ban_threshold": 3, "ban_window": 10,
    "kick_threshold": 3, "kick_window": 10,
    "channel_delete_threshold": 3, "channel_delete_window": 10,
    "channel_create_threshold": 5, "channel_create_window": 10,
    "role_delete_threshold": 3, "role_delete_window": 10,
    "role_create_threshold": 5, "role_create_window": 10,
    "webhook_create_threshold": 3, "webhook_create_window": 10,
    "mention_threshold": 10, "mention_window": 8,
    "emoji_delete_threshold": 5, "emoji_delete_window": 10,
    "min_account_age_days": 3,
    "min_guild_age_days": 0,
}

PRESET_RAPIDO = {
    "enabled": True,
    "punishment": "ban",
    "ban_threshold": 1, "ban_window": 5,
    "kick_threshold": 1, "kick_window": 5,
    "channel_delete_threshold": 1, "channel_delete_window": 5,
    "channel_create_threshold": 2, "channel_create_window": 5,
    "role_delete_threshold": 1, "role_delete_window": 5,
    "role_create_threshold": 2, "role_create_window": 5,
    "webhook_create_threshold": 1, "webhook_create_window": 5,
    "mention_threshold": 5, "mention_window": 5,
    "emoji_delete_threshold": 2, "emoji_delete_window": 5,
    "min_account_age_days": 7,
    "min_guild_age_days": 0,
}

PRESET_LABELS = {
    "normal": ("Normal", PRESET_NORMAL, "Equilibrado para el día a día: deja margen antes de castigar, pero cubre todos los módulos."),
    "rapido": ("Rápido", PRESET_RAPIDO, "Cero tolerancia: castiga a la primera acción sospechosa. Recomendado si ya sufriste un ataque antes."),
}


async def _ensure_log_channels(guild: discord.Guild) -> dict[str, int]:
    """Crea la categoría 'logs' y sus 10 canales si no existen. Devuelve {categoria: channel_id}."""
    category = discord.utils.get(guild.categories, name=LOGS_CATEGORY_NAME)
    if category is None:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        category = await guild.create_category(LOGS_CATEGORY_NAME, overwrites=overwrites, reason="AntiNuke: setup de logs")

    result = {}
    for cat_key, channel_name in LOG_CATEGORIES.items():
        _, _, description = LOG_CATEGORY_META.get(cat_key, ("📋", 0x2b2d31, ""))
        existing = discord.utils.get(category.text_channels, name=channel_name)
        if existing is None:
            existing = await guild.create_text_channel(
                channel_name, category=category, topic=description,
                reason="AntiNuke: setup de logs",
            )
        result[cat_key] = existing.id
    return result


class AutoSetup(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── ,setuplogs ───────────────────────────────────────────────────────────

    @commands.command(name="setuplogs")
    @commands.has_permissions(administrator=True)
    async def setuplogs(self, ctx: commands.Context):
        status_msg = await ctx.send(embed=discord.Embed(
            description="Creando la categoría de logs...",
            color=0x2b2d31,
        ))

        log_channels = await _ensure_log_channels(ctx.guild)

        config = db.get_guild(ctx.guild.id)
        config["log_channels"] = log_channels
        config["log_channel"] = log_channels.get("mod")  # fallback legado
        db.update_guild(ctx.guild.id, config)

        embed = discord.Embed(
            title="✅ Canales de logs listos",
            description="Cada tipo de evento ahora se manda a su canal correspondiente.",
            color=0x57f287,
        )
        channels_text = "\n".join(
            f"{LOG_CATEGORY_META.get(cat, ('📋','', ''))[0]} <#{cid}> — {LOG_CATEGORY_META.get(cat, ('','', ''))[2]}"
            for cat, cid in log_channels.items()
        )
        embed.add_field(name="Canales", value=channels_text, inline=False)
        await status_msg.edit(embed=embed)

    # ── ,autosetup ───────────────────────────────────────────────────────────

    @commands.group(name="autosetup", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def autosetup(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Auto-configuración",
            description=(
                "`,autosetup normal` — preset equilibrado (recomendado)\n"
                "`,autosetup rapido` — protección máxima al instante\n\n"
                "¿Todavía no tienes canales de logs? Usa `,setuplogs` para crearlos."
            ),
            color=0x2b2d31,
        )
        await ctx.send(embed=embed)

    @autosetup.command(name="normal")
    @commands.has_permissions(administrator=True)
    async def autosetup_normal(self, ctx: commands.Context):
        await self._run_preset(ctx, "normal")

    @autosetup.command(name="rapido")
    @commands.has_permissions(administrator=True)
    async def autosetup_rapido(self, ctx: commands.Context):
        await self._run_preset(ctx, "rapido")

    async def _run_preset(self, ctx: commands.Context, preset_key: str):
        label, preset, description = PRESET_LABELS[preset_key]
        status_msg = await ctx.send(embed=discord.Embed(
            description=f"Configurando el preset **{label}**...",
            color=0x2b2d31,
        ))

        config = db.get_guild(ctx.guild.id)
        config["antinuke"].update(preset)
        db.update_guild(ctx.guild.id, config)

        has_log_channels = bool(config.get("log_channels"))

        # ── Embed resumen de todo lo que se configuró ──
        embed = discord.Embed(
            title=f"✅ Preset «{label}» aplicado",
            description=description,
            color=0x57f287,
        )
        embed.add_field(
            name="AntiNuke",
            value=(
                f"Sanción: `{preset['punishment']}`\n"
                f"Umbral de baneos: `{preset['ban_threshold']}` en `{preset['ban_window']}s`\n"
                f"Umbral de expulsiones: `{preset['kick_threshold']}` en `{preset['kick_window']}s`\n"
                f"Umbral canales/roles: `{preset['channel_delete_threshold']}` en `{preset['channel_delete_window']}s`\n"
                f"Edad mínima de cuenta: `{preset['min_account_age_days']} días`"
            ),
            inline=False,
        )
        if not has_log_channels:
            embed.add_field(
                name="⚠️ Canales de logs",
                value="Todavía no tienes canales dedicados. Usa `,setuplogs` para crearlos.",
                inline=False,
            )
        embed.set_footer(text="Usa ,antinuke status para ver la configuración completa en cualquier momento.")

        await status_msg.edit(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoSetup(bot))
