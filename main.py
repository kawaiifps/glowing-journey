import discord
from discord import app_commands
from discord.ext import tasks
import os, datetime, re, asyncio, random

# --- CONFIGURATION ---
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1469674659380334593
FOUNDER_ROLE_ID = 1469706626897281107
STAFF_ROLE_ID = 1470085224435286120 
AUTO_ROLE_ID = 1470085549569212498
LOG_RECRU_ID = 1469706494487560456

# Salons
WELCOME_CHAN_ID = 1469699722846666762
LEAVE_CHAN_ID = 1469699902375198760
CAT_INFO_ID = 1469690712567316500
TICKET_LOG_CHAN = 1469706494487560456

def is_valid_hex(hex_code):
    return re.search(r'^#(?:[0-9a-fA-F]{3}){1,2}$', hex_code)

# --- SYSTÈME DE RECRUTEMENT ---
class CandidatureModal(discord.ui.Modal, title="Dossier Staff - L'Appartement de Sakuo"):
    pseudo = discord.ui.TextInput(label="Pseudo & Âge", placeholder="Ton pseudo & ton âge...")
    motive = discord.ui.TextInput(label="Tes motivations", style=discord.TextStyle.paragraph, min_length=20)

    async def on_submit(self, interaction: discord.Interaction):
        log_chan = interaction.guild.get_channel(LOG_RECRU_ID)
        embed = discord.Embed(title="📥 NOUVELLE CANDIDATURE", color=0xff69b4, timestamp=datetime.datetime.now())
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="👤 Candidat", value=interaction.user.mention)
        embed.add_field(name="🎮 Pseudo/Âge", value=self.pseudo.value)
        embed.add_field(name="❤️ Motivations", value=self.motive.value, inline=False)
        if log_chan:
            await log_chan.send(embed=embed)
            await interaction.response.send_message("✅ Ton dossier a été envoyé !", ephemeral=True)

class RecrutementView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="⭐ Postuler maintenant ⭐", style=discord.ButtonStyle.success, custom_id="kawail_v24")
    async def apply(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CandidatureModal())

# --- SYSTÈME D'EMBED PERSO ---
class EmbedModal(discord.ui.Modal, title="Créer une Annonce"):
    titre = discord.ui.TextInput(label="Titre", placeholder="Titre de l'embed...")
    description = discord.ui.TextInput(label="Message", style=discord.TextStyle.paragraph)
    couleur = discord.ui.TextInput(label="Couleur (Hex Code)", placeholder="#ff69b4", default="#ff69b4")
    async def on_submit(self, interaction: discord.Interaction):
        color_val = self.couleur.value if is_valid_hex(self.couleur.value) else "#ff69b4"
        embed = discord.Embed(title=self.titre.value, description=self.description.value, color=discord.Color.from_str(color_val))
        await interaction.channel.send(embed=embed)
        await interaction.response.send_message("✅ Embed envoyé !", ephemeral=True)

# --- SYSTÈME DE TICKETS ---
class TicketControl(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="🙋‍♂️ Prendre le ticket", style=discord.ButtonStyle.success, custom_id="claim_tkt")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        is_staff = any(role.id in [STAFF_ROLE_ID, FOUNDER_ROLE_ID] for role in interaction.user.roles)
        if not is_staff: return await interaction.response.send_message("❌ Seul le Staff peut traiter ce ticket.", ephemeral=True)
        button.disabled, button.label, button.style = True, "✅ Pris en charge", discord.ButtonStyle.secondary
        embed = interaction.message.embeds[0]
        embed.add_field(name="💼 Staff en charge", value=f"{interaction.user.mention}", inline=False)
        embed.color = discord.Color.gold()
        await interaction.response.edit_message(embed=embed, view=self)
    @discord.ui.button(label="🔒 Fermer", style=discord.ButtonStyle.danger, custom_id="close_tkt")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        is_staff = any(role.id in [STAFF_ROLE_ID, FOUNDER_ROLE_ID] for role in interaction.user.roles)
        if not is_staff: return await interaction.response.send_message("❌ Staff uniquement.", ephemeral=True)
        await interaction.channel.delete()

class TicketLauncher(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.select(
        placeholder="Comment pouvons-nous vous aider ?",
        options=[
            discord.SelectOption(label="Signaler un Bug", value="Bug", emoji="🛠️"),
            discord.SelectOption(label="Suggestion", value="Idée", emoji="💡"),
            discord.SelectOption(label="Plainte", value="Plainte", emoji="🚫")
        ],
        custom_id="tkt_sakuo_v4"
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        guild, cat = interaction.guild, interaction.guild.get_channel(CAT_INFO_ID)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.get_role(STAFF_ROLE_ID): discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.get_role(FOUNDER_ROLE_ID): discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        chan = await guild.create_text_channel(f"🏠-{select.values[0]}-{interaction.user.name}", category=cat, overwrites=overwrites)
        embed = discord.Embed(title="🎫 TICKET D'ASSISTANCE", color=0xff69b4, timestamp=datetime.datetime.now())
        embed.set_author(name=f"Utilisateur : {interaction.user.name}", icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="📂 Catégorie", value=f"`{select.values[0]}`", inline=True)
        embed.add_field(name="🆔 ID Client", value=f"`{interaction.user.id}`", inline=True)
        embed.add_field(name="📅 Compte créé le", value=interaction.user.created_at.strftime("%d/%m/%Y"), inline=True)
        embed.set_footer(text="L'appartement de Sakuo • Support Client")
        await chan.send(content=f"{interaction.user.mention} | <@&{STAFF_ROLE_ID}>", embed=embed, view=TicketControl())
        await interaction.response.send_message(f"✅ Ticket ouvert ici : {chan.mention}", ephemeral=True)

# --- BOT CORE ---
class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.all())
        self.tree = app_commands.CommandTree(self)
    async def setup_hook(self):
        self.add_view(TicketLauncher())
        self.add_view(TicketControl())
        self.add_view(RecrutementView())
        await self.tree.sync()
    async def on_ready(self):
        print(f"Bot Sakuo prêt !")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="L'appartement de Sakuo 🏠"))
    async def on_member_join(self, member):
        role = member.guild.get_role(AUTO_ROLE_ID)
        if role: await member.add_roles(role)
        chan = member.guild.get_channel(WELCOME_CHAN_ID)
        if chan:
            embed = discord.Embed(title="✨ Bienvenue !", description=f"Bienvenue {member.mention} dans **L'appartement de Sakuo** !", color=0xff69b4)
            await chan.send(embed=embed)

