import discord
from discord.ext import commands
from discord import app_commands
import pandas as pd
import typing
import requests
import json
import io
from PIL import Image, ImageDraw, ImageFont
from utils import DEFAULT_FONT_PATH

def generate_stat_sheet_image(data, leader):
    # Prepare data
        stat = data[["tpe", "name", "username"]].sort_values("tpe", ascending=False).head()
        stat.columns = stat.columns.str.upper()
        leaders = stat.to_dict('records')

    # Image setup
        WIDTH = 600
        HEIGHT = 60 + len(leaders)*50 + 40
        HEADER_BG = "#070B51"
        ROW_BG = "#070B51"
        TEXT_COLOR = "#FFFFFF"
        FONT_PATH = DEFAULT_FONT_PATH # Change to your font path if needed
        try:
            TITLE_FONT = ImageFont.truetype(DEFAULT_FONT_PATH, 32)
            ROW_FONT = ImageFont.truetype(DEFAULT_FONT_PATH, 24)
        except IOError:
            TITLE_FONT = ImageFont.load_default()
            ROW_FONT = ImageFont.load_default()

        img = Image.new('RGB', (WIDTH, HEIGHT), color=ROW_BG)
        draw = ImageDraw.Draw(img)

    # Draw header
        draw.rectangle([0, 0, WIDTH, 60], fill=HEADER_BG)
        draw.text((WIDTH//2, 20), leader + " Class Leaders", font=TITLE_FONT, fill="#ED9523", anchor="mm")

    # Draw column labels
        draw.text((40, 70), "TPE", font=ROW_FONT, fill=TEXT_COLOR)
        draw.text((140, 70), "PLAYER", font=ROW_FONT, fill=TEXT_COLOR)
        draw.text((360, 70), "USER", font=ROW_FONT, fill=TEXT_COLOR)
        draw.line([(30, 100), (WIDTH-30, 100)], fill=HEADER_BG, width=3)

    # Draw rows
        y = 110
        for leader in leaders:
            draw.text((40, y), str(leader['TPE']), font=ROW_FONT, fill=TEXT_COLOR)
            draw.text((140, y), leader['NAME'], font=ROW_FONT, fill=TEXT_COLOR)
            draw.text((360, y), leader['USERNAME'], font=ROW_FONT, fill=TEXT_COLOR)
            y += 50

    # Save to buffer
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf


class Leaders(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{__name__} is online!")

   
    @app_commands.command(name='classleaders', description='Shows the draft class leaders for a specific class (number)')
    async def classleaders(self, interaction: discord.Interaction, season: typing.Optional[int] = None):
        if season is None:
            info = requests.get('https://api.simulationsoccer.com/player/getDraftClass')
            leader = "Academy"
        else: 
            info = requests.get('https://api.simulationsoccer.com/player/getDraftClass?class=' + str(season))
            leader = 'S' + str(season)
         # Data formatting
        data = pd.DataFrame(json.loads(info.content))
        embed = discord.Embed(color = discord.Color(0xBD9523))
        embed.title = leader + ' Class Leaders'
         # TPE Leaders
        stat = data[["tpe", "name", "username"]].sort_values("tpe", ascending = False).head()
        stat.columns = stat.columns.str.upper()
         # Convert the DataFrame to a formatted string
        stat_string = stat.to_string(index=False)
         # Format the string to fit nicely in the embed
        formatted_stat_string = f"```\n{stat_string}\n```"
        embed.add_field(name = "", value = formatted_stat_string, inline = True)
        await interaction.response.send_message(embed = embed)

    
    @app_commands.command(name='test_classleaders', description='Shows the draft class leaders for a specific class (number)')
    async def classleaders(self, interaction: discord.Interaction, season: typing.Optional[int] = None):
        if season is None:
            info = requests.get('https://api.simulationsoccer.com/player/getDraftClass')
            leader = "Academy"
        else:
            info = requests.get('https://api.simulationsoccer.com/player/getDraftClass?class=' + str(season))
            leader = 'S' + str(season)
        data = pd.DataFrame(json.loads(info.content))
        embed = discord.Embed(color=discord.Color(0xBD9523))
        embed.title = leader + ' Class Leaders'

        # Generate image
        buf = generate_stat_sheet_image(data, leader)
        file = discord.File(buf, filename="classleaders.png")
        embed.set_image(url="attachment://classleaders.png")

        await interaction.response.send_message(file=file, embed=embed)
        
async def setup(bot):
    await bot.add_cog(Leaders(bot))
