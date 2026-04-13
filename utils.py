from PIL import Image, ImageDraw, ImageFont
import requests
import json 
import pandas as pd
import os
import aiohttp
# from pytablericons import TablerIcons, OutlineIcon, FilledIcon


DEFAULT_FONT_PATH = "./fonts/GOTHAM-BOLD.TTF"
STANDINGSAPIBASEURL = "https://api.simulationsoccer.com/index/standings"
NA_PLACEHOLDER = "N/A"
LEAGUEIDMAPPING = {
    "major": 1,
    "minor": 2,
    "ssl cup": 0,
    "ssl shield": 0,
    "wsfc": 5
}
MAJOR_LEAGUE_TEAMS_LIST = [
    "CA Buenos Aires", "Tokyo S.C.", "Hollywood FC", "CF Catalunya", "A.C. Romana",
    "União São Paulo", "Reykjavik United", "Schwarzwälder FV", "Shanghai Dragons FC", "CD Tenochtitlan", "Xelajú Cósmico FC", "Liffeyside Celtic FC"
]

MINOR_LEAGUE_TEAMS_LIST = [
    "AS Paris", "Montréal United", "Rapid Magyar SC", "Inter London", "Krung Thep FC",
    "North Shore United", "Athênai F.C.", "Cairo City", "Seoul MFC", "F.C. Kaapstad", "AF Masques Sacrés", "CS Rova Mpanjaka"
]
ALL_MAIN_TOURNAMENT_TEAMS = MAJOR_LEAGUE_TEAMS_LIST + MINOR_LEAGUE_TEAMS_LIST

ACADEMY_TEAMS = []

TEAM_ABBREVIATIONS = {
    "usp": "União São Paulo", "sao paulo": "União São Paulo", "asp": "AS Paris", "paris": "AS Paris",
    "asparis": "AS Paris", "cdt": "CD Tenochtitlan", "acr": "A.C. Romana", "sfv": "Schwarzwälder FV",
    "reyk": "Reykjavik United", "cata": "CF Catalunya", "hol": "Hollywood FC", "tok": "Tokyo S.C.",
    "sha": "Shanghai Dragons FC", "caba": "CA Buenos Aires", "mont": "Montréal United",
    "magyar": "Rapid Magyar SC", "london": "Inter London", "ktp": "Krung Thep FC",
    "nsu": "North Shore United", "athenai": "Athênai F.C.", "cairo": "Cairo City",
    "seoul": "Seoul MFC", "kaapstad": "F.C. Kaapstad", "ath": "Athênai F.C.", "cai": "Cairo City",
    "hol": "Hollywood FC", "lon": "Inter London", "tok": "Tokyo S.C.", "mtl": "Montréal United",
    "cat": "CF Catalunya", "seo": "Seoul MFC", "par": "AS Paris", "fck": "F.C. Kaapstad",
    "rkv": "Reykjavik United", "sfv": "Schwarzwälder FV", "nsu": "North Shore United",
    "sha": "Shanghai Dragons FC", "mag": "Rapid Magyar SC", "kth": "Krung Thep FC",
    "buenos aires": "CA Buenos Aires", "tokyo": "Tokyo S.C.", "hollywood": "Hollywood FC",
    "hfc": "Hollywood FC", "catalunya": "CF Catalunya", "romana": "A.C. Romana",
    "roma": "A.C. Romana", "uniao": "União São Paulo", "reykjavik": "Reykjavik United",
    "schwarzwalder": "Schwarzwälder FV", "black forest": "Schwarzwälder FV",
    "shanghai": "Shanghai Dragons FC", "tenochtitlan": "CD Tenochtitlan", "paris": "AS Paris",
    "montreal": "Montréal United", "mon": "Montréal United", "rapid magyar": "Rapid Magyar SC",
    "london": "Inter London", "inter": "Inter London", "krung thep": "Krung Thep FC",
    "north shore": "North Shore United", "athenai": "Athênai F.C.", "cairo": "Cairo City",
    "seoul": "Seoul MFC", "kaapstad": "F.C. Kaapstad", "xelaju": "Xelajú Cósmico FC",
    "afmsd" : "AF Masques Sacrés", "liffeyside": "Liffeyside Celtic FC", "csrm": "CS Rova Mpanjaka",
    "xcfc": "Xelajú Cósmico FC", "lcfc": "Liffeyside Celtic FC", "xlc": "Xelajú Cósmico FC",
    "msd" : "AF Masques Sacrés", "lif": "Liffeyside Celtic FC", "rmp": "CS Rova Mpanjaka", "rova": "CS Rova Mpanjaka"
}

