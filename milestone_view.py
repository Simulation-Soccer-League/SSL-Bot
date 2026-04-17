from discord.ui import View, button, Select
from discord import ButtonStyle, SelectOption
import discord
import pandas as pd

from utils import (
  CURRENT_SEASON,
  MILESTONES,
)


class MilestoneSelect(discord.ui.Select):
  def __init__(self, ancestor):
    self.ancestor = ancestor

    # Add all options based on MILESTONES
    options = [
      discord.SelectOption(
        label = stat.title(),
        value = stat
      )
      for stat in MILESTONES.keys()
    ]

    super().__init__(
        placeholder = "Choose an option...",
        min_values = 1,
        max_values = 1,
        options = options
    )

  async def callback(self, interaction: discord.Interaction):
    value = self.values[0]
    base = MILESTONES[value]
    
    embed = await self.ancestor.cog.milestoneEmbed(
      self.ancestor.actives, 
      value, 
      base, 
      self.ancestor.league
    )
    
    # If this interaction has not been responded to yet:
    if interaction.response.is_done():
        # Use followup
        await interaction.followup.edit_message(
            message_id = interaction.message.id,
            embed = embed,
            view = self.ancestor
        )
    else:
        # First response
        await interaction.response.edit_message(
            embed = embed,
            view = self.ancestor
        )


class MilestoneView(View):
  def __init__(self, cog, actives, league):
    super().__init__(timeout = 60)
    self.cog = cog
    self.actives = actives
    self.league = league
    
    self.add_item(MilestoneSelect(self))
    
  async def on_timeout(self):
    for child in self.children:
      child.disabled = True

      # Fully disable select menus visually
      if isinstance(child, discord.ui.Select):
        child.placeholder = " "
        child.options = [discord.SelectOption(label="TIMED OUT", value="disabled")]

    try:
        await self.message.edit(view=self)
    except Exception as e:
        print("Timeout edit failed:", e)

class RecordSelect(discord.ui.Select):
  def __init__(self, ancestor):
    self.ancestor = ancestor

    # Add all options based on MILESTONES
    options = [
      discord.SelectOption(
        label = stat.title(),
        value = stat
      )
      for stat in MILESTONES.keys()
    ]

    super().__init__(
        placeholder = "Choose an option...",
        min_values = 1,
        max_values = 1,
        options = options
    )

  async def callback(self, interaction: discord.Interaction):
    value = self.values[0]
    
    embed = await self.ancestor.cog.recordEmbed(
      self.ancestor.actives, 
      value, 
      self.ancestor.league,
      self.ancestor.org
    )
    
    # If this interaction has not been responded to yet:
    if interaction.response.is_done():
        # Use followup
        await interaction.followup.edit_message(
            message_id = interaction.message.id,
            embed = embed,
            view = self.ancestor
        )
    else:
        # First response
        await interaction.response.edit_message(
            embed = embed,
            view = self.ancestor
        )

class RecordView(View):
  def __init__(self, cog, actives, league, org):
    super().__init__(timeout = 60) # Time out after 1 minute
    self.cog = cog
    self.actives = actives
    self.league = league
    self.org = org

    self.add_item(RecordSelect(self))
    
  async def on_timeout(self):
    for child in self.children:
      child.disabled = True

      # Fully disable select menus visually
      if isinstance(child, discord.ui.Select):
        child.placeholder = " "
        child.options = [discord.SelectOption(label="TIMED OUT", value="disabled")]

    try:
        await self.message.edit(view=self)
    except Exception as e:
        print("Timeout edit failed:", e)







