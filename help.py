import discord
from discord.ext import commands
from config import db
import logging

log = logging.getLogger("antinuke.help")

# ── Tabla de comandos ──────────────────────────────────────────────────────

CATEGORIES = {
    "antinuke": {
        "label": "AntiNuke",
        "emoji": "🛡️",
        "description": "Motor de protección principal — activa, desactiva y ajusta cada módulo.",
        "commands": [
            (",antinuke enable", "Activa la protección en este servidor"),
            (",antinuke disable", "Desactiva la protección en este servidor"),
            (",antinuke status", "Muestra la configuración completa actual"),
            (",antinuke punishment <tipo>", "Sanción a aplicar: `ban` `kick` `strip` `mute`"),
            (",antinuke module <nombre> <on/off>", "Activa o desactiva un módulo específico"),
            (",antinuke threshold <módulo> <n>", "Cuántas acciones antes de disparar la protección"),
            (",antinuke window <módulo> <seg>", "Ventana de tiempo en segundos para el límite"),
            (",antinuke accountage <días>", "Edad mínima de cuenta para unirse (0 = desactivado)"),
            (",antinuke guildage <días>", "Días mínimos en el server para confiar en sus acciones (0 = off)"),
            (",antinuke reset", "Reinicia la configuración a valores por defecto *(solo owner)*"),
        ],
    },
    "modulos": {
        "label": "Módulos",
        "emoji": "🧩",
        "description": "Módulos de protección disponibles, activables por separado.",
        "commands": [
            ("ban", "Detecta ataques de baneo masivo"),
            ("kick", "Detecta ataques de expulsión masiva"),
            ("channeldelete", "Detecta eliminación masiva de canales"),
            ("channelcreate", "Detecta creación en cadena de canales"),
            ("roledelete", "Detecta eliminación masiva de roles"),
            ("rolecreate", "Detecta creación en cadena de roles"),
            ("webhook", "Detecta creación no autorizada de webhooks"),
            ("mention", "Detecta spam de menciones masivas"),
            ("emojidelete", "Detecta eliminación masiva de emojis"),
            ("botadd", "Bloquea la adición no autorizada de bots"),
            ("everyone", "Bloquea menciones no autorizadas a @everyone/@here"),
            ("serverupdate", "Bloquea cambios no autorizados de nombre/ícono del server"),
            ("prune", "Bloquea expulsiones masivas (prune) no autorizadas"),
        ],
    },
    "moderacion": {
        "label": "Moderación",
        "emoji": "🔨",
        "description": "Comandos de moderación estándar: kicks, baneos, silencios, advertencias, purgas y más.",
        "commands": [
            (",kick <usuario> [razón]", "Expulsa a un miembro del servidor"),
            (",ban <usuario> [días_borrado] [razón]", "Banea a un miembro (borra sus mensajes de hasta 7 días)"),
            (",softban <usuario> [razón]", "Banea y desbanea al instante — borra mensajes sin expulsar de forma permanente"),
            (",unban <id_usuario> [razón]", "Desbanea a un usuario por su ID"),
            (",mute <usuario> <duración> [razón]", "Silencia temporalmente (ej. `10m`, `2h`, `1d`)"),
            (",unmute <usuario> [razón]", "Quita el silencio antes de tiempo"),
            (",warn <usuario> [razón]", "Registra una advertencia"),
            (",warnings <usuario>", "Muestra todas las advertencias de un usuario"),
            (",clearwarns <usuario>", "Borra todas las advertencias de un usuario"),
            (",delwarn <usuario> <índice>", "Elimina una advertencia específica por número"),
            (",purge <cantidad> [usuario]", "Borra mensajes recientes del canal (máx. 200)"),
            (",lockchannel [#canal]", "Bloquea un canal específico (impide que @everyone escriba)"),
            (",unlockchannel [#canal]", "Desbloquea un canal específico"),
            (",slowmode <segundos> [#canal]", "Ajusta el modo lento del canal"),
            (",nick <usuario> <apodo|reset>", "Cambia el apodo de un miembro"),
            (",role add <usuario> <rol>", "Asigna un rol a un miembro"),
            (",role remove <usuario> <rol>", "Quita un rol a un miembro"),
            (",modlogs <usuario>", "Muestra el historial de moderación de un usuario"),
            (",setupjail", "Crea el rol y canal de cuarentena, y bloquea el acceso en todo lo demás"),
            (",jail <usuario> [razón]", "Aísla a un usuario: le quita roles y lo manda al canal de cuarentena"),
            (",unjail <usuario> [razón]", "Libera a un usuario y le devuelve sus roles anteriores"),
        ],
    },
    "imagedrop": {
        "label": "Reenvío de Imágenes",
        "emoji": "🖼️",
        "description": "Mándale links de fotos/gifs por DM al bot y los reenvía al canal configurado — así no tienes que guardarlos tú.",
        "commands": [
            (",setpostchannel <#canal>", "Define a qué canal se reenvían los links que mandes"),
            (",posters add <usuario>", "Da acceso a alguien más para mandar links por DM"),
            (",posters remove <usuario>", "Quita ese acceso"),
            (",posters", "Lista quién tiene acceso"),
            (",post <link1> <link2> ...", "Postea hasta 5 links directamente desde el server"),
        ],
    },
    "whitelist": {
        "label": "Whitelist",
        "emoji": "✅",
        "description": "Los usuarios en whitelist están completamente exentos de la detección AntiNuke.",
        "commands": [
            (",whitelist", "Muestra los usuarios en whitelist"),
            (",whitelist add <usuario>", "Agrega un usuario a la whitelist *(solo owner)*"),
            (",whitelist remove <usuario>", "Quita un usuario de la whitelist *(solo owner)*"),
            (",whitelist clear", "Vacía toda la whitelist *(solo owner)*"),
            (",whitelist check <usuario>", "Verifica si un usuario está en whitelist"),
        ],
    },
    "logs": {
        "label": "Logs y Configuración",
        "emoji": "📋",
        "description": "Configura el canal de logs legado, el prefijo y la apariencia de los embeds.",
        "commands": [
            (",setlogs [#canal]", "Canal de logs único legado (omite el canal para quitarlo)"),
            (",setprefix <prefijo>", "Cambia el prefijo de comandos"),
            (",logembed color <hex>", "Color de los embeds de log (ej. `#a855f7`)"),
            (",logembed footer <texto>", "Texto del footer (soporta emojis del server)"),
            (",logembed thumbnail <on/off>", "Muestra/oculta el ícono del server en los logs"),
        ],
    },
    "autosetup": {
        "label": "Auto-Configuración",
        "emoji": "⚡",
        "description": "Configura todo el bot en segundos, con presets o canales de logs automáticos.",
        "commands": [
            (",setuplogs", "Crea (o reutiliza) la categoría de logs con sus 10 canales y los enlaza"),
            (",autosetup normal", "Preset equilibrado: sanciones con margen, pensado para el día a día"),
            (",autosetup rapido", "Protección máxima al instante: castiga a la primera acción sospechosa"),
        ],
    },
    "vc": {
        "label": "VC Tracker",
        "emoji": "🎚️",
        "description": "Rastrea cuánta gente hay en canales de voz y anuncia hitos.",
        "commands": [
            (",setvc channel <#canal>", "Canal donde se mandan las alertas automáticas de voz"),
            (",setvc threshold <n>", "Anuncia cada vez que se cruza un múltiplo de n personas"),
            (",vcstats", "Muestra cuánta gente hay ahora mismo en canales de voz"),
        ],
    },
    "voz": {
        "label": "Voz Temporal",
        "emoji": "🎙️",
        "description": "Canales de voz temporales tipo Join-to-Create, con panel de botones incluido.",
        "commands": [
            (",voiceset setup <categoría>", "Crea la categoría y el canal hub para generar VCs"),
            (",voiceset hub <#canal_voz>", "Usa un canal de voz existente como hub"),
            (",voiceset off", "Desactiva el sistema de voz temporal"),
            (",voice rename <nombre>", "Renombra tu canal de voz temporal"),
            (",voice limit <n>", "Cambia el límite de usuarios de tu canal"),
            ("Panel de botones", "Se manda solo al crear tu VC: bloquear, ocultar, reclamar, y más"),
        ],
    },
    "bienvenidas": {
        "label": "Bienvenidas",
        "emoji": "👋",
        "description": "Mensajes de bienvenida personalizados, con embeds, botones y variables.",
        "commands": [
            (",welcome add <#canal> <config>", "Agrega un mensaje de bienvenida en un canal"),
            (",welcome list", "Lista todas las bienvenidas configuradas"),
            (",welcome remove <n>", "Elimina la bienvenida número n"),
            (",welcome test", "Envía una bienvenida de prueba"),
            (",welcome off", "Desactiva todas las bienvenidas"),
        ],
    },
    "invitaciones": {
        "label": "Invitaciones",
        "emoji": "📨",
        "description": "Rastrea cuántas invitaciones trae cada miembro y recompensa a los que más invitan.",
        "commands": [
            (",setinvite channel <#canal>", "Canal donde se anuncian los hitos de invitaciones"),
            (",setinvite threshold <n> [recompensa]", "Define un umbral de invitaciones y su recompensa"),
            (",setinvite altdays <días>", "Días para considerar una cuenta como alt"),
            (",invites [usuario]", "Muestra cuántas invitaciones tiene alguien (o tú)"),
            (",invitetop", "Top de usuarios con más invitaciones"),
            (",resetinvites", "Reinicia el conteo de invitaciones del servidor"),
        ],
    },
    "giveaways": {
        "label": "Giveaways",
        "emoji": "🎉",
        "description": "Sorteos con botón de participación, bonus de probabilidad y reroll.",
        "commands": [
            (",gcreate <#canal> <duración> <premio>", "Crea un sorteo"),
            (",gend <id_mensaje>", "Termina un sorteo antes de tiempo"),
            (",greroll <id_mensaje>", "Rifa de nuevo un ganador"),
            (",gbonus <usuario> <porcentaje>", "Da a un usuario un % extra de probabilidad"),
            (",gbonus remove <usuario>", "Quita el bonus de un usuario"),
            (",gbonus list", "Lista todos los bonus activos"),
        ],
    },
    "lockdown": {
        "label": "Lockdown",
        "emoji": "🔒",
        "description": "Bloquea el servidor por completo al instante ante un ataque.",
        "commands": [
            (",lockdown", "Bloquea el servidor (impide que @everyone escriba)"),
            (",unlock", "Desbloquea el servidor"),
            (",lockdown exempt add <canal>", "Agrega un canal exento del lockdown"),
            (",lockdown exempt remove <canal>", "Quita un canal exento"),
            (",lockdown exempt list", "Lista los canales exentos"),
        ],
    },
    "desbaneos": {
        "label": "Desbaneos",
        "emoji": "🔨",
        "description": "Herramientas de moderación para revertir baneos masivos.",
        "commands": [
            (",unbanall", "Desbanea a todos los usuarios baneados del servidor"),
        ],
    },
    "freefire": {
        "label": "Free Fire",
        "emoji": "🔥",
        "description": "Búsqueda de jugadores de Free Fire por UID (API no oficial de comunidad).",
        "commands": [
            (",ffinfo <uid> [region]", "Perfil: nivel, rango, clan (región por defecto: `ind`)"),
            (",ffstats <uid> [region]", "Estadísticas: victorias, kills, headshots"),
            (",ffban <uid>", "Verifica si la cuenta está o estuvo baneada/reportada por hacks, con motivo y duración si aplica"),
        ],
    },
    "autoresponder": {
        "label": "Autoresponders",
        "emoji": "💬",
        "description": "Respuestas automáticas a palabras o frases exactas, en texto o embed.",
        "commands": [
            (",autoresponder add <trigger> | <respuesta>", "Crea una respuesta automática (texto o código de embed)"),
            (",autoresponder remove <trigger>", "Elimina un autoresponder"),
            (",autoresponder list", "Lista todos los autoresponders activos"),
            (",autoresponder clear", "Elimina todos los autoresponders"),
        ],
    },
    "embeds": {
        "label": "Embeds Personalizados",
        "emoji": "🖼️",
        "description": "Crea y edita embeds con el mismo motor de sintaxis que usan las bienvenidas.",
        "commands": [
            (",createembed <código>", "Crea y envía un embed personalizado en el canal actual"),
            (",editembed <link_mensaje> <código>", "Edita un embed que el bot mandó antes"),
            ("Sintaxis", "`{embed}$v{title: ...}$v{description: ...}$v{color: #hex}$v{field: nombre && valor && inline}`"),
            ("Variables", "`{user.mention}` `{user.tag}` `{guild.name}` `{guild.count}` `{channel.mention}` y más"),
        ],
    },
    "backup": {
        "label": "Respaldo",
        "emoji": "💾",
        "description": "Copias de seguridad del servidor para restaurar canales y roles tras un ataque.",
        "commands": [
            (",backup snapshot", "Fuerza una copia de seguridad ahora *(solo owner del bot)*"),
            (",backup restore", "Restaura el servidor desde la última copia *(solo owner del bot)*"),
            (",backup status", "Muestra info de la última copia guardada"),
        ],
    },
}

