import discord
from discord.ext import commands
from discord import app_commands
import requests
import asyncio
import datetime
from PIL import Image, ImageDraw, ImageFont
import io
import logging

from utils import (
    STANDINGSAPIBASEURL,
    DEFAULT_FONT_PATH,
    NA_PLACEHOLDER,
    LEAGUEIDMAPPING,
    get_team_logo_path,
    CURRENT_SEASON,
    DEFAULT_LOGO_PATH,       
    MAJOR_TROPHY_PATH,    
    MINOR_TROPHY_PATH,
)

logger = logging.getLogger(__name__)

class Standings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{__name__} is online!")

    @app_commands.command(name="leaguestandings", description="Get the standings for the specified league")
    @app_commands.describe(league="The League name (Majors, Minors)", season="The season number (e.g., 23)")
    async def leaguestandings(self, interaction: discord.Interaction, league: str, season: str = CURRENT_SEASON):
        league_name_lower = league.lower()
        league_id = LEAGUEIDMAPPING.get(league_name_lower)
        if league_id is None or league_id == 0:
            await interaction.response.send_message(
                "Standings are only available for Majors and Minors leagues.", ephemeral=True
            )
            return

        await interaction.response.defer()

        standings_data, error_msg = await asyncio.to_thread(self.getstandingsdataseason, season, league_id)
        if error_msg:
            await interaction.followup.send(f"Error fetching standings: {error_msg}", ephemeral=True)
            return

        if not standings_data:
            await interaction.followup.send(f"No standings data found for {league.title()} Season {season}.", ephemeral=True)
            return

        image_bytes = await asyncio.to_thread(self.create_standings_image, standings_data, league.title(), season)
        if not image_bytes:
            await interaction.followup.send("Failed to generate standings image.", ephemeral=True)
            return

        file = discord.File(fp=image_bytes, filename="standings.png")
        embed = discord.Embed(
            title=f"{league.title()} Standings - Season {season}",
            color=discord.Color.purple(),
            timestamp=datetime.datetime.utcnow(),
        )
        embed.set_image(url="attachment://standings.png")
        await interaction.followup.send(embed=embed, file=file)

    def getstandingsdataseason(self, season, league):
        url = f"{STANDINGSAPIBASEURL}?season={season}&league={league}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json(), None
        except requests.exceptions.HTTPError as e:
            return None, f"HTTP error {e.response.status_code}: {e.response.reason}"
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            return None, "Network issue: Unable to reach the standings API at this time."
        except requests.exceptions.RequestException as e:
            return None, f"Unexpected error occurred: {e}"
        except ValueError as e:
            return None, f"Error parsing standings data: {e}"

    def create_standings_image(self, standings_data, league_name, season):
        try:
            # Theme and assets
            is_major = league_name.lower().startswith("major")
            accent_color = (218, 185, 45) if is_major else (176, 40, 49)
            bg_dark = (30, 30, 30)
            gradient_end = (46, 46, 46)
            header_bg = (48, 48, 48)
            row_even = (38, 38, 38)
            row_odd = (26, 26, 26, 255)
            top_row = accent_color + (100,)

            trophy_path = MAJOR_TROPHY_PATH if is_major else MINOR_TROPHY_PATH

            # Fonts
            try:
                title_font = ImageFont.truetype(DEFAULT_FONT_PATH, 56)
                header_font = ImageFont.truetype(DEFAULT_FONT_PATH, 32)
                row_font = ImageFont.truetype(DEFAULT_FONT_PATH, 26)
            except Exception:
                title_font = ImageFont.load_default()
                header_font = ImageFont.load_default()
                row_font = ImageFont.load_default()

            logo_size = 48
            row_height = 64
            padding = 18

            columns = [
                ("#", 40, "center", None),
                ("Team", 210, "left", "Team"),
                ("P", 44, "center", "MatchesPlayed"),
                ("W", 44, "center", "Wins"),
                ("D", 44, "center", "Draws"),
                ("L", 44, "center", "Losses"),
                ("GF", 44, "center", "GoalsFor"),
                ("GA", 44, "center", "GoalsAgainst"),
                ("GD", 52, "center", "GoalDifference"),
                ("Pts", 54, "center", "Points"),
            ]
            # Width calculations
            col_widths = {col[0]: col[1] for col in columns}
            total_width = sum([w for _, w, _, _ in columns]) + padding * 2
            num_rows = len(standings_data)
            total_height = 190 + (row_height * (num_rows + 1)) + padding * 2

            # Base image and gradient
            image = Image.new("RGBA", (total_width + 260, total_height + 20), bg_dark)
            draw = ImageDraw.Draw(image)
            # Gradient overlay
            for y in range(image.height):
                ratio = y / image.height
                r = int(accent_color[0] * (1-ratio) + gradient_end[0] * ratio)
                g = int(accent_color[1] * (1-ratio) + gradient_end[1] * ratio)
                b = int(accent_color[2] * (1-ratio) + gradient_end[2] * ratio)
                draw.line([(0, y), (image.width, y)], fill=(r, g, b, 255))

            # Title
            title_text = f"{league_name} League Table"
            tw, th = draw.textsize(title_text, font=title_font)
            draw.text(((total_width // 2 - tw // 2) + padding, 38), title_text, font=title_font, fill=accent_color)

            # League badge
            try:
                badge = Image.open(DEAFULT_LOGO_PATH).convert("RGBA")
                badge = badge.resize((88, 88), Image.Resampling.LANCZOS)
                image.paste(badge, (30, 30), badge)
            except Exception:
                pass

            # Trophy graphic
            try:
                trophy = Image.open(trophy_path).convert("RGBA")
                trophy = trophy.resize((180, 350), Image.Resampling.LANCZOS)
                image.paste(trophy, (total_width + 50, total_height - 380), trophy)
            except Exception:
                pass

            # Header row
            header_y = 145
            draw.rectangle(
                [padding, header_y, total_width + padding, header_y+row_height],
                fill=header_bg,
                outline=None
            )
            x = padding
            for header, _, align, _ in columns:
                text = header
                w, h = draw.textsize(text, font=header_font)
                if align == "center":
                    tx = x + (col_widths[header] - w) // 2
                elif align == "right":
                    tx = x + col_widths[header] - w - 12
                else:
                    tx = x + 12
                draw.text((tx, header_y + (row_height - h) // 2), text, font=header_font, fill="white")
                x += col_widths[header]

            # Team rows
            current_y = header_y + row_height
            for idx, team_stats in enumerate(standings_data):
                x = padding
                row_bg = top_row if idx == 0 else (row_even if idx % 2 == 0 else row_odd)
                draw.rectangle(
                    [padding, current_y, total_width + padding, current_y + row_height],
                    fill=row_bg,
                    outline=None
                )
                # Rank
                pos_text = str(idx + 1)
                w, h = draw.textsize(pos_text, font=row_font)
                draw.text((x + (col_widths["#"] - w) // 2, current_y + (row_height - h) // 2), pos_text, font=row_font, fill="white")
                x += col_widths["#"]

                # Logo + Name
                team_name = team_stats.get("Team", NA_PLACEHOLDER)
                try:
                    logo_path = get_team_logo_path(team_name)
                    logo = Image.open(logo_path).convert("RGBA").resize((logo_size, logo_size), Image.Resampling.LANCZOS)
                    logo_y = current_y + (row_height - logo_size) // 2
                    image.paste(logo, (x + 12, logo_y), logo)
                except Exception:
                    pass
                tn_x = x + logo_size + 24
                draw.text((tn_x, current_y + (row_height - h) // 2), team_name, font=row_font, fill="white")
                x += col_widths["Team"]

                # Stats
                data_keys = ["MatchesPlayed", "Wins", "Draws", "Losses", "GoalsFor", "GoalsAgainst", "GoalDifference", "Points"]
                for idx_col, header in enumerate([col[0] for col in columns[2:]]):
                    value = str(team_stats.get(data_keys[idx_col], 0))
                    w, h = draw.textsize(value, font=row_font)
                    col = columns[2 + idx_col]
                    align = col[2]
                    if align == "center":
                        tx = x + (col_widths[header] - w) // 2
                    elif align == "right":
                        tx = x + col_widths[header] - w - 10
                    else:
                        tx = x + 10
                    draw.text((tx, current_y + (row_height - h) // 2), value, font=row_font, fill="white")
                    x += col_widths[header]
                current_y += row_height

            # Line under header
            draw.line([(padding, header_y+row_height), (total_width + padding, header_y+row_height)], fill=accent_color, width=3)
            # Final render
            byte_arr = io.BytesIO()
            image.save(byte_arr, format="PNG")
            byte_arr.seek(0)
            return byte_arr
        except Exception as e:
            logger.error(f"Error creating standings image for {league_name} Season {season}: {e}")
            return None

async def setup(bot):
    await bot.add_cog(Standings(bot))