bot = MyBot()

# --- COMMANDES ---

@bot.tree.command(name="regles", description="Affiche le règlement de l'appartement")
@app_commands.checks.has_permissions(administrator=True)
async def regles(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📜 RÈGLEMENT DE L'APPARTEMENT DE SAKUO",
        description=(
            "Bienvenue parmi nous ! Pour que l'expérience reste agréable pour tous, "
            "merci de respecter les règles suivantes :\n\n"
            "**1️⃣ Respect & Courtoisie**\n"
            "Le respect est la base. Les insultes, le harcèlement et la toxicité ne sont pas tolérés.\n\n"
            "**2️⃣ Pas de Spam ni de Pub**\n"
            "Évitez de spammer les salons et ne faites pas de publicité sans autorisation (MP inclus).\n\n"
            "**3️⃣ Contenu Approprié**\n"
            "L'appartement est un lieu convivial. Pas de contenu NSFW, raciste, homophobe ou haineux.\n\n"
            "**4️⃣ Utilisation du Support**\n"
            "Utilisez les tickets de manière responsable. Le spam de tickets pourra entraîner un bannissement.\n\n"
            "**5️⃣ Règlement Rec Room**\n"
            "En jouant sur notre map, vous acceptez également de suivre le Code de Conduite officiel de Rec Room.\n\n"
            "---"
        ),
        color=0xff69b4
    )
    embed.add_field(
        name="🛡️ Sanctions", 
        value="Tout manquement à ces règles pourra donner lieu à un avertissement, un timeout ou un bannissement définitif.",
        inline=False
    )
    embed.set_footer(text="En restant sur ce serveur, vous acceptez ce règlement.")
    embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
    
    await interaction.channel.send(embed=embed)
    await interaction.response.send_message("✅ Le règlement a été posté !", ephemeral=True)

@bot.tree.command(name="setup_tickets", description="Déployer le panel de support")
@app_commands.checks.has_permissions(administrator=True)
async def setup_tickets(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🏠 Centre d'Assistance - L'Appartement de Sakuo",
        description=(
            "✨ **Bienvenue dans le support officiel de la map !**\n\n"
            "Un souci ou une idée géniale ? Notre staff est là pour vous.\n\n"
            "**Comment procéder ?**\n"
            "1️⃣ Choisissez une catégorie ci-dessous.\n"
            "2️⃣ Un salon privé sera ouvert avec l'équipe.\n"
            "3️⃣ Expliquez-nous tout en détail !\n\n"
            "⚠️ *Le spam de tickets est sanctionné.*"
        ),
        color=0xff69b4
    )
    embed.set_footer(text="Système de Support • Rec Room")
    await interaction.channel.send(embed=embed, view=TicketLauncher())
    await interaction.response.send_message("✅ Panel déployé !", ephemeral=True)

@bot.tree.command(name="giveaway", description="Lancer un giveaway")
@app_commands.checks.has_permissions(administrator=True)
async def giveaway(interaction: discord.Interaction, lot: str, temps_secondes: int):
    embed = discord.Embed(title="🎉 GIVEAWAY 🎉", description=f"Lot : **{lot}**\nRéagissez avec 🎉 !", color=0xff69b4)
    await interaction.response.send_message("Lancement...", ephemeral=True)
    msg = await interaction.channel.send(embed=embed)
    await msg.add_reaction("🎉")
    await asyncio.sleep(temps_secondes)
    msg = await interaction.channel.fetch_message(msg.id)
    users = [u async for u in msg.reactions[0].users() if not u.bot]
    if users:
        await interaction.channel.send(f"🎊 Bravo {random.choice(users).mention} ! Tu as gagné **{lot}** !")

@bot.tree.command(name="embed", description="Créer une annonce")
@app_commands.checks.has_permissions(manage_messages=True)
async def embed_cmd(interaction: discord.Interaction):
    await interaction.response.send_modal(EmbedModal())

@bot.tree.command(name="setup_recrutement", description="Panel de recrutement")
@app_commands.checks.has_permissions(administrator=True)
async def setup_recru(interaction: discord.Interaction):
    embed = discord.Embed(title="⭐ RECRUTEMENT STAFF", description="Postule pour rejoindre l'équipe !", color=0xff69b4)
    await interaction.channel.send(embed=embed, view=RecrutementView())
    await interaction.response.send_message("Panel envoyé.", ephemeral=True)

bot.run(TOKEN)
