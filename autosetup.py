"""
autosetup.py — Configura todo el bot automáticamente en un solo comando.

Comandos:
  ,autosetup normal   — preset equilibrado, pensado para la mayoría de servidores
  ,autosetup rapido    — protección máxima al instante, todo lo más estricto posible

Ambos comandos:
  1. Crean la categoría "logs" con los 10 canales (si no existen ya).
  2. Enlazan cada canal a su categoría de log correspondiente.
  3. Activan y configuran el AntiNuke con el preset elegido.
  4. Muestran un embed con todo lo que se configuró.
"""

import discord
from discord.ext import commands
from config import db
from logger import LOG_CATEGORIES
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
        category = await guild.create_category(LOGS_CATEGORY_NAME, overwrites=overwrites, reason="AntiNuke: auto-configuración")

    result = {}
    for cat_key, channel_name in LOG_CATEGORIES.items():
        existing = discord.utils.get(category.text_channels, name=channel_name)
        if existing is None:
            existing = await guild.create_text_channel(
                channel_name, category=category, reason="AntiNuke: auto-configuración"
            )
        result[cat_key] = existing.id
    return result


class AutoSetup(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.group(name="autosetup", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def autosetup(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Auto-configuración",
            description=(
                "`,autosetup normal` — preset equilibrado (recomendado)\n"
                "`,autosetup rapido` — protección máxima al instante\n\n"
                "Ambos crean automáticamente la categoría de logs con sus 10 canales."
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

        log_channels = await _ensure_log_channels(ctx.guild)

        config = db.get_guild(ctx.guild.id)
        config["log_channels"] = log_channels
        config["log_channel"] = log_channels.get("mod")  # fallback legado
        config["antinuke"].update(preset)
        db.update_guild(ctx.guild.id, config)

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
        channels_text = "\n".join(
            f"`{cat}` → <#{cid}>" for cat, cid in log_channels.items()
        )
        embed.add_field(name="Canales de Logs Creados", value=channels_text, inline=False)
        embed.set_footer(text="Usa ,antinuke status para ver la configuración completa en cualquier momento.")

        await status_msg.edit(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoSetup(bot))
