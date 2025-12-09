import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()

# --- Configurações ---
TOKEN = os.getenv("DISCORD_TOKEN")
CATEGORY_OPEN_ID = int(os.getenv("CATEGORY_OPEN_ID"))
CATEGORY_CLOSED_ID = int(os.getenv("CATEGORY_CLOSED_ID"))
ROLE_ATENDIMENTO_ID = int(os.getenv("ROLE_ATENDIMENTO_ID"))
STAFF_ROLE_ID = int(os.getenv("ROLE_STAFF_ID"))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True 

bot = commands.Bot(command_prefix="!", intents=intents)

# --- VIEW DO TICKET ABERTO (Botão Fechar/Arquivar) ---
class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Encerrar e Arquivar", style=discord.ButtonStyle.danger, custom_id="btn_close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Encerrando atendimento...", ephemeral=True)
        
        # Tenta pegar o ID do usuário no tópico para remover o cargo
        user_id = None
        if interaction.channel.topic and interaction.channel.topic.isdigit():
            user_id = int(interaction.channel.topic)
        
        # Remove o cargo "Em Atendimento"
        guild = interaction.guild
        role_atendimento = guild.get_role(ROLE_ATENDIMENTO_ID)
        if user_id and role_atendimento:
            member = guild.get_member(user_id)
            if member:
                try:
                    await member.remove_roles(role_atendimento)
                except:
                    pass

        # --- AQUI ESTÁ A CORREÇÃO ---
        category_closed = guild.get_channel(CATEGORY_CLOSED_ID)
        if category_closed:
            # sync_permissions=True: Apaga as permissões antigas (do usuário) e copia as da categoria
            await interaction.channel.edit(
                category=category_closed, 
                name=f"closed-{interaction.channel.name}", 
                sync_permissions=True
            )
            
            await interaction.channel.send(f"✅ Atendimento encerrado por {interaction.user.mention}. Permissões sincronizadas com o arquivo.")
        else:
            await interaction.followup.send("Erro: Categoria de Arquivo não encontrada.", ephemeral=True)

# --- MODAL (FORMULÁRIO) ---
class TicketModal(discord.ui.Modal, title="Abrir Novo Chamado"):
    nome = discord.ui.TextInput(
        label="Seu Nome",
        placeholder="Como gostaria de ser chamado?",
        max_length=50
    )
    motivo = discord.ui.TextInput(
        label="Motivo do Contato",
        style=discord.TextStyle.paragraph,
        placeholder="Descreva brevemente o que você precisa...",
        max_length=500,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        category_open = guild.get_channel(CATEGORY_OPEN_ID)
        staff_role = guild.get_role(STAFF_ROLE_ID)
        role_atendimento = guild.get_role(ROLE_ATENDIMENTO_ID)
        log_channel = guild.get_channel(LOG_CHANNEL_ID)
        
        if not category_open or not staff_role:
            await interaction.response.send_message("Erro interno de configuração.", ephemeral=True)
            return

        channel_name = f"ticket-{interaction.user.name.lower().replace(' ', '-')}"
        existing_channel = discord.utils.get(guild.text_channels, name=channel_name)
        if existing_channel:
            await interaction.response.send_message(f"Você já possui um ticket aberto: {existing_channel.mention}", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            staff_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        ticket_channel = await guild.create_text_channel(
            name=channel_name, 
            category=category_open, 
            overwrites=overwrites,
            topic=str(interaction.user.id)
        )

        try:
            await interaction.user.add_roles(role_atendimento)
        except:
            pass

        embed_welcome = discord.Embed(
            title="Solicitação Recebida",
            description=f"Olá {interaction.user.mention}, um membro da equipe {staff_role.mention} irá atendê-lo em breve.",
            color=0xFFFFFF
        )
        embed_welcome.add_field(name="👤 Nome Informado", value=self.nome.value, inline=True)
        embed_welcome.add_field(name="📝 Motivo", value=self.motivo.value, inline=False)
        embed_welcome.set_footer(text="Nexit Software • Aguarde o atendimento")

        await ticket_channel.send(f"{interaction.user.mention} | {staff_role.mention}", embed=embed_welcome, view=TicketControlView())

        if log_channel:
            embed_log = discord.Embed(
                title="🔔 Novo Ticket Aberto",
                description=f"**Cliente:** {interaction.user.mention}\n**Canal:** {ticket_channel.mention}",
                color=0x5865F2
            )
            embed_log.add_field(name="Nome", value=self.nome.value, inline=True)
            embed_log.add_field(name="Motivo", value=self.motivo.value, inline=False)
            embed_log.set_footer(text=f"ID: {interaction.user.id}")

            view_link = discord.ui.View()
            view_link.add_item(discord.ui.Button(label="Ir para o Ticket 🚀", style=discord.ButtonStyle.link, url=ticket_channel.jump_url))

            await log_channel.send(embed=embed_log, view=view_link)

        await interaction.response.send_message(f"Ticket criado com sucesso: {ticket_channel.mention}", ephemeral=True)

# --- VIEW DO PAINEL PRINCIPAL ---
class MainTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Iniciar Atendimento", style=discord.ButtonStyle.primary, custom_id="btn_open_ticket")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketModal())

# --- EVENTOS ---

@bot.event
async def on_ready():
    print(f'✅ Bot Suporte (V4 Sync Permissions) Logado')
    bot.add_view(MainTicketView())
    bot.add_view(TicketControlView())

@bot.command()
async def setup_ticket(ctx):
    await ctx.message.delete()
    embed = discord.Embed(
        title="Central de Suporte",
        description="Clique abaixo e preencha o formulário para falar com nossa equipe.",
        color=0xFFFFFF
    )
    embed.set_footer(text="Nexit Software")
    await ctx.send(embed=embed, view=MainTicketView())

if TOKEN:
    bot.run(TOKEN)