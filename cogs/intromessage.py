import discord
from discord.ext import commands
from discord import app_commands
import os
import easy_pil
import random
from dotenv import load_dotenv
from PIL import ImageFilter, ImageFont
from utils import DEFAULT_FONT_PATH
from db_utils import *


load_dotenv(".secrets/.env")
SSL_MAIN_SERVER_ID = int(os.getenv("SSL_MAIN_SERVER_ID"))
SSL_HELP_CHANNEL_ID = int(os.getenv("SSL_MAIN_SERVER_SSL_HELP_CHANNEL"))
SSL_NEW_PLAYER_GUIDE_CHANNEL_ID = int(os.getenv("SSL_MAIN_SERVER_NEW_PLAYER_GUIDE_CHANNEL"))
SSL_BOD_ROLE_ID = int(os.getenv("SSL_MAIN_SERVER_BOD_ROLE_ID"))
SSL_ACADEMY_COACHES_ROLE_ID = int(os.getenv("SSL_MAIN_SERVER_ACADEMY_COACHES_ROLE_ID"))
# TEST_ID = int(os.getenv('DISCORD_TEST_ID'))



class IntroMessage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(name='test_join', description='Simulates a member joining')
    # @discord.app_commands.guilds(discord.Object(id=TEST_ID))
    async def test_join(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.on_member_join(interaction.user)
        await interaction.followup.send("Simulated join event triggered.")
        
    @app_commands.command(name='toggle_welcome', description='Toggles the activation of the welcome message in the server')
    # @discord.app_commands.guilds(discord.Object(id=TEST_ID)) # Removed to have it accessible for all servers
    async def toggle_welcome(self, interaction: discord.Interaction):
        # Check if user has admin permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "You must be a server administrator to use this command.",
                ephemeral=True
            )
            return
    
        guild_id = interaction.guild.id
        current_status = get_welcome_status(guild_id)
    
        # Flip the toggle
        new_status = not current_status
        set_welcome_status(guild_id, new_status)
    
        await interaction.response.send_message(
            f"Welcome messages are now **{'enabled' if new_status else 'disabled'}** for this server.",
            ephemeral=True
        )
        
    @commands.Cog.listener()
    async def on_ready(self):
        print("cog.intromessage is online!")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if not get_welcome_status(member.guild.id):
            return  # Skip if disabled
      
        welcome_channel = member.guild.system_channel
        if not welcome_channel:
            # Skip if system channel is not set
            return
        
        ssl_main_server_id=SSL_MAIN_SERVER_ID

        if member.guild.id == ssl_main_server_id:
            new_player_guide_channel_id = SSL_NEW_PLAYER_GUIDE_CHANNEL_ID
            ssl_help_channel_id = SSL_HELP_CHANNEL_ID
            bod_role_id = SSL_BOD_ROLE_ID
            academy_coaches_role_id = SSL_ACADEMY_COACHES_ROLE_ID

            welcome_message = (
                f"Hey {member.name}! Welcome to {member.guild.name}!\n\n"
                f"The SSL is a simulation league within the world of soccer/football." 
                f"The league takes the Be-a-pro game mode to a multiplayer environment where"
                f"users from across the globe create their own player, join one of the teams,"
                f"fight for the league or cup championships and watch commentated games"
                f"simulated through Football Manager.\n\n"
                f"Read more about how you can start your career in the" 
                f"<#{new_player_guide_channel_id}>.\n\n"
                f"If you need any help you can contact any of the <@&{academy_coaches_role_id}> or" 
                f"<@&{bod_role_id}>, and of course you can always ask question"
                f"in <#{ssl_help_channel_id}>"
            )
        else:
            welcome_message = f"Hello there {member.name}! Welcome to {member.guild.name}!"    

        images = os.listdir("./graphics/welcome_images")
        random_image = random.choice(images)
        
        bg = easy_pil.Editor(f"./graphics/welcome_images/{random_image}").resize((1920, 1080))
        bg.image = bg.image.filter(ImageFilter.GaussianBlur(radius=5))

        avatar_image = await easy_pil.load_image_async(str(member.avatar.url))
        avatar = easy_pil.Editor(avatar_image).resize((250, 250)).circle_image()

        # Fix the font module reference (easy_pil.Font, not easy.pil.Font)
        font_big = ImageFont.truetype(DEFAULT_FONT_PATH, size=135)
        font_small = ImageFont.truetype(DEFAULT_FONT_PATH, size=65)

        bg.paste(avatar, (835, 340))
        bg.ellipse((835, 340), 250, 250, outline="#ED9523", stroke_width=5)

        x1, y1 = (960, 620) #Coordinates for the big welcome text in image
        offsets = [(-4, 0), (4, 0), (0, -4), (0, 4)]

        # Draw outline by drawing text shifted in four directions
        for dx, dy in offsets:
            bg.text((x1 + dx, y1 + dy), f"Greetings!", font=font_big, color="#ffffff", align="center")
        # Draw main text on top
        bg.text((x1, y1), f"Greetings!", font=font_big, color="#070B51", align="center")

        x2, y2 = (960, 800) #Coordinates for the small member count text in image
        offset = 5
        offsets = [(-offset, 0), (offset, 0), (0, -offset), (0, offset)]

        # Draw outline by drawing text shifted in four directions
        for dx, dy in offsets:
            bg.text((x2 + dx, y2 + dy),  f"{member.name} is here!", font=font_small, color="#ffffff", align="center")
        # Draw main text on top
        bg.text((x2, y2),  f"{member.name} is here!", font=font_small, color="#070B51", align="center")

        image_file = discord.File(fp=bg.image_bytes, filename="welcome.png")  # Use a fixed filename for easy caching

        await welcome_channel.send(welcome_message, file=image_file)

async def setup(bot):
    await bot.add_cog(IntroMessage(bot))
