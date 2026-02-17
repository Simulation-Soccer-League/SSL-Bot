import discord
from discord.ext import commands
from discord import app_commands
import pandas as pd
import requests
import datetime
import json
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
from dotenv import load_dotenv
import os

load_dotenv(".secrets/.env")
# TEST_ID = int(os.getenv("DISCORD_TEST_ID"))

from utils import (
    MAJORS_DIV2_LOGO_PATH,
    STANDINGSAPIBASEURL,
    DEFAULT_FONT_PATH,
    NA_PLACEHOLDER,
    LEAGUEIDMAPPING,
    get_team_logo_path,
    CURRENT_SEASON,
    DEFAULT_LOGO_PATH,
    MAJOR_LEAGUE_LOGO_PATH,
    MINOR_LEAGUE_LOGO_PATH,
    MAJORS_DIV1_LOGO_PATH,
    MINORS_DIV1_LOGO_PATH,
    MAJORS_DIV2_LOGO_PATH,
    MINORS_DIV2_LOGO_PATH,
    DEMO_STANDINGS_DATA,
)

class Standings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        #Returns the correct logo path based on league + division

    def get_league_logo_path(self, league_name: str):
        lname = league_name.lower()

        is_major = lname.startswith("major")
        is_div1 = "division 1" in lname
        is_div2 = "division 2" in lname

        if is_major:
            if is_div1:
                return MAJORS_DIV1_LOGO_PATH
            if is_div2:
                return MAJORS_DIV2_LOGO_PATH
            return MAJOR_LEAGUE_LOGO_PATH
        else:
            if is_div1:
                return MINORS_DIV1_LOGO_PATH
            if is_div2:
                return MINORS_DIV2_LOGO_PATH
            return MINOR_LEAGUE_LOGO_PATH
    

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{__name__} is online!")

    # ---------------- COMMAND ----------------
    @app_commands.command(
        name="leaguestandings",
        description="Get the standings for the specified league",
    )
    # @app_commands.guilds(discord.Object(id=TEST_ID))
    @app_commands.describe(
        league="Major or Minor",
        season="Season number (e.g. 24)",
        division="Division to show: 1, 2, or All (S24+ only)",
    )
    async def leaguestandings(
        self,
        interaction: discord.Interaction,
        league: str,
        season: int = int(CURRENT_SEASON),
        division: str = "All",
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

        has_divisions = season >= 24
        division = division.lower()

        # -------- Enforce S24+ rule --------
        if season < 24 and division != "all":
            await interaction.followup.send(
                "Divisions were introduced in Season 24.\n"
                "Showing the full table instead.",
                ephemeral=True,
            )
            division = "all"

        # -------- Fetch data once --------
        response = requests.get(  
            f"{STANDINGSAPIBASEURL}?season={season}&league={league_id}"
        )
        standings_data = pd.DataFrame(json.loads(response.content))  

        standings_data = standings_data.sort_values(  
            by=["p", "gd", "gf"],
            ascending=[False, False, False]
        ).reset_index(drop=True)

        if standings_data.empty:
            await interaction.followup.send(
                f"No standings data found for {league.title()} Season {season}.",
                ephemeral=True,
            )
            return

        # -------- Split by division --------
        div1 = standings_data[standings_data['matchday'] == "1"].reset_index(drop=True)
        div2 = standings_data[standings_data['matchday'] == "2"].reset_index(drop=True)
        no_div = standings_data[standings_data['matchday'] == "ALL"].reset_index(drop=True)

        # -------- Routing logic --------
        if not has_divisions:
            data = standings_data
            title = league.title()
        elif division == "all":
            data = None
        elif division == "1":
            data = div1
            title = f"{league.title()} Division 1"
        elif division == "2":
            data = div2
            title = f"{league.title()} Division 2"
        else:
            await interaction.followup.send(
                "Invalid division option. Use 1, 2, or All.",
                ephemeral=True,
            )
            return

        # -------- Side label rule --------
        show_side_label = not (season >= 24 and division in ["1", "2"])  

        if division == "all" and has_divisions:
            image_bytes = self.create_two_divisions_image(
                div1,
                div2,
                league.title(),
                season
            )
        else:
            image_bytes = self.create_standings_image(
                data,
                title,
                season,
                False,
                True,
                False,
                show_side_label,  
            )

        if not image_bytes:
            await interaction.followup.send(
                "Failed to generate standings image.",
                ephemeral=True,
            )
            return

        file = discord.File(fp=image_bytes, filename="standings.png")

        if division == "1":
            embed_title = f"{league.title()} Division 1 Standings - Season {season}"
        elif division == "2":
            embed_title = f"{league.title()} Division 2 Standings - Season {season}"
        else:
            embed_title = f"{league.title()} Standings - Season {season}"

        embed = discord.Embed(
            title=embed_title,
            color=discord.Color.purple(),
        )
        embed.set_image(url="attachment://standings.png")

        await interaction.followup.send(embed=embed, file=file)

    # ---------- IMAGE GENERATION: SINGLE TABLE ----------
    def create_standings_image(
        self,
        standings_data,
        league_name,
        season,
        show_header=False,
        show_trophy=True,
        table_only=False,
        show_side_label=True,
    ):
        try:
            # Theme and assets
            is_major = league_name.lower().startswith("major")
            accent_color = (218, 185, 45) if is_major else (176, 40, 49)
            bg_dark = (30, 30, 30)
            gradient_end = (46, 46, 46)
            header_bg = (48, 48, 48)
            row_even = (38, 38, 38)
            row_odd = (26, 26, 26, 255)
            top_row = (
                int(accent_color[0] * 0.85),
                int(accent_color[1] * 0.85),
                int(accent_color[2] * 0.85),
                120,
            )
            # Promotion / relegation colors (S24+ only)
            promotion_green = (39, 174, 96, 120)   # Clean green
            playoff_blue = (41, 128, 185, 120)      # Clear blue
            relegation_red = (169, 50, 38, 120)     # Distinct from Minors red
            
            league_logo_path = self.get_league_logo_path(league_name)
            
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
            padding = 12

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
            num_rows = len(standings_data.index)
            # Division detection
            is_division_1 = "division 1" in league_name.lower()
            is_division_2 = "division 2" in league_name.lower()
            total_height = 100 + (row_height * (num_rows + 1)) + padding * 2

            canvas_width = total_width if table_only else total_width + 260
            image = Image.new(
                "RGBA", (canvas_width, total_height + 40), bg_dark
            )
            draw = ImageDraw.Draw(image)
            
            # Gradient background
            if not table_only:
                for y in range(image.height):
                    ratio = y / image.height
                    r = int(accent_color[0] * (1 - ratio) + gradient_end[0] * ratio)
                    g = int(accent_color[1] * (1 - ratio) + gradient_end[1] * ratio)
                    b = int(accent_color[2] * (1 - ratio) + gradient_end[2] * ratio)
                    draw.line([(0, y), (image.width, y)], fill=(r, g, b, 255))


            # Trophy + vertical label
            if show_trophy and not table_only:
                trophy_panel_x = total_width + 40
                trophy_panel_y = total_height - 360
                trophy_panel_w, trophy_panel_h = 200, 340

                try:
                    trophy = Image.open(league_logo_path).convert("RGBA")

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
                    if show_side_label:
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
                    print(f"Error loading trophy or drawing side label: {e}")

            # Header row
            header_y = 80
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
            for position, (_, team_stats) in enumerate(standings_data.iterrows(), start=1):
                x = padding
                #Default row background
                row_bg = top_row if position == 1 else (
                    row_even if position % 2 == 0 else row_odd
                )
                # Promotion / Relegation logic (S24+ only)              
                if season >= 24:
                # Division 2 rules    
                    if is_division_2:
                        if position == 1:
                            row_bg = promotion_green
                        elif position == 2:
                            row_bg = playoff_blue
                # Division 1 rules
                    if is_division_1:
                        if position == num_rows:
                            row_bg = relegation_red
                        elif position == num_rows - 1:
                            row_bg = playoff_blue
                draw.rectangle(
                    [padding, current_y, total_width + padding, current_y + row_height],
                    fill=row_bg,
                    outline=None,
                )

                # Rank
                pos_text = str(position)
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
                team_name = team_stats["team"]
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
                    "mp",
                    "w",
                    "d",
                    "l",
                    "gf",
                    "ga",
                    "gd",
                    "p",
                ]
                for idx_col, header in enumerate([col[0] for col in columns[2:]]):
                    value = str(team_stats[data_keys[idx_col]])
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
            print(
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
        # Generate bare tables (no header/logo inside each, no trophy panel)
        img1_bytes = self.create_standings_image(
            standings_div1, f"{league_name} Division 1", season, show_header=False, show_trophy=False, table_only=True, show_side_label=False,
        )
        img2_bytes = self.create_standings_image(
            standings_div2, f"{league_name} Division 2", season, show_header=False, show_trophy=False, table_only=True, show_side_label=False,
        )
        if not img1_bytes or not img2_bytes:
            return None

        img1 = Image.open(img1_bytes).convert("RGBA")
        img2 = Image.open(img2_bytes).convert("RGBA")

        # Theme for combined image
        is_major = league_name.lower().startswith("major")
        accent_color = (218, 185, 45) if is_major else (176, 40, 49)
        bg_dark = (30, 30, 30)
        gradient_end = (46, 46, 46)
        league_logo_path = (
            MAJOR_LEAGUE_LOGO_PATH
            if league_name.lower().startswith("major")
            else MINOR_LEAGUE_LOGO_PATH
        )


        # Fonts
        try:
            title_font = ImageFont.truetype(DEFAULT_FONT_PATH, 52)
            header_font = ImageFont.truetype(DEFAULT_FONT_PATH, 28)
            row_font = ImageFont.truetype(DEFAULT_FONT_PATH, 22)
            division_font = ImageFont.truetype(DEFAULT_FONT_PATH, 32)
        except Exception:
            title_font = ImageFont.load_default()
            header_font = ImageFont.load_default()
            row_font = ImageFont.load_default()
            division_font = ImageFont.load_default()

        LEFT_MARGIN = 20    

        # Table dimensions (match single table)
        logo_size = 48
        row_height = 64
        padding = 12
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

        # Height reserved for the single global title
        header_height = 30
        width = total_width + 260  # Match single table width (table + trophy panel)
        height = header_height + img1.height + img2.height + 100

        combined = Image.new("RGBA", (width, height), bg_dark)
        draw = ImageDraw.Draw(combined)

        # Gradient background
        for y in range(combined.height):
            ratio = y / combined.height
            r = int(accent_color[0] * (1 - ratio) + gradient_end[0] * ratio)
            g = int(accent_color[1] * (1 - ratio) + gradient_end[1] * ratio)
            b = int(accent_color[2] * (1 - ratio) + gradient_end[2] * ratio)
            draw.line([(0, y), (combined.width, y)], fill=(r, g, b, 255))


        # Paste the two division tables below the header (aligned left)
        # --- Division 1 label ---
        d1_text = "Division 1"
        bbox = draw.textbbox((0, 0), d1_text, font=division_font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

        d1_y = header_height
        draw.text(
            (LEFT_MARGIN + (total_width - tw) // 2, d1_y),
            d1_text,
            font=division_font,
            fill="white",
        )   
        # Paste Division 1 table
        combined.paste(img1, (LEFT_MARGIN, d1_y + th + 10), img1)

        # --- Division 2 label ---
        d2_text = "Division 2"
        bbox = draw.textbbox((0, 0), d2_text, font=division_font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

        d2_y = d1_y + th + 10 + img1.height + 20
        draw.text(
            (LEFT_MARGIN + (total_width - tw) // 2, d2_y),
            d2_text,
            font=division_font,
            fill="white",
        )
        # Paste Division 2 table
        combined.paste(img2, (LEFT_MARGIN, d2_y + th + 10), img2)

        
        # Single trophy + vertical label positioned relative to combined tables
        # trophy_panel_x and trophy_panel_y match single table positioning logic
        trophy_panel_x = total_width + 40
        combined_table_height = img1.height + img2.height
        trophy_panel_y = header_height + combined_table_height - 360
        trophy_panel_w, trophy_panel_h = 200, 340

        try:
            trophy = Image.open(league_logo_path).convert("RGBA")

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
            combined.paste(shadow, (sx, sy), shadow)

            combined.paste(trophy, (center_x, center_y), trophy)

            # Vertical MAJORS/MINORS label (same logic as single table)
            side_label = "MAJORS" if is_major else "MINORS"

            label_top_limit = 20 + header_height  # Offset for header
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
            if ly < label_top_limit:
                ly = label_top_limit
            combined.paste(label_img, (lx, ly), label_img)

        except Exception as e:
            print(f"Error loading trophy or drawing side label: {e}")

        out = io.BytesIO()
        combined.save(out, format="PNG")
        out.seek(0)
        return out

async def setup(bot):
    await bot.add_cog(Standings(bot))