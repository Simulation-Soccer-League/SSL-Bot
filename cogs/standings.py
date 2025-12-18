import discord
from discord.ext import commands
from discord import app_commands
import requests
import asyncio
import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import logging
from dotenv import load_dotenv
import os
from typing import Optional
import pytz

load_dotenv(".secrets/.env")
TEST_ID = int(os.getenv("DISCORD_TEST_ID"))

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

    @app_commands.command(
        name="leaguestandings",
        description="Get the standings for the specified league",
    )
    @app_commands.guilds(discord.Object(id=TEST_ID))
    @app_commands.describe(
        league="The League name (Majors, Minors)",
        season="The season number (e.g., 23)",
        division="Division number (1 or 2). Leave empty for both (S24+).",
    )
    async def leaguestandings(
        self,
        interaction: discord.Interaction,
        league: str,
        season: str = CURRENT_SEASON,
        division: Optional[int] = None,
    ):
        league_name_lower = league.lower()
        league_id = LEAGUEIDMAPPING.get(league_name_lower)
        if league_id is None or league_id == 0:
            await interaction.response.send_message(
                "Standings are only available for Majors and Minors leagues.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()
        season_int = int(season)

        # Case 1: old seasons or explicit division -> single table
        if season_int < 24 or division is not None:
            div_value = division if season_int >= 24 else None
            standings_data, error_msg = await asyncio.to_thread(
                self.getstandingsdataseason,
                season,
                league_id,
                div_value,
            )
            if error_msg:
                await interaction.followup.send(
                    f"Error fetching standings: {error_msg}", ephemeral=True
                )
                return

            if not standings_data:
                div_text = f" Division {division}" if div_value else ""
                await interaction.followup.send(
                    f"No standings data found for {league.title()}{div_text} Season {season}.",
                    ephemeral=True,
                )
                return

            league_title = (
                f"{league.title()} Division {division}" if div_value else league.title()
            )
            image_bytes = await asyncio.to_thread(
                self.create_standings_image,
                standings_data,
                league_title,
                season,
            )

        else:
            # Case 2: S24+ and no division -> fetch both division 1 and 2
            standings_div1, err1 = await asyncio.to_thread(
                self.getstandingsdataseason,
                season,
                league_id,
                1,
            )
            standings_div2, err2 = await asyncio.to_thread(
                self.getstandingsdataseason,
                season,
                league_id,
                2,
            )
            if err1 or err2:
                await interaction.followup.send(
                    f"Error fetching standings: {err1 or err2}", ephemeral=True
                )
                return
            if not standings_div1 and not standings_div2:
                await interaction.followup.send(
                    f"No standings data found for {league.title()} Season {season}.",
                    ephemeral=True,
                )
                return

            image_bytes = await asyncio.to_thread(
                self.create_two_divisions_image,
                standings_div1,
                standings_div2,
                league.title(),
                season,
            )

        if not image_bytes:
            await interaction.followup.send(
                "Failed to generate standings image.", ephemeral=True
            )
            return

        file = discord.File(fp=image_bytes, filename="standings.png")
        eastern = pytz.timezone("US/Eastern")
        now_et = datetime.datetime.now(eastern)


        embed = discord.Embed(
            title=f"{league.title()} Standings - Season {season}",
            color=discord.Color.purple(),
            timestamp=now_et,
        )
        embed.set_image(url="attachment://standings.png")
        await interaction.followup.send(embed=embed, file=file)

    # ---------- DATA FETCHING ----------

    def getstandingsdataseason(
        self, season: str, league: int, division: Optional[int] = None
    ):
        if division is not None and int(season) >= 24:
            url = f"{STANDINGSAPIBASEURL}?season={season}&league={league}&division={division}"
        else:
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

    # ---------- IMAGE GENERATION: SINGLE TABLE ----------

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
                title_font = ImageFont.truetype(DEFAULT_FONT_PATH, 52)
                header_font = ImageFont.truetype(DEFAULT_FONT_PATH, 28)
                row_font = ImageFont.truetype(DEFAULT_FONT_PATH, 22)
            except Exception:
                title_font = ImageFont.load_default()
                header_font = ImageFont.load_default()
                row_font = ImageFont.load_default()

            logo_size = 48
            row_height = 64
            padding = 18

            columns = [
                ("#", 40, "center", None),
                ("Team", 330, "left", "Team"),
                ("P", 50, "center", "MatchesPlayed"),
                ("W", 50, "center", "Wins"),
                ("D", 50, "center", "Draws"),
                ("L", 50, "center", "Losses"),
                ("GF", 50, "center", "GoalsFor"),
                ("GA", 50, "center", "GoalsAgainst"),
                ("GD", 52, "center", "GoalDifference"),
                ("Pts", 54, "center", "Points"),
            ]

            col_widths = {col[0]: col[1] for col in columns}
            total_width = sum(w for _, w, _, _ in columns) + padding * 2
            num_rows = len(standings_data)
            total_height = 190 + (row_height * (num_rows + 1)) + padding * 2

            image = Image.new(
                "RGBA", (total_width + 260, total_height + 40), bg_dark
            )
            draw = ImageDraw.Draw(image)

            # Gradient background
            for y in range(image.height):
                ratio = y / image.height
                r = int(accent_color[0] * (1 - ratio) + gradient_end[0] * ratio)
                g = int(accent_color[1] * (1 - ratio) + gradient_end[1] * ratio)
                b = int(accent_color[2] * (1 - ratio) + gradient_end[2] * ratio)
                draw.line([(0, y), (image.width, y)], fill=(r, g, b, 255))

            # League badge
            try:
                badge = Image.open(DEFAULT_LOGO_PATH).convert("RGBA")
                badge = badge.resize((88, 88), Image.Resampling.LANCZOS)
                image.paste(badge, (30, 30), badge)
            except Exception:
                pass

            # Title
            title_text = f"{league_name} League Table"
            bbox = draw.textbbox((0, 0), title_text, font=title_font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            table_center_x = padding + total_width // 2
            draw.text(
                (table_center_x - tw // 2, 38),
                title_text,
                font=title_font,
                fill="#ffffff",
            )

            # Trophy + vertical label
            trophy_panel_x = total_width + 40
            trophy_panel_y = total_height - 360
            trophy_panel_w, trophy_panel_h = 200, 340

            try:
                trophy = Image.open(trophy_path).convert("RGBA")

                tr_w, tr_h = trophy.size
                scale = min(trophy_panel_w / tr_w, trophy_panel_h / tr_h)
                new_w, new_h = int(tr_w * scale), int(tr_h * scale)
                trophy = trophy.resize((new_w, new_h), Image.Resampling.LANCZOS)

                center_x = trophy_panel_x + (trophy_panel_w - new_w) // 2
                center_y = trophy_panel_y + (trophy_panel_h - new_h) // 2

                # Shadow from trophy shape
                shadow = Image.new("RGBA", trophy.size, (0, 0, 0, 0))
                shadow_mask = trophy.split()[3]
                shadow.paste((0, 0, 0, 180), mask=shadow_mask)
                shadow = shadow.filter(ImageFilter.GaussianBlur(radius=6))
                sx = center_x + 8
                sy = center_y + 8
                image.paste(shadow, (sx, sy), shadow)

                image.paste(trophy, (center_x, center_y), trophy)

                # Vertical MAJORS/MINORS label, dynamic based on rotated size
                side_label = "MAJORS" if is_major else "MINORS"

                label_top_limit = 20
                label_bottom_limit = center_y - 10
                available_height = max(60, label_bottom_limit - label_top_limit)

                min_size = 16
                max_size = 110
                chosen_font = ImageFont.load_default()
                chosen_label_img = None

                for size in range(min_size, max_size + 1):
                    test_font = ImageFont.truetype(
                        DEFAULT_FONT_PATH, size
                    ) if DEFAULT_FONT_PATH else ImageFont.load_default()

                    tmp_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
                    tbbox = tmp_draw.textbbox((0, 0), side_label, font=test_font)
                    lw, lh = tbbox[2] - tbbox[0], tbbox[3] - tbbox[1]

                    temp_label = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
                    temp_draw = ImageDraw.Draw(temp_label)
                    darker_accent = tuple(max(0, int(c * 0.6)) for c in accent_color)
                    temp_draw.text(
                        (0, 0),
                        side_label,
                        font=test_font,
                        fill=(*darker_accent, int(255 * 0.4)),
                    )

                    rotated = temp_label.rotate(-90, expand=True)
                    rotated_h = rotated.height

                    if rotated_h <= available_height:
                        chosen_font = test_font
                        chosen_label_img = rotated
                    else:
                        break

                if chosen_label_img is None:
                    fallback_font = ImageFont.truetype(
                        DEFAULT_FONT_PATH, 20
                    ) if DEFAULT_FONT_PATH else ImageFont.load_default()
                    tmp_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
                    tbbox = tmp_draw.textbbox((0, 0), side_label, font=fallback_font)
                    lw, lh = tbbox[2] - tbbox[0], tbbox[3] - tbbox[1]
                    temp_label = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
                    temp_draw = ImageDraw.Draw(temp_label)
                    darker_accent = tuple(max(0, int(c * 0.6)) for c in accent_color)
                    temp_draw.text(
                        (0, 0),
                        side_label,
                        font=fallback_font,
                        fill=(*darker_accent, int(255 * 0.4)),
                    )
                    chosen_label_img = temp_label.rotate(-90, expand=True)

                label_img = chosen_label_img
                lx = trophy_panel_x + (trophy_panel_w - label_img.width) // 2
                ly = label_bottom_limit - label_img.height
                if ly < 10:
                    ly = 10
                image.paste(label_img, (lx, ly), label_img)

            except Exception as e:
                logger.error(f"Error loading trophy or drawing side label: {e}")

            # Header row
            header_y = 145
            draw.rectangle(
                [padding, header_y, total_width + padding, header_y + row_height],
                fill=header_bg,
                outline=None,
            )
            x = padding
            for header, _, align, _ in columns:
                text = header
                hbbox = draw.textbbox((0, 0), text, font=header_font)
                w, h = hbbox[2] - hbbox[0], hbbox[3] - hbbox[1]
                if align == "center":
                    tx = x + (col_widths[header] - w) // 2
                elif align == "right":
                    tx = x + col_widths[header] - w - 12
                else:
                    tx = x + 12
                draw.text(
                    (tx, header_y + (row_height - h) // 2),
                    text,
                    font=header_font,
                    fill="white",
                )
                x += col_widths[header]

            # Team rows
            current_y = header_y + row_height
            for idx, team_stats in enumerate(standings_data):
                x = padding
                row_bg = top_row if idx == 0 else (
                    row_even if idx % 2 == 0 else row_odd
                )
                draw.rectangle(
                    [padding, current_y, total_width + padding, current_y + row_height],
                    fill=row_bg,
                    outline=None,
                )

                # Rank
                pos_text = str(idx + 1)
                pbbox = draw.textbbox((0, 0), pos_text, font=row_font)
                w, h = pbbox[2] - pbbox[0], pbbox[3] - pbbox[1]
                draw.text(
                    (x + (col_widths["#"] - w) // 2, current_y + (row_height - h) // 2),
                    pos_text,
                    font=row_font,
                    fill="white",
                )
                x += col_widths["#"]

                # Logo + Name
                team_name = team_stats.get("Team", NA_PLACEHOLDER)
                try:
                    logo_path = get_team_logo_path(team_name)
                    logo = (
                        Image.open(logo_path)
                        .convert("RGBA")
                        .resize((logo_size, logo_size), Image.Resampling.LANCZOS)
                    )
                    logo_y = current_y + (row_height - logo_size) // 2
                    image.paste(logo, (x + 12, logo_y), logo)
                except Exception:
                    pass

                tn_x = x + logo_size + 24
                nbbox = draw.textbbox((0, 0), team_name, font=row_font)
                w, h = nbbox[2] - nbbox[0], nbbox[3] - nbbox[1]
                draw.text(
                    (tn_x, current_y + (row_height - h) // 2),
                    team_name,
                    font=row_font,
                    fill="white",
                )
                x += col_widths["Team"]

                # Stats
                data_keys = [
                    "MatchesPlayed",
                    "Wins",
                    "Draws",
                    "Losses",
                    "GoalsFor",
                    "GoalsAgainst",
                    "GoalDifference",
                    "Points",
                ]
                for idx_col, header in enumerate([col[0] for col in columns[2:]]):
                    value = str(team_stats.get(data_keys[idx_col], 0))
                    vbbox = draw.textbbox((0, 0), value, font=row_font)
                    w, h = vbbox[2] - vbbox[0], vbbox[3] - vbbox[1]
                    col = columns[2 + idx_col]
                    align = col[2]
                    if align == "center":
                        tx = x + (col_widths[header] - w) // 2
                    elif align == "right":
                        tx = x + col_widths[header] - w - 10
                    else:
                        tx = x + 10
                    draw.text(
                        (tx, current_y + (row_height - h) // 2),
                        value,
                        font=row_font,
                        fill="white",
                    )
                    x += col_widths[header]
                current_y += row_height

            draw.line(
                [(padding, header_y + row_height), (total_width + padding, header_y + row_height)],
                fill=accent_color,
                width=3,
            )

            buf = io.BytesIO()
            image.save(buf, format="PNG")
            buf.seek(0)
            return buf
        except Exception as e:
            logger.error(
                f"Error creating standings image for {league_name} Season {season}: {e}"
            )
            return None

    # ---------- IMAGE GENERATION: TWO DIVISIONS ----------

    def create_two_divisions_image(
        self,
        standings_div1,
        standings_div2,
        league_name,
        season,
    ):
        img1_bytes = self.create_standings_image(
            standings_div1, f"{league_name} Division 1", season
        )
        img2_bytes = self.create_standings_image(
            standings_div2, f"{league_name} Division 2", season
        )
        if not img1_bytes or not img2_bytes:
            return None

        img1 = Image.open(img1_bytes).convert("RGBA")
        img2 = Image.open(img2_bytes).convert("RGBA")

        width = max(img1.width, img2.width)
        height = img1.height + img2.height

        combined = Image.new("RGBA", (width, height), (0, 0, 0, 255))
        combined.paste(img1, (0, 0), img1)
        combined.paste(img2, (0, img1.height), img2)

        out = io.BytesIO()
        combined.save(out, format="PNG")
        out.seek(0)
        return out


async def setup(bot):
    await bot.add_cog(Standings(bot))
