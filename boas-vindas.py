import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

# Recupera as configurações
TOKEN = os.getenv("DISCORD_TOKEN")
WELCOME_CHANNEL_ID = int(os.getenv("WELCOME_CHANNEL_ID"))
ROLE_CLIENTE_ID = int(os.getenv("ROLE_CLIENTE_ID"))
ROLE_VISITANTE_ID = int(os.getenv("ROLE_VISITANTE_ID"))

# Configuração de Permissões
intents = discord.Intents.default()
intents.members = True 
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- CLASSE DOS BOTÕES (A VIEW) ---
class WelcomeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) 

    # Removi os emojis ("emoji=...") e mantive apenas o texto limpo
    @discord.ui.button(label="Já sou Cliente Nexit", style=discord.ButtonStyle.success, custom_id="btn_cliente")
    async def btn_cliente_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(ROLE_CLIENTE_ID)
        if role:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"Seja bem-vindo de volta. O cargo {role.mention} foi adicionado.", ephemeral=True)
        else:
            await interaction.response.send_message("Erro: Cargo não encontrado.", ephemeral=True)

    @discord.ui.button(label="Apenas Visitando", style=discord.ButtonStyle.primary, custom_id="btn_visitante")
    async def btn_visitante_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(ROLE_VISITANTE_ID)
        if role:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"Bem-vindo à comunidade. O cargo {role.mention} foi adicionado.", ephemeral=True)
        else:
            await interaction.response.send_message("Erro: Cargo não encontrado.", ephemeral=True)

# --- FUNÇÃO PARA CRIAR O EMBED (CARD) ---
def criar_embed_boas_vindas(member_mention):
    # Cria o card com a cor Branca (0xFFFFFF)
    embed = discord.Embed(
        description=f"Olá {member_mention}, seja muito bem-vindo(a) à **Nexit**.\n\nPara liberarmos os canais ideais para você, por favor **escolha uma das opções abaixo**:",
        color=0xFFFFFF 
    )
    # Adiciona um rodapé simples para dar acabamento, igual na referência
    embed.set_footer(text="Selecione seu perfil")
    return embed

# --- EVENTOS E COMANDOS ---

@bot.event
async def on_ready():
    print(f'✅ Logado como {bot.user} (ID: {bot.user.id})')
    print('--- Sistema Nexit Iniciado ---')
    bot.add_view(WelcomeView())

@bot.command()
async def teste(ctx):
    # Gera o embed usando a função criada acima
    embed = criar_embed_boas_vindas(ctx.author.mention)
    # Envia o embed e a view (botões)
    await ctx.send(embed=embed, view=WelcomeView())

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        embed = criar_embed_boas_vindas(member.mention)
        await channel.send(embed=embed, view=WelcomeView())

# Inicia o bot
if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ Erro: Token não encontrado no arquivo .env")