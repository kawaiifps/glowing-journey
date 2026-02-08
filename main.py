import discord
from discord import app_commands
from discord.ext import tasks
import os, datetime, re

# --- CONFIGURATION ---
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1469674659380334593
FOUNDER_ROLE_ID = 1469706626897281107
STAFF_ROLE_ID = 1470085224435286120 
AUTO_ROLE_ID = 1470085549569212498

# Salons Arrivée / Départ
WELCOME_CHAN_ID = 1469699722846666762
LEAVE_CHAN_ID = 1469699902375198760

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
            return await interaction.response.send_message("❌ Seul le Staff peut faire ça !", ephemeral=True)
        
        button.disabled = True
        button.label = "✅ Pris en charge"
        button.style = discord.ButtonStyle.secondary
        
        embed = interaction.message.embeds[0]
        embed.add_field(name="💼 Staff en charge", value=f"{interaction.user.mention}", inline=False)
        embed.color = discord.Color.gold()
        
        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.followup.send(f"🛠️ {interaction.user.mention} s'occupe de la demande !")

    @discord.ui.button(label="🔒 Fermer", style=discord.ButtonStyle.danger, custom_id="close_tkt")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        is_staff = any(role.id in [STAFF_ROLE_ID, FOUNDER_ROLE_ID] for role in interaction.user.roles)
        if not is_staff:
             return await interaction.response.send_message("❌ Seul le Staff peut fermer.", ephemeral=True)

        log_chan = interaction.guild.get_channel(TICKET_LOG_CHAN)
        if log_chan:
            log_embed = discord.Embed(title="Archive Ticket", color=discord.Color.red(), timestamp=datetime.datetime.now())
            log_embed.add_field(name="Salon", value=interaction.channel.name)
            log_embed.add_field(name="Par", value=interaction.user.name)
            await log_chan.send(embed=log_embed)
        await interaction.channel.delete()

class TicketLauncher(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        placeholder="Ouvrir un ticket...",
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
        
        embed = discord.Embed(title="✨ SUPPORT SAKUO", description=f"Bonjour {interaction.user.mention}, un staff arrive.", color=0xff69b4)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        await chan.send(content=f"{interaction.user.mention} | <@&{STAFF_ROLE_ID}>", embed=embed, view=TicketControl())
        await interaction.response.send_message(f"✅ Ticket ouvert : {chan.mention}", ephemeral=True)

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
        print(f"Bot Sakuo prêt (Arrivée/Départ activés) !")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="L'appartement de Sakuo 🏠"))

    # --- ÉVÉNEMENT ARRIVÉE (BIENVENUE + AUTOROLE) ---
    async def on_member_join(self, member):
        # 1. Autorole
        role = member.guild.get_role(AUTO_ROLE_ID)
        if role:
            try: await member.add_roles(role)
            except: pass

        # 2. Message Bienvenue
        channel = member.guild.get_channel(WELCOME_CHAN_ID)
        if channel:
            embed = discord.Embed(
                title="✨ Bienvenue !",
                description=f"Bienvenue {member.mention} dans **L'appartement de Sakuo** ! \nOn est ravis de te voir ici.",
                color=0xff69b4,
                timestamp=datetime.datetime.now()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"Nous sommes maintenant {member.guild.member_count}")
            await channel.send(embed=embed)

    # --- ÉVÉNEMENT DÉPART (AUREVOIR) ---
    async def on_member_remove(self, member):
        channel = member.guild.get_channel(LEAVE_CHAN_ID)
        if channel:
            embed = discord.Embed(
                title="👋 Au revoir",
                description=f"**{member.name}** a quitté l'appartement. À bientôt !",
                color=discord.Color.red(),
                timestamp=datetime.datetime.now()
            )
            await channel.send(embed=embed)

bot = MyBot()

@bot.tree.command(name="embed", description="Faire une annonce")
@app_commands.checks.has_permissions(manage_messages=True)
async def embed_cmd(interaction: discord.Interaction):
    # (Modal identique au précédent)
    await interaction.response.send_modal(EmbedModal())

@bot.tree.command(name="setup_tickets", description="Installer le support")
@app_commands.checks.has_permissions(administrator=True)
async def setup_tickets(interaction: discord.Interaction):
    embed = discord.Embed(title="🏠 Support Sakuo", description="Besoin d'aide ? Ouvre un ticket ci-dessous.", color=0xff69b4)
    await interaction.channel.send(embed=embed, view=TicketLauncher())
    await interaction.response.send_message("Panel installé.", ephemeral=True)

bot.run(TOKEN)
