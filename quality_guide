"""
quality_guide.py — Comando fijo que manda la tarjeta de guía de calidad
(upscale de wallpapers), con botón de link a imageupscaler.com.

Comando: ,calidad
"""

import discord
from discord.ext import commands

# TODO: reemplaza esto por el link directo de tu gif animado real (no un PNG).
# Sube el .gif a cualquier canal de tu server, copia el link del archivo
# (clic derecho → Copiar enlace, o el link que te da Discord al subirlo) y
# pégalo aquí.
GIF_URL = "PEGA_AQUI_EL_LINK_DE_TU_GIF"

QUALITY_TEXT_PT = (
    "Hello! You downloaded a wallpaper, but the quality isn't quite what you wanted? "
    "Follow the guide below.\n\n"
    "**How to use:**\n"
    "• Download the wallpaper of your choice.\n"
    "• If the quality isn't good, click the button below to upscale your image by **400x**.\n"
    "• After that, just save and use your new wallpaper."
)

QUALITY_TEXT_EN = (
    "Hello! You downloaded a wallpaper, but the quality isn't quite what you wanted? "
    "Follow the steps below.\n\n"
    "**How to use:**\n"
    "• Download the wallpaper of your choice.\n"
    "• If the quality isn't good, click the button below to upscale your image by **400x**.\n"
    "• After that, simply save and use your new wallpaper."
)


class QualityGuide(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="calidad")
    async def calidad(self, ctx: commands.Context):
        embed = discord.Embed(color=0x2b2d31)
        if GIF_URL and "PEGA_AQUI" not in GIF_URL:
            embed.set_image(url=GIF_URL)
        embed.add_field(name="🇧🇷 - Quality Introduction", value=QUALITY_TEXT_PT, inline=False)
        embed.add_field(name="🇺🇸 - Quality Guide", value=QUALITY_TEXT_EN, inline=False)

        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label="Calidad", url="https://imageupscaler.com/", style=discord.ButtonStyle.link,
        ))

        await ctx.send(embed=embed, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(QualityGuide(bot))