OUT_STAT_GROUPS = {
  "Physical": ["apps", "minutes played", "distance run (km)", "dribbles", "player of the match", "yellow cards", "red cards", "fouls", "fouls against", "average rating"],
  "Attack": ["goals", "xg", "shots on target", "shots", "penalties taken", "penalties scored", "goals outside box", "xg overperformance", "offsides", "fk shots", "shot accuracy%", "pen adj xG"],
  "Creative": ["assists", "xa", "successful passes", "attempted passes", "pass%", "key passes", "successful crosses", "attempted crosses", "cross%", "chances created", "progressive passes", "open play key passes", "successful open play crosses", "attempted open play crosses", "open play crosses%"],
  "Defense": ["tackles won", "attempted tackles", "tackle%", "key tackles", "interceptions", "clearances", "mistakes leading to goals", "blocks", "key headers", "successful headers", "attempted headers", "header%", "shots blocked", "successful presses", "attempted presses", "press%"]
}

GK_STAT_GROUPS = {
  "Physical": ["apps", "minutes played", "player of the match", "average rating"],
  "Goalkeeper": ["won", "drawn", "lost", "clean sheets", "saves parried", "saves held", "saves tipped", "conceded", "save%", "penalties faced", "penalties saved", "xg prevented"]
}

PLAYER_DATA_GROUPS = {
  "Player Information": ["class", "tpe", "tpebank", "render", "username", "traits"]
}

MILESTONES = {
  "apps": [100, 200, 300], 
  "goals": [50, 100, 150, 200], 
  "assists": [50, 100, 150], 
  "saves": [500, 750, 1000, 1250], 
  "clean sheets": [25, 50, 75],
  "distance run (km)": [2500, 3000, 3500, 4000], 
  "successful passes": [5000, 7500, 10000, 12500, 15000], 
  "tackles won": [500, 750, 1000], 
  "interceptions": [500, 750, 1000]
}

LEAGUEIDMAP = {
  "The Cup": 0,
  "Major League": 1,
  "Minor League": 2,
  "WSFC": 5
}

league_by_id = { v: k for k, v in LEAGUEIDMAP.items() }

season = requests.get('https://api.simulationsoccer.com/admin/getCurrentSeason')

CURRENT_SEASON = int(pd.DataFrame(json.loads(season.content))['season'].iloc[0])

DEFAULT_LOGO_PATH = "./graphics/logos/league-logo.png"  
MAJOR_LEAGUE_LOGO_PATH = "./graphics/logos/major_league_logo.png"
MINOR_LEAGUE_LOGO_PATH = "./graphics/logos/minor_league_logo.png"
MAJORS_DIV1_LOGO_PATH = "./graphics/logos/majors_div1.png"
MAJORS_DIV2_LOGO_PATH = "./graphics/logos/majors_div2.png"
MINORS_DIV1_LOGO_PATH = "./graphics/logos/minors_div1.png"
MINORS_DIV2_LOGO_PATH = "./graphics/logos/minors_div2.png"

def get_team_logo_path(team_name): # Returns the file path for the team logo image based on the team name.
    team_key = team_name.lower()
    imagename = team_key.replace(' ', '_')
    
    if team_key in{t.lower() for t in ALL_MAIN_TOURNAMENT_TEAMS}:
        team_logo_path = f"graphics/logos/{imagename}.png"
    
    elif team_key in{t.lower() for t in ACADEMY_TEAMS}:
        team_logo_path = f"graphics/logos/academy_{imagename}.png"    
    else: 
        return DEFAULT_LOGO_PATH
      
    if os.path.isfile(team_logo_path): # If the file does not exist, returns the default logo path.
        return team_logo_path
    else:
        return DEFAULT_LOGO_PATH

MAJOR_TROPHY_PATH= "./graphics/trophies/SSL_Major_Trophy_Front.png"
MINOR_TROPHY_PATH= "./graphics/trophies/SSL_Minor_Trophy_Front.png"

async def getAPI(endpoint, params = None):
  async with aiohttp.ClientSession() as session:
    try:
      async with session.get(endpoint, params=params, timeout=15) as resp:
        if resp.status != 200:
            print("getAPI error: HTTP", resp.status)
            return None

        data = await resp.json()

        # If API returns a list, convert directly
        if isinstance(data, list):
            return pd.DataFrame(data)

        # If API returns a dict, wrap it in a list
        if isinstance(data, dict):
            return pd.DataFrame([data])

        print("getAPI error: unexpected JSON type", type(data))
        return None

    except Exception as e:
      print("getAPI exception:", e)
      return None


