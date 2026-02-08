import discord
from discord import app_commands
from discord.ext import tasks
import os, datetime, re

# --- CONFIGURATION ---
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1469674659380334593
FOUNDER_ROLE_ID = 1469706626897281107
STAFF_ROLE_ID = 1470085224435286120 
AUTO_ROLE_ID = 1470085549569212498 # Ton nouveau rôle automatique
CAT_INFO_ID = 1469690712567316500
TICKET_LOG_CHAN = 1469706494487560456
BANNED_WORDS = ["insulte1", "insulte2", "fdp"]

def is_valid_hex(hex_code):
    return re.search(r'^#(?:[0-9a-fA-F]{3}){1,2}$', hex_code)

# --- GESTION DES TICKETS ---
class TicketControl(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🙋‍♂️ Prendre le ticket", style=discord.ButtonStyle.success, custom_id="claim_tkt")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        is_staff = any(role.id in [STAFF_ROLE_ID, FOUNDER_ROLE_ID] for role in interaction.user.roles)
        if not is_staff:
            return await interaction.response.send_message("❌ Seul le Staff de l'Appartement peut faire ça !", ephemeral=True)
        
        button.disabled = True
        button.label = "✅ Pris en charge"
        button.style = discord.ButtonStyle.secondary
        
        embed = interaction.message.embeds[0]
        embed.add_field(name="💼 Staff en charge", value=f"{interaction.user.mention}", inline=False)
        embed.color = discord.Color.gold()
        
        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.followup.send(f"🛠️ {interaction.user.mention} s'occupe de votre demande !")

    @discord.ui.button(label="🔒 Fermer", style=discord.ButtonStyle.danger, custom_id="close_tkt")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        is_staff = any(role.id in [STAFF_ROLE_ID, FOUNDER_ROLE_ID] for role in interaction.user.roles)
        if not is_staff:
             return await interaction.response.send_message("❌ Demande à un Staff de fermer le ticket.", ephemeral=True)

        log_chan = interaction.guild.get_channel(TICKET_LOG_CHAN)
        if log_chan:
            log_embed = discord.Embed(title="Archive Ticket - Appartement", color=discord.Color.red(), timestamp=datetime.datetime.now())
            log_embed.add_field(name="Salon", value=interaction.channel.name, inline=True)
            log_embed.add_field(name="Fermé par", value=interaction.user.name, inline=True)
            await log_chan.send(embed=log_embed)
        
        await interaction.channel.delete()

class TicketLauncher(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        placeholder="Ouvrir un accès au support...",
        options=[
            discord.SelectOption(label="Signaler un Bug", value="bug", emoji="🛠️"),
            discord.SelectOption(label="Suggestion", value="idée", emoji="💡"),
            discord.SelectOption(label="Question / Autre", value="autre", emoji="🏠")
        ],
        custom_id="tkt_main_sakuo"
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        guild = interaction.guild
        cat = guild.get_channel(CAT_INFO_ID)
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.get_role(STAFF_ROLE_ID): discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.get_role(FOUNDER_ROLE_ID): discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        chan = await guild.create_text_channel(f"🏠-{select.values[0]}-{interaction.user.name}", category=cat, overwrites=overwrites)
        
        embed = discord.Embed(
            title="✨ SUPPORT : L'APPARTEMENT DE SAKUO",
            description=f"Bonjour {interaction.user.mention} !\nUn membre de l'équipe arrive.",
            color=0xff69b4,
            timestamp=datetime.datetime.now()
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text="Système de gestion - Rec Room Map")
        
        await chan.send(content=f"{interaction.user.mention} | <@&{STAFF_ROLE_ID}>", embed=embed, view=TicketControl())
        await interaction.response.send_message(f"✅ Ticket ouvert ici : {chan.mention}", ephemeral=True)

# --- FORMULAIRE ANNONCE ---
class EmbedModal(discord.ui.Modal, title="Annonce Appartement Sakuo"):
    titre = discord.ui.TextInput(label="Titre", required=True)
    description = discord.ui.TextInput(label="Contenu", style=discord.TextStyle.paragraph, required=True)
    couleur = discord.ui.TextInput(label="Hex (ex: #ff69b4)", default="#ff69b4", min_length=7, max_length=7)
    image = discord.ui.TextInput(label="Lien Image", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        color_val = int(self.couleur.value.replace("#", ""), 16) if is_valid_hex(self.couleur.value) else 0xff69b4
        embed = discord.Embed(title=self.titre.value, description=self.description.value, color=color_val, timestamp=datetime.datetime.now())
        if self.image.value and self.image.value.startswith("http"): embed.set_image(url=self.image.value)
        await interaction.channel.send(embed=embed)
        await interaction.response.send_message("✨ Envoyé !", ephemeral=True)

# --- BOT CORE ---
class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.all()) # Obligatoire pour l'autorole
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.add_view(TicketLauncher())
        self.add_view(TicketControl())
        await self.tree.sync()

    async def on_ready(self):
        print(f"Bot Sakuo opérationnel !")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="L'appartement de Sakuo 🏠"))

    # --- FONCTION AUTOROLE ---
    async def on_member_join(self, member):
        role = member.guild.get_role(AUTO_ROLE_ID)
        if role:
            try:
                await member.add_roles(role)
                print(f"Autorole : {role.name} donné à {member.name}")
            except Exception as e:
                print(f"Erreur autorole : {e}")

bot = MyBot()

@bot.tree.command(name="embed", description="Faire une annonce")
@app_commands.checks.has_permissions(manage_messages=True)
async def embed_cmd(interaction: discord.Interaction):
    await interaction.response.send_modal(EmbedModal())

@bot.tree.command(name="setup_tickets", description="Installer le support")
@app_commands.checks.has_permissions(administrator=True)
async def setup_tickets(interaction: discord.Interaction):
    embed = discord.Embed(title="🏠 Support de l'Appartement", description="Choisissez une catégorie pour ouvrir un ticket.", color=0xff69b4)
    await interaction.channel.send(embed=embed, view=TicketLauncher())
    await interaction.response.send_message("Panel installé.", ephemeral=True)

bot.run(TOKEN)
