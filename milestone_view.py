from discord.ui import View, button
from discord import ButtonStyle
import discord
import pandas as pd

from utils import (
  CURRENT_SEASON,
  MILESTONES,
)

class MilestoneView(View):
    def __init__(self, cog, actives, league):
        super().__init__(timeout = 300) # Time out after 5 minutes
        self.cog = cog
        self.actives = actives
        self.league = league

        # Create one button per milestone
        for stat, base in MILESTONES.items():
            self.add_item(self.make_button(stat, base, league))

        # First button active
        self.children[0].disabled = True
        
    async def on_timeout(self):
        # Disable all buttons
        for child in self.children:
            child.disabled = True

        # Edit the original message to update the disabled state
        try:
            await self.message.edit(view=self)
        except Exception as e:
            print("Timeout edit failed:", e)

    def make_button(self, stat, base, league):
        # Create a button instance
        button = discord.ui.Button(
            label = stat.title(),
            style = discord.ButtonStyle.success
        )
        
        # Define the callback dynamically
        async def callback(interaction: discord.Interaction):
            # Toggle active state
            for child in self.children:
                child.disabled = False
            button.disabled = True
            
            # Build embed for this milestone
            embed = await self.cog.milestoneEmbed(self.actives, stat, base, league)
            
            # If this interaction has not been responded to yet:
            if interaction.response.is_done():
                # Use followup
                await interaction.followup.edit_message(
                    message_id = interaction.message.id,
                    embed = embed,
                    view = self
                )
            else:
                # First response
                await interaction.response.edit_message(
                    embed = embed,
                    view = self
                )

        # Attach callback to button
        button.callback = callback
        return button


class RecordView(View):
    def __init__(self, cog, actives, league, org):
        super().__init__(timeout = 300) # Time out after 5 minutes
        self.cog = cog
        self.actives = actives
        self.league = league
        self.org = org

        # Create one button per milestone
        for stat, base in MILESTONES.items():
            self.add_item(self.make_button(stat, league, org))

        # First button active
        self.children[0].disabled = True
      
    async def on_timeout(self):
        # Disable all buttons
        for child in self.children:
            child.disabled = True

        # Edit the original message to update the disabled state
        try:
            await self.message.edit(view=self)
        except Exception as e:
            print("Timeout edit failed:", e)

    def make_button(self, stat, league, org):
        # Create a button instance
        button = discord.ui.Button(
            label = stat.title(),
            style = discord.ButtonStyle.success
        )
        
        # Define the callback dynamically
        async def callback(interaction: discord.Interaction):
            # Toggle active state
            for child in self.children:
                child.disabled = False
            button.disabled = True
            
            # Build embed for this milestone
            embed = await self.cog.recordEmbed(self.actives, stat, league, org)
            
            # If this interaction has not been responded to yet:
            if interaction.response.is_done():
                # Use followup
                await interaction.followup.edit_message(
                    message_id = interaction.message.id,
                    embed = embed,
                    view = self
                )
            else:
                # First response
                await interaction.response.edit_message(
                    embed = embed,
                    view = self
                )

        # Attach callback to button
        button.callback = callback
        return button
