import discord
from discord.ext import commands
from discord import app_commands
import requests
import datetime
import asyncio
from PIL import Image, ImageDraw, ImageFont
import io
import urllib.parse
from dotenv import load_dotenv
import os
import sys
import re

# Fix import path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv(".secrets/.env")
# TEST_ID = int(os.getenv("DISCORD_TEST_ID", 0))

# ---------------- CONFIG ---------------- #
from utils import (
    SCORESAPIBASEURL,
    BOXSCOREAPIBASEURL,
    CURRENT_SEASON,
    DEFAULT_FONT_PATH,
    TEAM_ABBREVIATIONS,
    DEFAULT_PRIMARY_COLOR,
    get_team_logo_path,
    get_team_colors_from_api
)

DATE_FORMAT_STR = "%Y-%m-%d"

FILENAME_NEXT_MATCH_IMAGE = "next_match.png"
FILENAME_LAST_MATCH_IMAGE = "last_match.png"
DEFAULT_SCORE_COLOR = (7, 11, 81, 255)

ALL_TEAMS = set(TEAM_ABBREVIATIONS.values())

# ---------------- HELPERS ---------------- #

def get_matchday_help_embed():
    embed = discord.Embed(
        title="Matchday Format Help",
        description="Here are the valid formats you can use for Matchday:",
        color=0x2b2d31
    )

    embed.add_field(
        name="League Matchdays",
        value=(
            "• `1` → Matchday 1 (Used for seasons before S24 in Majors/Minors)\n"
            "• `1.1` → Division 1 Matchday 1\n"
            "• `2.5` → Division 2 Matchday 5"
        ),
        inline=False
    )

    embed.add_field(
        name="Cup Stages",
        value=(
            "• `FR` → First Round\n"
            "• `QF` / `QF1` → Quarter Finals (Leg 1 in case it was two legged)\n"
            "• `SF` / `SF2` → Semi Finals (Leg 2 in case it was two legged)\n"
            "• `F` → Final"
        ),
        inline=False
    )

    embed.add_field(
        name="Special",
        value="• `Shi` → SSL Shield",
        inline=False
    )


    return embed

def get_league_id_from_match(match):
    return match.get("MatchType", 1)


def get_league_display_name(match):
    match_type = match.get("MatchType")
    matchday = match.get("MatchDay")

    if match_type == 1:
        return "Major League"
    if match_type == 2:
        return "Minor League"
    if match_type == -1:
        return "Pre-season Friendly"
    if match_type == 5:
        return "WSFC"
    if match_type == 0:
        if str(matchday).lower() == "shi":
            return "SSL Shield"
        return "SSL Cup"

    return "Major League"


def resolve_team(name: str):
    name = name.lower().strip()
    if name in TEAM_ABBREVIATIONS:
        return TEAM_ABBREVIATIONS[name]
    for t in ALL_TEAMS:
        if t.lower() == name:
            return t
    return None


def parse_date(date_str):
    try:
        return datetime.datetime.strptime(date_str, DATE_FORMAT_STR).date()
    except Exception:
        return None


def get_api_data(season):
    url = f"{SCORESAPIBASEURL}?season={season}&league=ALL"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json()


def get_boxscore(season, league_id, matchday, team):
    try:
        team = urllib.parse.quote(team)
        url = f"{BOXSCOREAPIBASEURL}?season={season}&league={league_id}&matchday={matchday}&team={team}"

        r = requests.get(url, timeout=10)
        r.raise_for_status()

        data = r.json()

        if isinstance(data, list) and len(data) > 0:
            return data[0]

        logger.warning(f"Boxscore unexpected response: {data}")
        return None

    except Exception as e:
        logger.error(f"Boxscore fetch failed: {e}")
        return None


def create_linear_gradient(width, height, start_color, end_color):
    image = Image.new("RGBA", (width, height))
    pixels = image.load()

    for x in range(width):
        ratio = x / width
        r = int(start_color[0] + (end_color[0] - start_color[0]) * ratio)
        g = int(start_color[1] + (end_color[1] - start_color[1]) * ratio)
        b = int(start_color[2] + (end_color[2] - start_color[2]) * ratio)
        a = int(start_color[3] + (end_color[3] - start_color[3]) * ratio)

        for y in range(height):
            pixels[x, y] = (r, g, b, a)

    return image


