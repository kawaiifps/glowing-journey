import discord
from discord import app_commands
from discord.ext import tasks
import os, datetime, re

# --- CONFIGURATION ---
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1469674659380334593
FOUNDER_ROLE_ID = 1469706626897281107
CAT_INFO_ID = 1469690712567316500
TICKET_LOG_CHAN = 1469706494487560456
BANNED_WORDS = ["insulte1", "insulte2", "fdp"]

def is_valid_hex(hex_code):
    return re.search(r'^#(?:[0-9a-fA-F]{3}){1,2}$', hex_code)

# --- FORMULAIRE EMBED ANNONCE ---
class EmbedModal(discord.ui.Modal, title="Annonce : L'appartement de Sakuo"):
    titre = discord.ui.TextInput(label="Titre", placeholder="Ex: Grande fête ce soir !", required=True)
    description = discord.ui.TextInput(label="Contenu", style=discord.TextStyle.paragraph, placeholder="Détails...", required=True)
    couleur = discord.ui.TextInput(label="Couleur Hex", placeholder="#ff69b4", default="#ff69b4", min_length=7, max_length=7)
    image = discord.ui.TextInput(label="Image", placeholder="Lien URL...", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        color_val = int(self.couleur.value.replace("#", ""), 16) if is_valid_hex(self.couleur.value) else 0xff69b4
        embed = discord.Embed(title=self.titre.value, description=self.description.value, color=color_val, timestamp=datetime.datetime.now())
        if self.image.value.startswith("http"): embed.set_image(url=self.image.value)
        embed.set_footer(text="Gestion Appartement Sakuo")
        await interaction.channel.send(embed=embed)
        await interaction.response.send_message("✨ Annonce envoyée !", ephemeral=True)

# --- GESTION DES TICKETS (TRAITEMENT & FERMETURE) ---
class TicketControl(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🙋‍♂️ Prendre le ticket", style=discord.ButtonStyle.success, custom_id="claim_tkt")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Vérification si c'est un staff
        if not any(role.id == FOUNDER_ROLE_ID for role in interaction.user.roles):
            return await interaction.response.send_message("Tu n'as pas la permission de traiter ce ticket.", ephemeral=True)
        
        button.disabled = True
        button.label = "✅ En cours de traitement"
        
        embed = interaction.message.embeds[0]
        embed.add_field(name="💼 Staff en charge", value=interaction.user.mention, inline=False)
        embed.color = discord.Color.orange()
        
        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.followup.send(f"Le ticket est désormais géré par {interaction.user.mention}.")

    @discord.ui.button(label="🔒 Fermer", style=discord.ButtonStyle.danger, custom_id="close_tkt")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        log_chan = interaction.guild.get_channel(TICKET_LOG_CHAN)
        if log_chan:
            log_embed = discord.Embed(title="Ticket Archivé", color=discord.Color.red(), timestamp=datetime.datetime.now())
            log_embed.add_field(name="Salon", value=interaction.channel.name)
            log_embed.add_field(name="Action par", value=interaction.user.name)
            await log_chan.send(embed=log_embed)
        await interaction.channel.delete()

class TicketLauncher(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        placeholder="Comment pouvons-nous vous aider ?",
        options=[
            discord.SelectOption(label="Signaler un Bug", value="bug", emoji="🛠️"),
            discord.SelectOption(label="Suggestion Map", value="idée", emoji="💡"),
            discord.SelectOption(label="Autre demande", value="autre", emoji="🏠")
        ],
        custom_id="tkt_select_sakuo"
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        guild = interaction.guild
        cat = guild.get_channel(CAT_INFO_ID)
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.get_role(FOUNDER_ROLE_ID): discord.PermissionOverwrite(read_messages=True, manage_channels=True)
        }
        
        chan = await guild.create_text_channel(f"🏠-{select.values[0]}-{interaction.user.name}", category=cat, overwrites=overwrites)
        
        # --- EMBED DÉVELOPPÉ DU TICKET ---
        embed = discord.Embed(
            title="🎫 NOUVEAU TICKET D'ASSISTANCE",
            description=f"Bienvenue {interaction.user.mention} dans votre espace de support.",
            color=0xff69b4,
            timestamp=datetime.datetime.now()
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="👤 Demandeur", value=interaction.user.name, inline=True)
        embed.add_field(name="📂 Catégorie", value=select.values[0].capitalize(), inline=True)
        embed.add_field(name="⏳ État", value="En attente d'un staff", inline=False)
        embed.set_footer(text="L'appartement de Sakuo • Système de Support")
        
        await chan.send(content=f"{interaction.user.mention} | <@&{FOUNDER_ROLE_ID}>", embed=embed, view=TicketControl())
        await interaction.response.send_message(f"✅ Ton ticket est prêt ici : {chan.mention}", ephemeral=True)

# --- BOT MAIN ---
class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.all())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.add_view(TicketLauncher())
        self.add_view(TicketControl()) # Indispensable pour que les boutons marchent après reboot
        await self.tree.sync()

    async def on_ready(self):
        print(f"Bot Sakuo opérationnel !")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="L'appartement de Sakuo 🏠"))

bot = MyBot()

@bot.tree.command(name="embed", description="Créer une annonce personnalisée")
@app_commands.checks.has_permissions(manage_messages=True)
async def embed_cmd(interaction: discord.Interaction):
    await interaction.response.send_modal(EmbedModal())

@bot.tree.command(name="setup_tickets", description="Déployer le panel de support")
@app_commands.checks.has_permissions(administrator=True)
async def setup_tickets(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🏠 Centre d'aide - L'appartement de Sakuo",
        description="Besoin d'aide ? Vous voulez proposer une amélioration pour la map Rec Room ?\n\nSélectionnez la catégorie ci-dessous pour parler avec notre équipe.",
        color=0xff69b4
    )
    embed.set_image(url="Lien_Dune_Belle_Image_RecRoom_Si_Tu_En_As_Une")
    await interaction.channel.send(embed=embed, view=TicketLauncher())
    await interaction.response.send_message("Panel installé !", ephemeral=True)

bot.run(TOKEN)
