import discord
from discord import app_commands
from discord.ext import tasks
import os, datetime, re, asyncio

# --- CONFIGURATION DES IDS ---
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1469674659380334593
FOUNDER_ROLE_ID = 1469706626897281107
STAFF_ROLE_ID = 1470085224435286120 
AUTO_ROLE_ID = 1470085549569212498 # Rôle donné après validation du règlement

# Salons
WELCOME_CHAN_ID = 1469699722846666762
LEAVE_CHAN_ID = 1469699902375198760
CAT_INFO_ID = 1469690712567316500
TICKET_LOG_CHAN = 1469706494487560456

# --- UTILITAIRES ---
def is_valid_hex(hex_code):
    return re.search(r'^#(?:[0-9a-fA-F]{3}){1,2}$', hex_code)

# --- SYSTÈME DE VÉRIFICATION (BOUTON ACCEPTER) ---
class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ Accepter le règlement", style=discord.ButtonStyle.success, custom_id="verify_user")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(AUTO_ROLE_ID)
        if role in interaction.user.roles:
            return await interaction.response.send_message("Tu as déjà accepté le règlement !", ephemeral=True)
        
        try:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("✨ Bienvenue officiellement ! Tu as maintenant accès à tout l'appartement.", ephemeral=True)
        except:
            await interaction.response.send_message("❌ Erreur : Vérifie que mon rôle est au-dessus du rôle membre.", ephemeral=True)

# --- GESTION DES TICKETS (TRAITEMENT & FERMETURE) ---
class TicketControl(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🙋‍♂️ Prendre le ticket", style=discord.ButtonStyle.success, custom_id="claim_tkt")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        is_staff = any(role.id in [STAFF_ROLE_ID, FOUNDER_ROLE_ID] for role in interaction.user.roles)
        if not is_staff:
            return await interaction.response.send_message("❌ Seul le Staff peut faire ça !", ephemeral=True)
        
        button.disabled = True
        button.label = "✅ Pris en charge"
        button.style = discord.ButtonStyle.secondary
        
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
        placeholder="Besoin d'aide sur la map ?",
        options=[
            discord.SelectOption(label="Signaler un Bug", value="Bug", emoji="🛠️"),
            discord.SelectOption(label="Suggestion", value="Idée", emoji="💡"),
            discord.SelectOption(label="Plainte", value="Plainte", emoji="🚫")
        ],
        custom_id="tkt_launcher_final"
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        guild = interaction.guild
        cat = guild.get_channel(CAT_INFO_ID)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.get_role(STAFF_ROLE_ID): discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        chan = await guild.create_text_channel(f"🏠-{select.values[0]}-{interaction.user.name}", category=cat, overwrites=overwrites)
        
        embed = discord.Embed(title="🎫 TICKET DE SUPPORT", color=0xff69b4, timestamp=datetime.datetime.now())
        embed.set_author(name=f"Utilisateur : {interaction.user.name}", icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="📂 Catégorie", value=f"`{select.values[0]}`", inline=True)
        embed.add_field(name="🆔 ID", value=f"`{interaction.user.id}`", inline=True)
        embed.set_footer(text="L'appartement de Sakuo")
        
        await chan.send(content=f"{interaction.user.mention} | <@&{STAFF_ROLE_ID}>", embed=embed, view=TicketControl())
        await interaction.response.send_message(f"✅ Ticket ouvert : {chan.mention}", ephemeral=True)

# --- BOT CORE ---
class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.all())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.add_view(VerifyView())
        self.add_view(TicketLauncher())
        self.add_view(TicketControl())
        await self.tree.sync()

    async def on_ready(self):
        print(f"Bot Sakuo opérationnel !")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="L'appartement de Sakuo 🏠"))

    async def on_member_join(self, member):
        chan = member.guild.get_channel(WELCOME_CHAN_ID)
        if chan:
            embed = discord.Embed(title="✨ Bienvenue !", description=f"Bienvenue {member.mention} ! Valide le règlement pour entrer.", color=0xff69b4)
            await chan.send(embed=embed)

    async def on_member_remove(self, member):
        chan = member.guild.get_channel(LEAVE_CHAN_ID)
        if chan: await chan.send(f"👋 **{member.name}** a quitté l'appartement.")

bot = MyBot()

# --- COMMANDES SLASH ---

@bot.tree.command(name="regles", description="Poster le règlement avec bouton")
@app_commands.checks.has_permissions(administrator=True)
async def regles(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📜 RÈGLEMENT DE L'APPARTEMENT DE SAKUO",
        description=(
            "Bienvenue ! Pour accéder au reste du serveur, merci de lire et d'accepter nos règles :\n\n"
            "**1️⃣ Respect** : Pas d'insultes ni de toxicité.\n"
            "**2️⃣ Pub** : Interdite sous toutes ses formes.\n"
            "**3️⃣ Support** : Utilisez le système de tickets pour nous parler.\n\n"
            "Clique sur le bouton ci-dessous pour débloquer l'accès ! ✅"
        ),
        color=0xff69b4
    )
    await interaction.channel.send(embed=embed, view=VerifyView())
    await interaction.response.send_message("✅ Règlement posté !", ephemeral=True)

@bot.tree.command(name="setup_tickets", description="Déployer le panel de support")
@app_commands.checks.has_permissions(administrator=True)
async def setup_tickets(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🏠 Centre d'Assistance",
        description="Besoin d'aide ? Un bug sur la map ?\n\n1️⃣ Choisissez une catégorie.\n2️⃣ Un staff vous répondra.",
        color=0xff69b4
    )
    await interaction.channel.send(embed=embed, view=TicketLauncher())
    await interaction.response.send_message("✅ Support installé.", ephemeral=True)

@bot.tree.command(name="clear", description="Nettoyer le salon")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, nombre: int):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=nombre)
    await interaction.followup.send(f"✅ {len(deleted)} messages supprimés.", ephemeral=True)

@bot.tree.command(name="warn", description="Avertir un membre")
@app_commands.checks.has_permissions(manage_messages=True)
async def warn(interaction: discord.Interaction, membre: discord.Member, raison: str):
    try: await membre.send(f"⚠️ Tu as été averti sur **L'appartement de Sakuo** : {raison}")
    except: pass
    await interaction.response.send_message(f"⚠️ {membre.mention} averti pour : {raison}")

@bot.tree.command(name="timeout", description="Exclure un membre temporairement")
@app_commands.checks.has_permissions(moderate_members=True)
async def timeout(interaction: discord.Interaction, membre: discord.Member, minutes: int, raison: str):
    await membre.timeout(datetime.timedelta(minutes=minutes), reason=raison)
    await interaction.response.send_message(f"⏳ {membre.mention} exclu {minutes} min pour : {raison}")

@bot.tree.command(name="ban", description="Bannir un membre")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, membre: discord.Member, raison: str):
    await membre.ban(reason=raison)
    await interaction.response.send_message(f"🔨 {membre.name} banni pour : {raison}")

bot.run(TOKEN)