ALIASES = {
    "mod": "moderacion", "moderation": "moderacion", "moderación": "moderacion",
    "images": "imagedrop", "imagenes": "imagedrop", "fotos": "imagedrop",
    "modules": "modulos", "módulos": "modulos",
    "log": "logs", "settings": "logs",
    "setup": "autosetup", "auto": "autosetup", "autoconfig": "autosetup",
    "vctracker": "vc", "voicechannel": "vc",
    "voice": "voz", "voicemaster": "voz",
    "welcome": "bienvenidas",
    "invites": "invitaciones", "invite": "invitaciones",
    "giveaway": "giveaways", "sorteos": "giveaways", "sorteo": "giveaways",
    "unban": "desbaneos",
    "respaldo": "backup",
}


def _build_overview_embed(guild: discord.Guild, prefix: str) -> discord.Embed:
    e = discord.Embed(
        description=(
            "**AntiNuke** — protección profesional para tu servidor.\n"
            f"Usa `{prefix}help <categoría>` o el menú de abajo para ver los comandos de cada sección.\n\u200b"
        ),
        color=0x2b2d31,
    )
    e.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)
    if guild.icon:
        e.set_thumbnail(url=guild.icon.url)

    for key, data in CATEGORIES.items():
        count = len(data["commands"])
        e.add_field(
            name=f"{data['emoji']} {data['label']} — `{count} comandos`",
            value=data["description"],
            inline=False,
        )

    e.set_footer(text=f"Prefijo: {prefix} · Todos los horarios en UTC")
    return e


