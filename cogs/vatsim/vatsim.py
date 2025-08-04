from discord.ext import tasks, commands
import aiohttp
import re

_BOT_TEST_ID = 1285386906451972096
_DISPATCH = 1347570976677822474

class Vatsim(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sent_msgs = set()

    async def send_once(self, s):
        #self.channel = self.bot.get_channel(_BOT_TEST_ID)
        self.channel = self.bot.get_channel(_DISPATCH)
        print(f'Adding msg {s}')
        if s not in self.sent_msgs:
            await self.channel.send(s)
            self.sent_msgs.add(s)

    async def process(self, session, js):
        for pilot in js['pilots']:
            name, callsign = pilot['name'], pilot['callsign']
            if not re.match(r'VYA.*', callsign, re.IGNORECASE):
                continue
            fp = pilot['flight_plan']
            if not fp:
                continue
            rules, dep, arr, ac = fp['flight_rules'], fp['departure'], fp['arrival'], fp['aircraft_faa']
            route = fp['route']
            if rules == 'I':
                fp_type = 'IFR' 
            else:
                fp_type = 'VFR'
            track_str = ''
            id_ = pilot['cid']
            link = f'https://vatsim-radar.com/?pilot={id_}'
            track_str = f'[Track flight]({link}).'
            await self.send_once(f'Voyager aviation has filed `{callsign}` {fp_type} in a {ac} on Vatsim. [{dep}](https://fshub.io/airport/{dep}/overview) -> [{arr}](https://fshub.io/airport/{arr}/overview) route: `{route}`.' + track_str)


    @tasks.loop(minutes=5)
    async def periodic(self):
        async with aiohttp.ClientSession() as session:
            async with session.get('https://data.vatsim.net/v3/vatsim-data.json') as r:
                if r.status == 200:
                    js = await r.json()
                    await self.process(session, js)


    async def on_load(self):
        self.periodic.start()

    async def on_unload(self):
        self.periodic.cancel()


async def setup(bot):
    v = Vatsim(bot)
    await bot.add_cog(v)
    await v.on_load()


async def teardown(bot):
    cog = bot.get_cog('Vatsim')
    await cog.on_unload()
    await bot.remove_cog('Vatsim')
