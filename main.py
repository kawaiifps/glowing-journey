import discord
from discord import app_commands
from discord.ext import tasks
import os, datetime, re, asyncio

# --- CONFIGURATION ---
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1469674659380334593
FOUNDER_ROLE_ID = 1469706626897281107
STAFF_ROLE_ID = 1470085224435286120 
AUTO_ROLE_ID = 1470085549569212498

# Salons
WELCOME_CHAN_ID = 1469699722846666762
LEAVE_CHAN_ID = 1469699902375198760
CAT_INFO_ID = 1469690712567316500
TICKET_LOG_CHAN = 1469706494487560456

def is_valid_hex(hex_code):
    return re.search(r'^#(?:[0-9a-fA-F]{3}){1,2}$', hex_code)

# --- SYSTÈME DE TICKETS ---
class TicketControl(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🙋‍♂️ Prendre le ticket", style=discord.ButtonStyle.success, custom_id="claim_tkt")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        is_staff = any(role.id in [STAFF_ROLE_ID, FOUNDER_ROLE_ID] for role in interaction.user.roles)
        if not is_staff:
            return await interaction.response.send_message("❌ Seul le Staff peut traiter ce ticket.", ephemeral=True)
        
        button.disabled = True
        button.label = "✅ Pris en charge"
        button.style = discord.ButtonStyle.secondary
        
        embed = interaction.message.embeds[0]
        embed.add_field(name="💼 Staff en charge", value=f"{interaction.user.mention}", inline=False)
        embed.color = discord.Color.gold()
        
        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.followup.send(f"🛠️ {interaction.user.mention} s'occupe de vous !")

    @discord.ui.button(label="🔒 Fermer", style=discord.ButtonStyle.danger, custom_id="close_tkt")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        is_staff = any(role.id in [STAFF_ROLE_ID, FOUNDER_ROLE_ID] for role in interaction.user.roles)
        if not is_staff: return await interaction.response.send_message("❌ Staff uniquement.", ephemeral=True)
        
        log_chan = interaction.guild.get_channel(TICKET_LOG_CHAN)
        if log_chan:
            log_embed = discord.Embed(title="Archive Ticket", color=discord.Color.red(), timestamp=datetime.datetime.now())
            log_embed.add_field(name="Salon", value=interaction.channel.name)
            log_embed.add_field(name="Fermé par", value=interaction.user.name)
            await log_chan.send(embed=log_embed)
        await interaction.channel.delete()

class TicketLauncher(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        placeholder="Comment pouvons-nous vous aider ?",
        options=[
            discord.SelectOption(label="Signaler un Bug", value="Bug", emoji="🛠️", description="Un problème sur la map Rec Room ?"),
            discord.SelectOption(label="Suggestion", value="Idée", emoji="💡", description="Une idée pour l'appartement ?"),
            discord.SelectOption(label="Plainte", value="Plainte", emoji="🚫", description="Signaler un comportement.")
        ],
        custom_id="tkt_sakuo_v4"
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
        await self.tree.sync()

    async def on_ready(self):
        print(f"Bot Sakuo prêt et connecté !")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="L'appartement de Sakuo 🏠"))

    async def on_member_join(self, member):
        role = member.guild.get_role(AUTO_ROLE_ID)
        if role: await member.add_roles(role)
        chan = member.guild.get_channel(WELCOME_CHAN_ID)
        if chan:
            embed = discord.Embed(title="✨ Bienvenue !", description=f"Bienvenue {member.mention} dans **L'appartement de Sakuo** !", color=0xff69b4)
            embed.set_thumbnail(url=member.display_avatar.url)
            await chan.send(embed=embed)

    async def on_member_remove(self, member):
        chan = member.guild.get_channel(LEAVE_CHAN_ID)
        if chan: await chan.send(f"👋 **{member.name}** a quitté l'appartement. À bientôt !")

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

@bot.tree.command(name="clear", description="Supprime un nombre de messages")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, nombre: int):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=nombre)
    await interaction.followup.send(f"✅ {len(deleted)} messages ont été supprimés.", ephemeral=True)

@bot.tree.command(name="warn", description="Avertir un membre")
@app_commands.checks.has_permissions(manage_messages=True)
async def warn(interaction: discord.Interaction, membre: discord.Member, raison: str):
    try: await membre.send(f"⚠️ Avertissement : **L'appartement de Sakuo**\nRaison : {raison}")
    except: pass
    await interaction.response.send_message(f"⚠️ {membre.mention} a été averti pour : {raison}")

@bot.tree.command(name="timeout", description="Exclure temporairement")
@app_commands.checks.has_permissions(moderate_members=True)
async def timeout(interaction: discord.Interaction, membre: discord.Member, minutes: int, raison: str):
    await membre.timeout(datetime.timedelta(minutes=minutes), reason=raison)
    await interaction.response.send_message(f"⏳ {membre.mention} exclu {minutes} min. Raison : {raison}")

@bot.tree.command(name="ban", description="Bannir un membre")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, membre: discord.Member, raison: str):
    await membre.ban(reason=raison)
    await interaction.response.send_message(f"🔨 {membre.name} banni. Raison : {raison}")

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

bot.run(TOKEN)
