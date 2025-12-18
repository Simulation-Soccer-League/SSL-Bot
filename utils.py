from PIL import Image, ImageDraw, ImageFont
import os

DEFAULT_FONT_PATH = "./fonts/GOTHAM-BOLD.TTF"
STANDINGSAPIBASEURL = "https://api.simulationsoccer.com/index/standings"
NA_PLACEHOLDER = "N/A"
LEAGUEIDMAPPING = {
    "majors": 1,
    "minors": 2,
    "ssl cup": 0,
    "ssl shield": 0,  
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

CURRENT_SEASON = "23"

DEFAULT_LOGO_PATH = "./graphics/logos/league-logo.png"  
MAJOR_LEAGUE_LOGO_PATH = "./graphics/logos/major_league_logo.png"
MINOR_LEAGUE_LOGO_PATH = "./graphics/logos/minor_league_logo.png"

def get_team_logo_path(team_name): # Returns the file path for the team logo image based on the team name.
    
    team_key = team_name.lower()
    imagename = team_key.replace(' ', '_')

    if team_key in{t.lower() for t in ALL_MAIN_TOURNAMENT_TEAMS}:
        team_logo_path = f"graphics/logos/{imagename}.png"
    
    elif team_key in{t.lower() for t in ACADEMY_TEAMS}:
        team_logo_path = f"graphics/logos/academy_{imagename}.png"    
    
    if os.path.isfile(team_logo_path): # If the file does not exist, returns the default logo path.
        return team_logo_path
    else:
        return DEFAULT_LOGO_PATH

MAJOR_TROPHY_PATH= "./graphics/trophies/SSL_Major_Trophy_Front.png"
MINOR_TROPHY_PATH= "./graphics/trophies/SSL_Minor_Trophy_Front.png"