def create_matchup_image(team1, score1, team2, score2, team_colors):
    try:
        # -------- CONFIG -------- #
        width, height = 1200, 320
        bottom_bar_height = 70
        logo_size = 150

        # -------- COLOR HELPERS -------- #
        def get_color(team, key, fallback):
            return team_colors.get(team, {}).get(key, fallback)

        def luminance(color):
            r, g, b = color[:3]
            return 0.299*r + 0.587*g + 0.114*b

        def is_near_white(color, threshold=200):
            return luminance(color) > threshold
        

        def get_text_color(bg):
            return (0, 0, 0) if luminance(bg) > 160 else (255, 255, 255)
    
        def ensure_contrast(text_color, bg_color):
            return text_color if abs(luminance(text_color) - luminance(bg_color)) > 60 else get_text_color(bg_color)

        left_primary = get_color(team1, "primary", DEFAULT_PRIMARY_COLOR)
        left_secondary = get_color(team1, "secondary", left_primary)
        left_tertiary = get_color(team1, "tertiary", left_primary)

        right_primary = get_color(team2, "primary", DEFAULT_PRIMARY_COLOR)
        right_secondary = get_color(team2, "secondary", right_primary)
        right_tertiary = get_color(team2, "tertiary", right_primary)

        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))

        
        # -------- SMART GRADIENT DIRECTION -------- #

        
        left_start, left_end = left_primary, (255, 255, 255, 255)
        right_start, right_end = (255, 255, 255, 255), right_primary

        
        left_half = create_linear_gradient(
        width // 2, height - bottom_bar_height,
        left_start, left_end
        )

        right_half = create_linear_gradient(
        width - width // 2, height - bottom_bar_height,
        right_start, right_end
        )

        img.paste(left_half, (0, 0))
        img.paste(right_half, (width // 2, 0))

        draw = ImageDraw.Draw(img)

        # -------- LOGOS -------- #
        logo1 = Image.open(get_team_logo_path(team1)).convert("RGBA").resize((logo_size, logo_size))
        logo2 = Image.open(get_team_logo_path(team2)).convert("RGBA").resize((logo_size, logo_size))

        logo_y = (height - bottom_bar_height) // 2 - logo_size // 2

        img.paste(logo1, (int(width * 0.25 - logo_size / 2), logo_y), logo1)
        img.paste(logo2, (int(width * 0.75 - logo_size / 2), logo_y), logo2)

        draw.rectangle((0, height - bottom_bar_height, width // 2, height), fill=left_secondary)
        draw.rectangle((width // 2, height - bottom_bar_height, width, height), fill=right_secondary)

        # -------- TEXT COLORS -------- #
        left_text_color = ensure_contrast(left_tertiary, left_secondary)
        right_text_color = ensure_contrast(right_tertiary, right_secondary)
       
        def is_black(color, threshold=40):
            return luminance(color) < threshold

        if is_near_white(left_secondary) and is_black(left_text_color):
            left_text_color = left_primary
        if is_black(left_secondary) and is_near_white(left_text_color):
            left_text_color = left_primary    

        
        try:
            font_score = ImageFont.truetype(DEFAULT_FONT_PATH, 110)
            font_small = ImageFont.truetype(DEFAULT_FONT_PATH, 40)
        except:
            font_score = ImageFont.load_default()
            font_small = ImageFont.load_default()

        # -------- TEAM NAMES -------- #
        draw.text(
            (width // 4, height - bottom_bar_height // 2),
            team1.upper(),
            font=font_small,
            fill=left_text_color,
            anchor="mm"
        )

        draw.text(
            (3 * width // 4, height - bottom_bar_height // 2),
            team2.upper(),
            font=font_small,
            fill=right_text_color,
            anchor="mm"
        )

        if score1 is not None:
            draw.text(
                (width // 2 - 80, (height - bottom_bar_height) // 2),
                str(score1),
                font=font_score,
                fill=DEFAULT_SCORE_COLOR,
                anchor="mm"
            )

            draw.text(
                (width // 2 + 80, (height - bottom_bar_height) // 2),
                str(score2),
                font=font_score,
                fill=DEFAULT_SCORE_COLOR,
                anchor="mm"
            )
        else:
            draw.text(
                (width // 2, (height - bottom_bar_height) // 2),
                "VS",
                font=font_score,
                fill=DEFAULT_SCORE_COLOR,
                anchor="mm"
            )


        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer

    except Exception as e:
        logger.error(f"Match image error: {e}")
        return None

# ---------------- MATCH DETAILS FORMAT ---------------- #

def format_match_details(match, box):
    league_name = get_league_display_name(match)
    matchday = match.get("MatchDay")
    matchday = match.get("MatchDay")

    matchday_str = ""
    if matchday:
        md = str(matchday)

        if "." in md:
            # Format: 1.1 → Division 1 Matchday 1
            try:
                div, day = md.split(".")
                matchday_str = f" | Division {int(div)} Matchday {int(day)}"
            except:
                matchday_str = f" | {md}"
        else:
            # Format: 1 → Matchday 1
            try:
                matchday_str = f" | Matchday {int(md)}"
            except:
                matchday_str = f" | {md}"

    desc = (
        f"**Match Details**\n"
        f"**Date**: {match.get('IRLDate')}\n"
        f"**League**: {league_name}{matchday_str}\n"
        f"**Match**: **{match.get('Home')}** {match.get('HomeScore')} - {match.get('AwayScore')} **{match.get('Away')}**"
    )

    if isinstance(box, dict):
        desc += f"\n**{match.get('Home')} Scorers**: {box.get('homeGoals', 'None')}"
        desc += f"\n**{match.get('Home')} Assists**: {box.get('homeAssists', 'None')}"
        desc += f"\n**{match.get('Away')} Scorers**: {box.get('awayGoals', 'None')}"
        desc += f"\n**{match.get('Away')} Assists**: {box.get('awayAssists', 'None')}"
        desc += f"\n**Player of the Match**: {box.get('Player of the Match', 'N/A')}"

    return desc


# ---------------- COG ---------------- #

class Scores(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.team_colors = {} 
        
    async def ensure_team_colors(self):
        if not self.team_colors:
            try:
                colors = await get_team_colors_from_api()

                if not colors:
                    raise ValueError("Empty color data")

                self.team_colors = colors
                print(f" Loaded {len(colors)} team colors")

            except Exception as e:
                print(" Failed to load team colors:", e)
                self.team_colors = {}
        

    async def fetch_api(self, season):
        return await asyncio.to_thread(get_api_data, season)

    async def fetch_boxscore(self, season, league_id, matchday, team):
        return await asyncio.to_thread(get_boxscore, season, league_id, matchday, team)

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{__name__} is online!")
        

    # -------- LAST MATCH -------- #
    @app_commands.command(name="last_match", description="Get the most recent completed match for a team.")
    @app_commands.describe(
    team="Team name or abbreviation"
    )
    
    # @app_commands.guilds(discord.Object(id=TEST_ID))
    async def last_match(self, interaction: discord.Interaction, team: str, season: str = str(CURRENT_SEASON)):
        await interaction.response.defer()
        await self.ensure_team_colors()
        team_name = resolve_team(team)
        if not team_name:
            return await interaction.followup.send("No such team found.")

        data = await self.fetch_api(season)

        matches = [
            (parse_date(m.get("IRLDate")), m)
            for m in data
            if team_name in [m.get("Home"), m.get("Away")]
            and m.get("HomeScore") is not None
        ]

        if not matches:
            return await interaction.followup.send("No matches found.")

        match = sorted(matches, key=lambda x: x[0], reverse=True)[0][1]

        league_id = get_league_id_from_match(match)

        box = await self.fetch_boxscore(season, league_id, match.get("MatchDay"), team_name)

        desc = format_match_details(match, box)

        embed = discord.Embed(title=f"Last Match details for {team_name}", description=desc)

        image = await asyncio.to_thread(create_matchup_image,
                                        match.get("Home"), match.get("HomeScore"),
                                        match.get("Away"), match.get("AwayScore"),
                                        self.team_colors)

        if image:
            file = discord.File(image, filename=FILENAME_LAST_MATCH_IMAGE)
            embed.set_image(url=f"attachment://{FILENAME_LAST_MATCH_IMAGE}")
            await interaction.followup.send(embed=embed, file=file)
        else:
            await interaction.followup.send(embed=embed)

    # -------- NEXT MATCH -------- #
    @app_commands.command(name="next_match", description="Get the next scheduled match for a team.")
    @app_commands.describe(
    team="Team name or abbreviation"
    )
    # @app_commands.guilds(discord.Object(id=TEST_ID))
    async def next_match(self, interaction: discord.Interaction, team: str, season: str = str(CURRENT_SEASON)):
        await interaction.response.defer()
        await self.ensure_team_colors()
        team_name = resolve_team(team)
        if not team_name:
            return await interaction.followup.send("Unknown team")

        data = await self.fetch_api(season)

        matches = [
            (parse_date(m.get("IRLDate")), m)
            for m in data
            if m.get("IRLDate")
            and team_name in [m.get("Home"), m.get("Away")]
            and m.get("HomeScore") is None
        ]

        if not matches:
            return await interaction.followup.send("No upcoming matches found.")

        match = sorted(matches, key=lambda x: x[0])[0][1]

        league_name = get_league_display_name(match)
        matchday = match.get("MatchDay")
        matchday_str = ""
        if matchday:
            md = str(matchday)

            if "." in md:
                # Format: 1.1 → Division 1 Matchday 1
                try:
                    div, day = md.split(".")
                    matchday_str = f" | Division {int(div)} Matchday {int(day)}"
                except:
                    matchday_str = f" | {md}"
            else:
                # Format: 1 → Matchday 1
                try:
                    matchday_str = f" | Matchday {int(md)}"
                except:
                    matchday_str = f" | {md}"


        desc = (
            f"**Match Details**\n"
            f"**Date**: {match.get('IRLDate')}\n"
            f"**League**: {league_name}{matchday_str}\n"
            f"**Match**: **{match.get('Home')}** vs **{match.get('Away')}**"
        )

        embed = discord.Embed(title=f"Next Match details for {team_name}", description=desc)

        image = await asyncio.to_thread(
            create_matchup_image,
            match.get("Home"), None,
            match.get("Away"), None,
            self.team_colors
        )

        if image:
            file = discord.File(image, filename=FILENAME_NEXT_MATCH_IMAGE)
            embed.set_image(url=f"attachment://{FILENAME_NEXT_MATCH_IMAGE}")
            await interaction.followup.send(embed=embed, file=file)
        else:
            await interaction.followup.send(embed=embed)

    # -------- SEARCH MATCH -------- #
    @app_commands.command(name="search_match", description="Search for matches by season, competition, and matchday.")
    # @app_commands.guilds(discord.Object(id=TEST_ID))
    @app_commands.describe(
    season="Season number (e.g., 25)",
    competition="Select the competition",
    matchday="Matchday Format: 1, 1.1, QF1, Shi | Use /matchday_help to know more about the format",
    team="Optional: Filter by a specific team"
    )
    @app_commands.choices(
        competition=[
            app_commands.Choice(name="Major League", value=1),
            app_commands.Choice(name="Minor League", value=2),
            app_commands.Choice(name="SSL Cup / Shield", value=0),
            # app_commands.Choice(name="WSFC", value=5),
            # app_commands.Choice(name="Pre-season Friendly", value=-1),
        ]
    )
    async def search_match(
        self,
        interaction: discord.Interaction,
        season: str,
        competition: app_commands.Choice[int],
        matchday: str,
        team: str = None
    ):
        await interaction.response.defer()
        
        
        await self.ensure_team_colors()
        league_id = competition.value

        team_name = None
        if team:
            team_name = resolve_team(team)
            if not team_name:
                return await interaction.followup.send("Invalid team name.")

        data = await self.fetch_api(season)

        matches = [
            m for m in data
            if str(m.get("MatchDay")).lower() == str(matchday).lower()
            and m.get("MatchType") == league_id
            and (team_name is None or team_name in [m.get("Home"), m.get("Away")])
        ]

        if not matches:
            return await interaction.followup.send("No matches found.")
        
        # ---- TITLE LOGIC ---- #

        if league_id == 0:
            if str(matchday).lower() == "shi":
                title_text = f"Season {season} | SSL Shield"
            
            else:
                # --- Stage mapping ---
                stage_map = {
                "FR": "First Round",
                "QF": "Quarter Finals",
                "SF": "Semi Finals",
                "F": "Final"
                }

                # --- Extract stage + leg (if any) ---
                md = str(matchday).upper()
                match = re.match(r"(FR|QF|SF|F)(\d+)?", md)

                if match:
                    stage_code = match.group(1)
                    leg = match.group(2)

                    stage_name = stage_map.get(stage_code, stage_code)

                    if leg:
                        title_text = f"Season {season} | SSL Cup {stage_name} Leg {leg}"
                    else:
                        title_text = f"Season {season} | SSL Cup {stage_name}"

                else:
                    # fallback (just in case)
                    title_text = f"Season {season} | SSL Cup {md}"
        else:   

            title_text = f"Season {season} | {competition.name} | Matchday {matchday}"

        embeds = []
        files = []

        for i, match in enumerate(matches):
            box = None

            if match.get("HomeScore") is not None:
                box = await self.fetch_boxscore(
                    season,
                    league_id,
                    match.get("MatchDay"),
                    match.get("Home")
                )

            desc = format_match_details(match, box)

            embed = discord.Embed(
                title=title_text,
                description=desc
            )

            image = await asyncio.to_thread(
                create_matchup_image,
                match.get("Home"), match.get("HomeScore"),
                match.get("Away"), match.get("AwayScore"),
                self.team_colors
            )

            if image:
                filename = f"match_{i}.png"
                file = discord.File(image, filename=filename)
                embed.set_image(url=f"attachment://{filename}")
                files.append(file)

            embeds.append(embed)

        await interaction.followup.send(embeds=embeds, files=files)

    # -------- MATCHDAY HELP -------- #
    
    @app_commands.command(
    name="matchday_help",
    description="Show matchday format guide"
    )
    # @app_commands.guilds(discord.Object(id=TEST_ID))
    async def matchday_help(self, interaction: discord.Interaction):
        embed = get_matchday_help_embed()
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Scores(bot))