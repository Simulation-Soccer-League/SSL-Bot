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
from dotenv import load_dotenv
import os # default module

TEST_ID = int(os.getenv('DISCORD_TEST_ID'))

def generate_stat_sheet_image(data, leader):
    #Prepare Data
    stat = data[["tpe", "name", "username"]].sort_values("tpe", ascending=False).head()
    stat.columns = stat.columns.str.upper()
    leaders = stat.to_dict('records')
    
    #Draw Image
    WIDTH = 600
    HEADER_BG = "#070B51"
    ROW_BG = "#070B51"
    TEXT_COLOR = "#FFFFFF"
    FONT_PATH = DEFAULT_FONT_PATH
    try:
        TITLE_FONT = ImageFont.truetype(FONT_PATH, 32)
        ROW_FONT = ImageFont.truetype(FONT_PATH, 24)
    except IOError:
        TITLE_FONT = ImageFont.load_default()
        ROW_FONT = ImageFont.load_default()
    
    draw_dummy = ImageDraw.Draw(Image.new("RGB", (WIDTH, 60)))  # Used for measuring only

    headers = ["TPE", "PLAYER", "USER"]
    # Find out the max width needed per column
    col_content = {h: [h] + [str(l[h]) for l in leaders] for h in headers}
    max_widths = []
    for h in headers:
        max_w = max([draw_dummy.textbbox((0,0), v, font=ROW_FONT)[2] for v in col_content[h]])
        max_widths.append(max_w)
    
    # Calculate dynamic column X positions with a little padding
    col_positions = [30]
    for i in range(1, len(headers)):
        next_pos = col_positions[-1] + max_widths[i-1] + 40  # 40 px padding
        col_positions.append(next_pos)
    
    HEIGHT = 60 + len(leaders)*50 + 40
    img = Image.new('RGB', (WIDTH, HEIGHT), color=ROW_BG)
    draw = ImageDraw.Draw(img)
    
    # Draw header
    draw.rectangle([0, 0, WIDTH, 60], fill=HEADER_BG)
    draw.text((WIDTH//2, 20), leader + " Class Leaders", font=TITLE_FONT, fill="#ED9523", anchor="mm")
    
    # Draw column labels
    y_start = 70
    for idx, h in enumerate(headers):
        draw.text((col_positions[idx], y_start), h, font=ROW_FONT, fill=TEXT_COLOR)
    draw.line([(30, 100), (WIDTH-30, 100)], fill=HEADER_BG, width=3)
    
    # Draw rows
    y = 110
    for item in leaders:
        values = [str(item[h]) for h in headers]
        for idx, val in enumerate(values):
            draw.text((col_positions[idx], y), val, font=ROW_FONT, fill=TEXT_COLOR)
        y += 50

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
    @discord.app_commands.guilds(discord.Object(id=TEST_ID))
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
