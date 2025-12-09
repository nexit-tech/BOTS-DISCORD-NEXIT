import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import aiohttp # Biblioteca para enviar dados pro n8n sem travar o bot

load_dotenv()

# --- Configurações ---
TOKEN = os.getenv("DISCORD_TOKEN")
CATEGORY_NEX_ID = int(os.getenv("CATEGORY_NEX_ID"))
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- VIEW DE CONTROLE (Botão Encerrar Conversa) ---
class NexControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Encerrar Conversa", style=discord.ButtonStyle.danger, custom_id="btn_close_nex")
    async def close_conversation(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Encerrando conexão com NEX...", ephemeral=True)
        import asyncio
        await asyncio.sleep(3)
        await interaction.channel.delete()

# --- VIEW PRINCIPAL (Botão Falar com NEX) ---
class NexStartView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Conectar ao NEX", style=discord.ButtonStyle.success, custom_id="btn_start_nex")
    async def start_nex(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        category = guild.get_channel(CATEGORY_NEX_ID)
        
        if not category:
            await interaction.response.send_message("Erro: Categoria NEX não configurada.", ephemeral=True)
            return

        # Verifica se já existe canal
        channel_name = f"nex-{interaction.user.name.lower().replace(' ', '-')}"
        existing_channel = discord.utils.get(guild.text_channels, name=channel_name)
        
        if existing_channel:
            await interaction.response.send_message(f"Você já tem uma conexão ativa em {existing_channel.mention}", ephemeral=True)
            return

        # Cria canal privado
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        channel = await guild.create_text_channel(name=channel_name, category=category, overwrites=overwrites)

        # Mensagem de Boas-vindas do NEX
        embed = discord.Embed(
            description=f"Olá {interaction.user.mention}. Eu sou o **NEX**, a Inteligência Artificial da Nexit.\n\nEstou aqui para tirar suas dúvidas sobre nossos softwares, serviços e agendar reuniões com nosso time comercial.\n\n**Pode perguntar, estou te ouvindo...**",
            color=0xFFFFFF
        )
        embed.set_footer(text="Nexit AI • Powered by NEXIT")
        
        await channel.send(embed=embed, view=NexControlView())
        await interaction.response.send_message(f"Conexão estabelecida: {channel.mention}", ephemeral=True)

# --- LÓGICA DE CONVERSA (A PONTE COM O N8N) ---
@bot.event
async def on_message(message):
    # Ignora mensagens do próprio bot
    if message.author.bot:
        return

    # Verifica se a mensagem foi enviada em um canal de atendimento do NEX
    # A lógica aqui é: O canal deve estar na categoria do NEX
    if message.channel.category_id == CATEGORY_NEX_ID:
        
        # Mostra "NEX está digitando..."
        async with message.channel.typing():
            try:
                # Prepara os dados pro n8n
                payload = {
                    "content": message.content,
                    "user_id": str(message.author.id),
                    "user_name": message.author.name,
                    "channel_id": str(message.channel.id)
                }

                # Envia pro n8n
                async with aiohttp.ClientSession() as session:
                    async with session.post(N8N_WEBHOOK_URL, json=payload) as response:
                        if response.status == 200:
                            # Tenta pegar resposta JSON. Se n8n mandar texto puro, ajustamos aqui.
                            try:
                                data = await response.json()
                                resposta_ia = data.get("output", "Recebi, mas o n8n não mandou o campo 'output'.")
                            except:
                                # Se der erro no JSON, pega o texto puro
                                resposta_ia = await response.text()
                            
                            # Envia a resposta do NEX no canal
                            await message.channel.send(resposta_ia)
                        else:
                            await message.channel.send(f"⚠️ Erro de comunicação com o servidor: {response.status}")
            
            except Exception as e:
                await message.channel.send(f"⚠️ Ocorreu um erro ao processar sua mensagem: {e}")

    # Processa comandos (importante para o !setup_nex funcionar)
    await bot.process_commands(message)

# --- SETUP COMANDO ---
@bot.event
async def on_ready():
    print(f'✅ NEX AI Logado e Operante')
    bot.add_view(NexStartView())
    bot.add_view(NexControlView())

@bot.command()
async def setup_nex(ctx):
    await ctx.message.delete()
    embed = discord.Embed(
        title="Fale com o NEX",
        description="Dúvidas sobre nossos serviços? Quer agendar uma reunião?\n\nO **NEX**, nossa Inteligência Artificial, está pronto para te atender instantaneamente 24h por dia.",
        color=0xFFFFFF
    )
    # Adicione uma imagem se quiser: embed.set_image(url="URL_DA_FOTO_DO_ROBO")
    embed.set_footer(text="Nexit Software • AI Assistant")
    
    await ctx.send(embed=embed, view=NexStartView())

if TOKEN:
    bot.run(TOKEN)