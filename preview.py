"""
preview.py — Genera una tarjeta de vista previa a partir de una imagen de
avatar y/o banner que adjuntes directamente al comando, con un fondo
temático oscuro y botones de descarga.

Comando:
  ,preview  (con 1 o 2 imágenes adjuntas al mensaje)
      1 imagen  → genera la tarjeta de avatar (círculo)
      2 imágenes → genera avatar + banner (en ese orden de adjunto)

Nota sobre el fondo: por ahora genera un degradado oscuro con viñeta
programáticamente (no depende de ningún archivo externo). Si más adelante
quieres el estilo exacto de otro bot (fondos ilustrados, temas, etc.),
sube esas imágenes de fondo a /assets/themes/ en el repo y cambia
_generate_background() para que las use en vez del degradado.
"""

import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFilter, ImageOps, ImageFont
import io
import logging
from webhook_utils import edit_via_webhook

log = logging.getLogger("antinuke.preview")

CANVAS_SIZE = (800, 500)
BANNER_CANVAS_SIZE = (800, 320)
BADGE_COLORS = [(88, 101, 242), (87, 242, 135), (114, 137, 218), (235, 69, 158), (87, 242, 242)]


def _generate_background(size: tuple[int, int]) -> Image.Image:
    """Degradado oscuro con viñeta — placeholder hasta tener temas propios."""
    w, h = size
    top, bottom = (32, 22, 42), (6, 6, 12)
    bg = Image.new("RGB", size)
    draw = ImageDraw.Draw(bg)
    for y in range(h):
        t = y / h
        r = int(top[0] * (1 - t) + bottom[0] * t)
        g = int(top[1] * (1 - t) + bottom[1] * t)
        b = int(top[2] * (1 - t) + bottom[2] * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    vignette = Image.new("L", size, 0)
    vd = ImageDraw.Draw(vignette)
    vd.ellipse([-w * 0.3, -h * 0.3, w * 1.3, h * 1.3], fill=255)
    vignette = vignette.filter(ImageFilter.GaussianBlur(90))
    black = Image.new("RGB", size, (0, 0, 0))
    return Image.composite(bg, black, vignette)


def _circle_crop(img: Image.Image, size: int) -> Image.Image:
    img = ImageOps.fit(img.convert("RGBA"), (size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    img.putalpha(mask)
    return img


def _add_badge_row(canvas: Image.Image, x: int, y: int):
    draw = ImageDraw.Draw(canvas)
    for i, c in enumerate(BADGE_COLORS):
        cx = x + i * 34
        draw.ellipse([cx, y, cx + 26, y + 26], fill=c)


def _watermark_font(size: int = 22):
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except OSError:
        return ImageFont.load_default()


def build_avatar_card(avatar_bytes: bytes, watermark: str) -> io.BytesIO:
    avatar = Image.open(io.BytesIO(avatar_bytes))
    bg = _generate_background(CANVAS_SIZE).convert("RGBA")

    circle = _circle_crop(avatar, 320)
    pos = ((CANVAS_SIZE[0] - 320) // 2, 60)
    bg.paste(circle, pos, circle)

    _add_badge_row(bg, pos[0] + 6, pos[1] + 320 + 24)
    ImageDraw.Draw(bg).text(
        (pos[0] + 6, pos[1] + 320 + 60), watermark,
        fill=(230, 230, 235), font=_watermark_font(),
    )

    buf = io.BytesIO()
    bg.convert("RGB").save(buf, format="PNG")
    buf.seek(0)
    return buf


def build_banner_card(banner_bytes: bytes, watermark: str) -> io.BytesIO:
    banner = Image.open(io.BytesIO(banner_bytes))
    bg = _generate_background(BANNER_CANVAS_SIZE).convert("RGBA")

    banner_fit = ImageOps.fit(banner.convert("RGB"), (700, 200), Image.LANCZOS)
    pos = ((BANNER_CANVAS_SIZE[0] - 700) // 2, 40)
    bg.paste(banner_fit, pos)

    _add_badge_row(bg, pos[0] + 6, pos[1] + 200 + 24)
    ImageDraw.Draw(bg).text(
        (pos[0] + 6, pos[1] + 200 + 60), watermark,
        fill=(230, 230, 235), font=_watermark_font(),
    )

    buf = io.BytesIO()
    bg.convert("RGB").save(buf, format="PNG")
    buf.seek(0)
    return buf


class Preview(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="preview")
    async def preview(self, ctx: commands.Context):
        images = [a for a in ctx.message.attachments if a.content_type and a.content_type.startswith("image/")]
        if not images:
            return await ctx.send(embed=discord.Embed(
                description="Adjunta 1 imagen (avatar) o 2 (avatar + banner, en ese orden) junto con `,preview`.",
                color=0xed4245,
            ))
        if len(images) > 2:
            images = images[:2]

        status = await ctx.send(embed=discord.Embed(description="🎨 Generando la vista previa...", color=0x2b2d31))

        try:
            files = []
            watermark = ctx.guild.name if ctx.guild else "Preview"

            avatar_bytes = await images[0].read()
            files.append(discord.File(build_avatar_card(avatar_bytes, watermark), filename="avatar_preview.png"))

            if len(images) > 1:
                banner_bytes = await images[1].read()
                files.append(discord.File(build_banner_card(banner_bytes, watermark), filename="banner_preview.png"))
        except Exception as e:
            log.error(f"Error generando preview: {e}")
            return await status.edit(embed=discord.Embed(
                description="No pude procesar esa imagen — asegúrate de que sea un PNG/JPG/WEBP válido.",
                color=0xed4245,
            ))

        msg = await ctx.send(files=files)
        await status.delete()

        labels = ["⬇️ Descargar Avatar"] + (["⬇️ Descargar Banner"] if len(images) > 1 else [])
        view = discord.ui.View()
        for attachment, label in zip(msg.attachments, labels):
            view.add_item(discord.ui.Button(label=label, url=attachment.url, style=discord.ButtonStyle.link))

        await edit_via_webhook(ctx.channel, msg.id, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(Preview(bot))
