"""
quality_guide.py — Comando fijo que manda la tarjeta de guía de calidad
(upscale de wallpapers), con botón de link a imageupscaler.com.

Comando: ,calidad
"""

import os
import discord
from discord.ext import commands

# El gif vive dentro del repo — el bot lo manda desde disco cada vez,
# así nunca depende de un link externo que pueda caducar.
GIF_PATH = os.path.join(os.path.dirname(__file__), "assets", "quality_upscale.gif")
GIF_FILENAME = "quality_upscale.gif"

QUALITY_TEXT_ES = (
    "¡Hola! ¿Descargaste un wallpaper pero la calidad no quedó como querías? "
    "Sigue la guía de abajo.\n\n"
    "**Cómo usar:**\n"
    "• Descarga el wallpaper que quieras.\n"
    "• Si la calidad no es buena, dale clic al botón de abajo para mejorar tu imagen en **400x**.\n"
    "• Después de eso, solo guarda y usa tu nuevo wallpaper."
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
        embed.add_field(name="Introducción de Calidad", value=QUALITY_TEXT_ES, inline=False)
        embed.add_field(name="🇺🇸 - Quality Guide", value=QUALITY_TEXT_EN, inline=False)

        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label="Calidad", url="https://imageupscaler.com/", style=discord.ButtonStyle.link,
        ))

        kwargs = {"embed": embed, "view": view}
        if os.path.exists(GIF_PATH):
            file = discord.File(GIF_PATH, filename=GIF_FILENAME)
            embed.set_image(url=f"attachment://{GIF_FILENAME}")
            kwargs["file"] = file

        await ctx.send(**kwargs)


async def setup(bot: commands.Bot):
    await bot.add_cog(QualityGuide(bot))

