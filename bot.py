import discord
from discord.ext import commands
import sys

_ME = 397174722229698569

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())
bot.vya_dev_mode = False
for x in sys.argv:
    if x == '--dev':
        bot.vya_dev_mode = True

@bot.event
async def on_ready():
    if not bot.vya_dev_mode:
        await bot.load_extension('cogs.dispatch.dispatch')
        await bot.load_extension('cogs.screenshot.screenshot')
        await bot.load_extension('cogs.vatsim.vatsim')
    await bot.load_extension('cogs.reports.reports')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="your landings."))

@bot.command()
async def reload(ctx, *args):
    if ctx.message.author.id != _ME:
        return
    exts = []
    for x in bot.extensions:
        exts.append(x)
    for x in exts:
        print(x)
        if len(args) == 0 or x.split('.')[-1] == args[0]:
            await ctx.send(f'reloading {x}')
            await bot.reload_extension(x)
    await ctx.send('reloaded')

tokenpath = 'discord-token.txt'
if bot.vya_dev_mode:
    tokenpath = 'discord-token.dev.txt'
with open(tokenpath) as f:
    bot.run(f.read())
