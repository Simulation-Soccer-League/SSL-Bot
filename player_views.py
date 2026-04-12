from discord.ui import View, button
from discord import ButtonStyle
import discord
import pandas as pd

from utils import (
  CURRENT_SEASON,
)

class PlayerStatsView(View):
    def __init__(self, cog, portalData, aggregateData, careerData):
        super().__init__(timeout = 300) # Time out after 5 minutes
        self.cog = cog
        self.portalData = portalData
        self.aggregateData = aggregateData
        self.careerData = careerData
        
        self.children[0].disabled = True
        
        playerExistCurrent = CURRENT_SEASON in self.aggregateData['season'].values
        if not playerExistCurrent:
          # Removes the Current Season stats button if there is no data there
          self.remove_item(self.children[1])

    @button(label="Player Info", style=ButtonStyle.success)
    async def player_info(self, interaction: discord.Interaction, button):
        for child in self.children:
          child.disabled = False
        button.disabled = True
        
        embed, file = self.cog.playerStatsEmbed(self.portalData, None)
        
        await interaction.response.edit_message(embed = embed, attachments = [file], view = self)

    @button(label=f"S{CURRENT_SEASON} Stats", style=ButtonStyle.success)
    async def season_stats(self, interaction: discord.Interaction, button):
        for child in self.children:
          child.disabled = False
        button.disabled = True
        
        season_df = self.aggregateData[self.aggregateData["season"] == CURRENT_SEASON]
        
        embed, file = self.cog.playerStatsEmbed(self.portalData, season_df)

        await interaction.response.edit_message(embed = embed, attachments = [file], view = self)

    @button(label="Career Totals", style=ButtonStyle.success)
    async def career_totals(self, interaction: discord.Interaction, button):
        for child in self.children:
          child.disabled = False
        button.disabled = True
        
        embed, file = self.cog.playerStatsEmbed(self.portalData, self.careerData)
        
        await interaction.response.edit_message(embed = embed, attachments = [file], view = self)
