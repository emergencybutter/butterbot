from discord.ext import tasks, commands
import datetime
import discord
import json
import os
import logging


VOYAGER_GREEN = discord.Color.from_str("#3EA2AA")
VOYAGER_ORANGE = discord.Color.from_str("#F05A28")

_BOT_ID = 1287483856446033920
_VOY_EMOJI = 1064727097421090817
_PAPERPLANE_EMOJI = 1368584175980122253
_ORANGE_PAPERPLANE_EMOJI = 1373092931614933002
_BOT_TEST_ID = 1285386906451972096
_SCREENSHOT_ID = 1056720051111219253 
_EMERGENCY_SERVER_SCREENSHOT_ID = 1350203075557855242

_ME = 397174722229698569
_ANDREW = 363023921282547723
_GRANT = 173800542324260865
_ZACH = 626560110457782272
_SMITTY = 470385770465591327
_GABRIEL = 193958938897547264
_GOODFIXINS= 190539300364877824
_JERRAD = 741765887018795029
_LINUS = 538420610708144132
_ALLOWED_USERS = [
        _ME,
        _ANDREW,
        _GRANT,
        _ZACH,
        _SMITTY,
        _GABRIEL,
        _GOODFIXINS,
        _JERRAD,
        _LINUS,
        ]
#_IMAGE_DIR = "/var/www/html/data/images"
_IMAGE_DIR = "images"

def genimagejson():
    files = []
    for f in os.listdir(_IMAGE_DIR):
        if (f.lower().endswith(".jpg") or f.lower().endswith(".png")) and os.path.isfile(os.path.join(_IMAGE_DIR, f)):
            files.append(f)
    files.sort(key=lambda x: -os.path.getmtime(os.path.join(_IMAGE_DIR, x)))
    with open(os.path.join(_IMAGE_DIR, "images.json"), 'w') as f:
        f.write(json.dumps(files))


def is_voyager_emoji(emoji):
    return getattr(emoji, 'id', 0) in [_VOY_EMOJI, _PAPERPLANE_EMOJI, _ORANGE_PAPERPLANE_EMOJI] or str(emoji) == '▫️'

def get_first_image(attachments):
    for attachment in attachments:
        ctype = attachment.content_type
        if ctype.split('/')[0] == 'image':
            return attachment.url
    return None

def count_image_attachment(attachments):
    ret = 0
    for attachment in attachments:
        ctype = attachment.content_type
        if ctype.split('/')[0] == 'image':
            ret += 1
    return ret

class Screenshot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def on_load(self):
        self.once_a_month.start()

    async def on_unload(self):
        self.once_a_month.cancel()

    async def process_reactions_last_month(self, channel, nowutc):
        end_time = nowutc.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start_time = (end_time - datetime.timedelta(days=3)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        year_month_name = start_time.strftime("%Y-%B")
        winner_name = f'winners/{year_month_name}.txt'
        if os.path.isfile(winner_name):
            print(f'{winner_name} exists, bailing')
            return

        print(f'Scanning from {start_time} to {end_time}')
        top_message = None
        top_reaction_count = 0
        num_messages = 0
        num_reactions = 0
        num_images = 0
        async for message in channel.history(limit=None, after=start_time, before=end_time):
            if message.author.id == self.bot.user.id:
                continue
            num_messages += 1
            image_count = count_image_attachment(message.attachments)
            if not image_count:
                continue
            num_images += image_count
            message_reactions = 0
            for x in message.reactions:
                num_reactions += x.count
                message_reactions += x.count
                # if not is_voyager_emoji(x.emoji):
                #     continue
            if message_reactions > top_reaction_count:
                top_message = message
                top_reaction_count = message_reactions
        print(f'Done scanning. Winner: {top_message}')
        if not top_message:
            return

        with open(f'winners/{year_month_name}.txt', 'w') as f:
            f.write(top_message.jump_url)

        month_name = start_time.strftime("%B")
        url = get_first_image(top_message.attachments)
        embed = discord.Embed(title=f'Winning screenshot of {month_name}', description=f'This past month we saw {num_messages} messages, {num_images} images and {num_reactions} reactions in this channel. This image got the most reactions! Congrats to <@{top_message.author.id}>', color=VOYAGER_GREEN, url=top_message.jump_url)
        embed.set_image(url=url)
        embed.set_footer(text='ButterBot (c) Voyager Aviation', icon_url='https://flyvoyager.net/logov.png')
        #embed.set_author(name='ScreenshotBot', url='https://flyvoyager.net/pictures.html', icon_url='https://flyvoyager.net/logov.png')
        #await client.get_channel(_BOT_TEST_ID).send(embed=embed)
        await channel.send(embed=embed)

    @tasks.loop(hours=1)
    async def once_a_month(self):
        nowutc = datetime.datetime.now(tz=datetime.timezone.utc)
        channel = self.bot.get_channel(_SCREENSHOT_ID)
        if not channel:
            channel = self.bot.get_channel(_EMERGENCY_SERVER_SCREENSHOT_ID)
        await self.process_reactions_last_month(channel, nowutc)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, reaction):
        channel = await self.bot.fetch_channel(reaction.channel_id)
        message = await channel.fetch_message(reaction.message_id)
        user = await self.bot.fetch_user(reaction.user_id)
        if channel.id not in [_SCREENSHOT_ID, _BOT_TEST_ID, _EMERGENCY_SERVER_SCREENSHOT_ID]:
            return
        if user.id not in _ALLOWED_USERS:
            return
        if len(message.attachments) <= 0:
            return
        if not is_voyager_emoji(reaction.emoji):
            return
        for attachment in message.attachments:
            ctype = attachment.content_type
            if ctype.split('/')[0] != 'image':
                continue
            url = attachment.url
            x  = url.split('/')[-1].split('?')[0]
            print(f'Saving {attachment.url} to {os.path.join(_IMAGE_DIR, x)}')
            if channel.id in [_SCREENSHOT_ID, _EMERGENCY_SERVER_SCREENSHOT_ID]:
                await attachment.save(os.path.join(_IMAGE_DIR, x))
            else:
                print('or not')
        genimagejson()

async def setup(bot):
    cog = Screenshot(bot)
    await bot.add_cog(cog)
    await cog.on_load()

async def teardown(bot):
    cog = bot.get_cog('Screenshot')
    cog.on_unload()
    await bot.remove_cog('Screenshot')
