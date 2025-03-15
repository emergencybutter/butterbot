import logging
import discord
from discord.ext import commands
import sys

_ME = 397174722229698569

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

@bot.event
async def on_ready():
    await bot.load_extension('cogs.dispatch.dispatch')
    await bot.load_extension('cogs.screenshot.screenshot')

@bot.command()
async def reload(ctx):
    if ctx.message.author.id != _ME:
        return
    exts = []
    for x in bot.extensions:
        exts.append(x)
    for x in exts:
        await ctx.send(f'reloading {x}')
        await bot.reload_extension(x)
    await ctx.send('reloaded')

with open('discord-token.txt') as f:
    bot.run(f.read())
