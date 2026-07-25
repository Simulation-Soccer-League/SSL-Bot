import discord
from discord.ui import View, button
from discord.ext import commands
from discord import (app_commands, ButtonStyle,)
import pandas as pd
import typing
import requests
import json 
import asyncio
from db_utils import *
from dotenv import load_dotenv
import os

from milestone_view import (MilestoneView, RecordView)

from utils import (
  getAPI,
  get_team_logo_path,
  GK_STAT_GROUPS,
  OUT_STAT_GROUPS,
  PLAYER_DATA_GROUPS,
  CURRENT_SEASON,
  MILESTONES,
  TEAM_ABBREVIATIONS,
  league_by_id,
  filter_players,
  link_player,
)

load_dotenv(".secrets/.env")
TEST_ID = int(os.getenv("DISCORD_TEST_ID"))

class Milestones(commands.Cog): # create a class for our cog that inherits from commands.Cog
    # this class is used to create a cog, which is a module that can be added to the bot

    def __init__(self, bot): # this is a special method that is called when the cog is loaded
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{__name__} is online!")
    
    
    @staticmethod
    async def milestoneEmbed(actives: pd.DataFrame, stat, base, league) -> discord.Embed:
        # Create and color the embed
        embed = discord.Embed(color = discord.Color(0xBD9523))
        
        if (league == None):
          leagueGroup = "False"
          leagueName = None
        else:
          leagueGroup = "True"
          leagueName = league_by_id.get(league)
        
        # Title
        embed.title = f" { stat.title() } Milestone Chasers"
        embed.description = f"{ leagueName if leagueName is not None else ''}"
        
        lines = {m: [] for m in base}

        if stat in ['saves', 'clean sheets']:
          url = "https://api.simulationsoccer.com/index/careerKeeper"
        else:
          url = "https://api.simulationsoccer.com/index/careerOutfield"
        
        data = await getAPI(url, params = {"name": "ALL", "league": leagueGroup})
        
        if stat == 'saves':
          value = data['saves parried'] + data['saves tipped'] + data['saves held']
          data.insert(len(data.columns)-1, stat, value)
        
        data = data.loc[
          (data['name'].isin(actives['name'])) & 
          (data[stat] > 0.95*base[0]) &
          ( True if leagueName is None else (data['league'] == leagueName))
        ].sort_values(stat, ascending = False)
        
        for index, row in data.iterrows():
          value = row[stat]
          player = row['name']
          pid = row['pid']
          
          for m in base:
            if value < m and (value >= min(m * 0.95, (m - 5))):
              lines[m].append(
                f" { link_player(player, pid) } is { round(m - value, 2) } away from **{ m }** { stat.title() }!"
              )

        for m in base:

          text = "\n".join(lines[m]) if lines[m] else "No players close."

          embed.add_field(
            name = f"## { m } { stat } ##",
            value = text,
            inline = False
          )
            
        return embed
    
    @app_commands.command(name = 'upcoming')
    # @app_commands.guilds(discord.Object(id=TEST_ID))
    async def upcoming2(
        self, 
        interaction: discord.Interaction, 
        league: typing.Optional[int] = None
      ):
        """Returns active players within 5% (or 5) of specific milestones for given statistics.
        
        Args:
          league(int) : Optional limited to a specific league (0: The Cup, 1: Major League, 2: Minor League, 5: WSFC)
        """
        await interaction.response.defer()
        
        actives = await getAPI("https://api.simulationsoccer.com/player/getAllPlayers", params = {"active": "true"})
        
        stat, base = next(iter(MILESTONES.items()))
        
        embed = await self.milestoneEmbed(actives, stat, base, league)
        
        print("Get first embed")
        
        view = MilestoneView(
          self,
          actives,
          league
        )
        
        print("view created")
        
        msg = await interaction.followup.send(embed = embed, view = view)
        view.message = msg

    @staticmethod
    async def recordEmbed(actives: pd.DataFrame, stat, league, team) -> discord.Embed:
        # Create and color the embed
        embed = discord.Embed(color = discord.Color(0xBD9523))
        
        if (league is None):
          leagueGroup = "False"
          leagueName = None
        else:
          leagueGroup = "True"
          leagueName = league_by_id.get(league)
          
        if (team is None):
          organization = None
          orgGroup = "False"
        elif (TEAM_ABBREVIATIONS[team.lower()] is None):
          organization = None
          orgGroup = "False"
        else:
          organization = TEAM_ABBREVIATIONS[team.lower()]
          orgGroup = "True"
        
        # Title
        embed.title = f" { stat.title() } Record Chasers"
        embed.description = f"{ organization if organization is not None else ''} { leagueName if leagueName is not None else ''}"
        
        if stat in ['saves', 'clean sheets']:
          url = "https://api.simulationsoccer.com/index/careerKeeper"
        else:
          url = "https://api.simulationsoccer.com/index/careerOutfield"
        
        data = await getAPI(url, params = {"name": "ALL", "league": leagueGroup, "club": orgGroup})
        
        if stat == 'saves':
          value = data['saves parried'] + data['saves tipped'] + data['saves held']
          data.insert(len(data.columns)-1, stat, value)
        
        dataFilter = filter_players(data, league = leagueName, club = organization)
        
        record = dataFilter.loc[
          ( dataFilter[stat] == max(dataFilter[stat]) )
        ]

        recordValue = record[stat].iloc[0]
        recordName = record['name']
        recordPid = record['pid']
        recordActive = recordName.isin(actives['name']).iloc[0]
        
        embed.add_field(
            name = f"## Current { stat.title() } Record Holder ##",
            value = f" **{ link_player(recordName, recordPid) }**{ '*' if recordActive else ''} with **{ recordValue }** { stat.title() }!",
            inline = False
          )
        
        embed.set_footer(text = "* means the record setter is still active.")
        
        data = dataFilter.loc[
          (dataFilter['name'].isin(actives['name'])) & 
          ((dataFilter[stat] > 0.90*recordValue) & (dataFilter[stat] < recordValue))
        ].sort_values(stat, ascending = False)
        
        lines = []
        
        for index, row in data.iterrows():
          value = row[stat]
          player = row['name']
          pid = row['pid']
          
          lines.append(
            f" { link_player(player, pid) } is { round(recordValue - value, 2) } away from the record!"
          )
        
        text = "\n".join(lines) if lines else "No players close."  
        
        embed.add_field(
          name = "## The Chasers ##",
          value = text,
          inline = False
        )
            
        return embed
    
    @app_commands.command(name = 'upcoming_records')
    # @app_commands.guilds(discord.Object(id=TEST_ID))
    async def upcoming_records(
      self, 
      interaction: discord.Interaction, 
      league: typing.Optional[int] = None,
      team: typing.Optional[str] = None
      ):
        """Returns active players within 10% of the record for the given statistic.
        
        Args:
          league(int) : Optional limited to a specific league (0: The Cup, 1: Major League, 2: Minor League, 5: WSFC)
          team(str) : Optional limited to a specific team (using official 3-4 letter abbreviation)
        """
        await interaction.response.defer()
        
        actives = await getAPI("https://api.simulationsoccer.com/player/getAllPlayers", params = {"active": "true"})
        
        stat, base = next(iter(MILESTONES.items()))
        
        embed = await self.recordEmbed(actives, stat, league, team)
        
        view = RecordView(
          self,
          actives,
          league,
          team
        )
        
        msg = await interaction.followup.send(embed = embed, view = view)
        view.message = msg
        
        
async def setup(bot): # this is called by Pycord to setup the cog
    await bot.add_cog(Milestones(bot)) # add the cog to the bot