def _build_category_embed(guild: discord.Guild, prefix: str, cat_key: str) -> discord.Embed:
    data = CATEGORIES[cat_key]
    e = discord.Embed(
        title=f"{data['emoji']} {data['label']}",
        description=data["description"] + "\n\u200b",
        color=0x2b2d31,
    )
    e.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)
    if guild.icon:
        e.set_thumbnail(url=guild.icon.url)

    lines = [f"`{cmd}`\n{desc}" for cmd, desc in data["commands"]]
    half = (len(lines) + 1) // 2
    left = "\n\n".join(lines[:half])
    right = "\n\n".join(lines[half:])

    if right:
        e.add_field(name="\u200b", value=left, inline=True)
        e.add_field(name="\u200b", value=right, inline=True)
    else:
        e.add_field(name="\u200b", value=left, inline=False)

    e.set_footer(text=f"Prefijo: {prefix} · <obligatorio> [opcional]")
    return e


class CategorySelect(discord.ui.Select):
    def __init__(self, guild: discord.Guild, prefix: str):
        self.guild = guild
        self.prefix = prefix
        options = [
            discord.SelectOption(label=data["label"], value=key, emoji=data["emoji"])
            for key, data in CATEGORIES.items()
        ]
        super().__init__(placeholder="📖 Elige una categoría para ver sus comandos...", options=options)

    async def callback(self, interaction: discord.Interaction):
        embed = _build_category_embed(self.guild, self.prefix, self.values[0])
        await interaction.response.edit_message(embed=embed, view=self.view)


class HelpView(discord.ui.View):
    def __init__(self, guild: discord.Guild, prefix: str):
        super().__init__(timeout=180)
        self.add_item(CategorySelect(guild, prefix))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help", aliases=["h", "commands"])
    async def help_command(self, ctx, *, category: str = None):
        """Muestra la ayuda general o de una categoría específica."""
        config = db.get_guild(ctx.guild.id)
        prefix = config.get("prefix", ",")

        if category is None:
            embed = _build_overview_embed(ctx.guild, prefix)
            view = HelpView(ctx.guild, prefix)
            await ctx.send(embed=embed, view=view)
            return

        cat_key = category.lower().strip()
        cat_key = ALIASES.get(cat_key, cat_key)

        if cat_key not in CATEGORIES:
            available = " · ".join(f"`{k}`" for k in CATEGORIES)
            e = discord.Embed(
                description=f"Categoría `{category}` no encontrada.\nDisponibles: {available}",
                color=0x2b2d31,
            )
            e.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
            return await ctx.send(embed=e)

        embed = _build_category_embed(ctx.guild, prefix, cat_key)
        view = HelpView(ctx.guild, prefix)
        await ctx.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(Help(bot))
