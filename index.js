import discord
from discord import app_commands
from discord.ext import tasks
import os, json, asyncio, datetime, random, re, aiohttp

# --- CONFIGURATION ---
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1469674659380334593
LOG_RECRU_ID = 1469706756115529799
RECRUT_CHANNEL_ID = 1469694484722880594
FOUNDER_ROLE_ID = 1469706626897281107
CAT_INFO_ID = 1469690712567316500
TICKET_LOG_CHAN = 1469706494487560456
BANNED_WORDS = ["insulte1", "insulte2", "fdp"]

# Configuration API Twitch & YouTube
YT_CHANNEL_ID = "UCAIHAZYHfPVAdDx7MzDpGvg" # Remplace par ton ID YouTube
TWITCH_USER = "kawail_fps"
TWITCH_CLIENT_ID = "58mv5cbsbyescfioiq32q83lt541s8"
TWITCH_CLIENT_SECRET = "uhi30ge4bsw6fyb62w9bblzmmh9llb"

def parse_duration(duration_str):
    units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400, 'w': 604800, 'mo': 2592000}
    match = re.match(r"(\d+)(s|m|h|d|w|mo)", duration_str.lower())
    if match:
        amount, unit = match.groups()
        return int(amount) * units[unit]
    return None

# --- SYSTÈME DE TICKETS DÉVELOPPÉ ---
class TicketControl(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Fermer le ticket", style=discord.ButtonStyle.danger, custom_id="close_tkt")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        log_chan = interaction.guild.get_channel(TICKET_LOG_CHAN)
        embed = discord.Embed(title="🔒 Archive Support", color=discord.Color.dark_grey(), timestamp=datetime.datetime.now())
        embed.add_field(name="Ticket", value=interaction.channel.name, inline=True)
        embed.add_field(name="Fermé par", value=interaction.user.name, inline=True)
        if log_chan: await log_chan.send(embed=embed)
        await interaction.channel.delete()

class TicketLauncher(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        placeholder="Ouvrir un ticket de support...",
        options=[
            discord.SelectOption(label="Aide", value="aide", emoji="🆘", description="Assistance technique et aide développeur"),
            discord.SelectOption(label="Problème", value="prob", emoji="⚠️", description="Signaler un bug ou un comportement"),
            discord.SelectOption(label="Autre / Partenariat", value="part", emoji="🤝", description="Demandes de partenariat ou autres")
        ],
        custom_id="tkt_select_v2"
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        guild = interaction.guild
        cat = guild.get_channel(CAT_INFO_ID)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.get_role(FOUNDER_ROLE_ID): discord.PermissionOverwrite(read_messages=True)
        }
        chan = await guild.create_text_channel(f"🎫-{select.values[0]}-{interaction.user.name}", category=cat, overwrites=overwrites)
        
        embed = discord.Embed(title=f"Support : {select.values[0].upper()}", color=discord.Color.blue())
        if select.values[0] == "aide":
            embed.description = "Posez votre question technique ici. Un développeur vous répondra."
        elif select.values[0] == "prob":
            embed.description = "Décrivez le problème ou bug rencontré avec un maximum de détails."
        else:
            embed.description = "Présentez votre demande de partenariat ou votre sujet divers."
            
        await chan.send(content=f"{interaction.user.mention} | <@&{FOUNDER_ROLE_ID}>", embed=embed, view=TicketControl())
        await interaction.response.send_message(f"✅ Ticket ouvert : {chan.mention}", ephemeral=True)

# --- BOT CORE & NOTIFICATIONS ---
class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.all())
        self.tree = app_commands.CommandTree(self)
        self.last_vid = None
        self.is_live = False
        self.twitch_token = None

    async def get_twitch_token(self):
        async with aiohttp.ClientSession() as session:
            url = f"https://id.twitch.tv/oauth2/token?client_id={TWITCH_CLIENT_ID}&client_secret={TWITCH_CLIENT_SECRET}&grant_type=client_credentials"
            async with session.post(url) as r:
                data = await r.json()
                self.twitch_token = data.get("access_token")

    @tasks.loop(minutes=5)
    async def notif_loop(self):
        chan = self.get_channel(RECRUT_CHANNEL_ID)
        if not chan: return
        async with aiohttp.ClientSession() as session:
            # YouTube Check
            async with session.get(f"https://www.youtube.com/feeds/videos.xml?channel_id={YT_CHANNEL_ID}") as r:
                if r.status == 200:
                    text = await r.text()
                    v_id = text.split('<yt:videoId>')[1].split('</yt:videoId>')[0]
                    if self.last_vid and self.last_vid != v_id:
                        await chan.send(f"🎥 **@everyone Nouvelle vidéo YouTube !**\nhttps://www.youtube.com/watch?v={v_id}")
                    self.last_vid = v_id

            # Twitch Check
            if not self.twitch_token: await self.get_twitch_token()
            headers = {"Client-ID": TWITCH_CLIENT_ID, "Authorization": f"Bearer {self.twitch_token}"}
            async with session.get(f"https://api.twitch.tv/helix/streams?user_login={TWITCH_USER}", headers=headers) as r:
                if r.status == 200:
                    data = await r.json()
                    currently_live = len(data["data"]) > 0
                    if currently_live and not self.is_live:
                        title = data["data"][0]["title"]
                        await chan.send(f"🔴 **@everyone KAWIL_FPS est en LIVE sur Twitch !**\nTITRE: *{title}*\nhttps://twitch.tv/{TWITCH_USER}")
                    self.is_live = currently_live

    async def setup_hook(self):
        self.add_view(TicketLauncher())
        self.notif_loop.start()
        await self.tree.sync()

    async def on_ready(self):
        print(f"Bot connecté : {self.user.name}")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Kawail_FPS 🛠️"))

    async def on_message(self, message):
        if message.author.bot: return
        is_staff = any(role.id == FOUNDER_ROLE_ID for role in message.author.roles)
        if not is_staff:
            if "http" in message.content or "discord.gg/" in message.content:
                await message.delete()
            if any(word in message.content.lower() for word in BANNED_WORDS):
                await message.delete()

bot = MyBot()

@bot.tree.command(name="setup_tickets", description="Envoie le panel de tickets")
@app_commands.checks.has_permissions(administrator=True)
async def setup_tickets(interaction: discord.Interaction):
    embed = discord.Embed(title="🎫 Support Kawail_FPS", description="Choisissez une catégorie pour ouvrir un ticket.", color=discord.Color.blue())
    await interaction.channel.send(embed=embed, view=TicketLauncher())
    await interaction.response.send_message("Panel envoyé !", ephemeral=True)

bot.run(TOKEN)
