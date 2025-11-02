import discord
from discord.ext import commands
from discord import app_commands
import os
import easy_pil
import random
from dotenv import load_dotenv


load_dotenv(".secrets/.env")
SSL_MAIN_SERVER_ID = int(os.getenv("SSL_MAIN_SERVER_ID"))
SSL_HELP_CHANNEL_ID = int(os.getenv("SSL_MAIN_SERVER_SSL_HELP_CHANNEL"))
SSL_NEW_PLAYER_GUIDE_CHANNEL_ID = int(os.getenv("SSL_MAIN_SERVER_NEW_PLAYER_GUIDE_CHANNEL"))
SSL_BOD_ROLE_ID = int(os.getenv("SSL_MAIN_SERVER_BOD_ROLE_ID"))
SSL_ACADEMY_COACHES_ROLE_ID = int(os.getenv("SSL_MAIN_SERVER_ACADEMY_COACHES_ROLE_ID"))
TEST_ID = int(os.getenv('DISCORD_TEST_ID'))

class IntroMessage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(name='test_join', description='Simulates a member joining')
    @discord.app_commands.guilds(discord.Object(id=TEST_ID))
    async def test_join(self, interaction: discord.Interaction):
        print("testing")
        await interaction.response.defer()
        await self.on_member_join(interaction.user)
        await interaction.followup.send("Simulated join event triggered.")
    
    @commands.Cog.listener()
    async def on_ready(self):
        print("IntroMessage Cog is online!")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
      
        print(f"Simulating welcome for {member.name}")

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
                f"The SSL is a simulation league within the world of soccer/football. The league takes the Be-a-pro game mode to a multiplayer environment where users from across the globe create their own player, join one of the teams, fight for the league or cup championships and watch commentated games simulated through Football Manager.\n\n"
                f"Read more about how you can start your career in the <#{new_player_guide_channel_id}>.\n\n"
                f"If you need any help you can contact any of the <@&{bod_role_id}> or <@&{academy_coaches_role_id}>, and of course you can always ask question in <#{ssl_help_channel_id}>"
            )
        else:
            welcome_message = f"Hello there {member.name}, welcome to {member.guild.name}!"    

        images = os.listdir("./graphics/welcome_images")
        random_image = random.choice(images)
        
        bg = easy_pil.Editor(f"./graphics/welcome_images/{random_image}").resize((1920, 1080))
        
        print("Base background created")
        
        avatar_image = await easy_pil.load_image_async(str(member.avatar.url))
        avatar = easy_pil.Editor(avatar_image).resize((250, 250)).circle_image()

        # Fix the font module reference (easy_pil.Font, not easy.pil.Font)
        font_big = easy_pil.Font.poppins(size=80, variant="bold")
        font_small = easy_pil.Font.poppins(size=40, variant="bold")

        bg.paste(avatar, (835, 340))
        bg.ellipse((835, 340), 250, 250, outline="#ED9523", stroke_width=5)
        # bg.rectangle([(650, 570), (1270, 700)], fill="#ffffff")
        print(bg)
        print(welcome_channel)

        # Fix parentheses and parameters for bg.text method calls
        bg.text((960, 620), f"Welcome to {member.guild.name}", font=font_big, color="#070B51", align="center")
        bg.text((960, 740), f"{member.name} is member #{member.guild.member_count} here!", font=font_small, color="#070B51", align="center")

        image_file = discord.File(fp=bg.image_bytes, filename="welcome.png")  # Use a fixed filename for easy caching

        await welcome_channel.send(welcome_message, file=image_file)

async def setup(bot):
    await bot.add_cog(IntroMessage(bot))
