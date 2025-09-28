from discord.ext import tasks, commands
import aiohttp
import re
import lib.fshub as fshub
import cogs.reports.voyager as voyager
import copy
import json
import os

_BOT_TEST_ID = 1285386906451972096
_DISPATCH = 1347570976677822474
_STATE_PATH = 'var/vatsim.json'

class Vatsim(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sent_msgs = set()
        self.fshub = fshub.FsHub()
        self.fshub.load_key()
        with open(_STATE_PATH) as f:
            self.vatsim_id_to_handles = json.loads(f.read())

    @commands.command()
    async def reload_user_ids(self, ctx, *args):
        async with aiohttp.ClientSession() as session:
            pilots = await self.fshub.get_airline_pilots(session, airline_id=voyager.VYA_AIRLINE)
            for p in pilots['data']:
                pilot = await self.fshub.get_pilot(session, p['id'])
                if pilot['data']['handles']['vatsim']:
                    vatsim_id = str(pilot['data']['handles']['vatsim'])
                    handles = {}
                    for k, v in pilot['data']['handles'].items():
                        if v:
                            handles[k] = v
                    if p['id']:
                        handles['fshub'] = p['id']
                    if p['discord_id']:
                        handles['discord'] = p['discord_id']
                    if handles:
                        self.vatsim_id_to_handles[vatsim_id] = handles
        with open(_STATE_PATH + '.tmp', 'w') as f:
            f.write(json.dumps(self.vatsim_id_to_handles))
        os.rename(_STATE_PATH + '.tmp', _STATE_PATH)


    async def send_once(self, s):
        #self.channel = self.bot.get_channel(_BOT_TEST_ID)
        self.channel = self.bot.get_channel(_DISPATCH)
        print(f'Adding msg {s}')
        if s not in self.sent_msgs:
            await self.channel.send(s)
            self.sent_msgs.add(s)

    async def process(self, session, js):
        for pilot in js['pilots']:
            cid, name, callsign = pilot['cid'], pilot['name'], pilot['callsign']
            fp = pilot['flight_plan']
            if not fp:
                continue
            rules, dep, arr, ac, rmk = fp['flight_rules'], fp['departure'], fp['arrival'], fp['aircraft_faa'], fp['remarks']
            if not re.match(r'VYA.*', callsign, re.IGNORECASE) and not re.match(r'.*\b(flyvoyager|voyager)\b.*', rmk, re.IGNORECASE):
                continue
            discord_id = self.vatsim_id_to_handles.get(str(cid), {}).get('discord', None)
            if discord_id:
                name += f' (<@{discord_id}>)'

            route = fp['route']
            if rules == 'I':
                fp_type = 'IFR' 
            else:
                fp_type = 'VFR'
            track_str = ''
            id_ = pilot['cid']
            link = f'https://vatsim-radar.com/?pilot={id_}'
            track_str = f'[Track flight]({link}).'
            await self.send_once(f'Voyager aviation has filed `{callsign}` for {name}. {fp_type} in a {ac} on Vatsim. [{dep}](https://fshub.io/airport/{dep}/overview) -> [{arr}](https://fshub.io/airport/{arr}/overview) route: `{route}`.' + track_str)


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

    @commands.command()
    async def flightplans(self, ctx, *args):
        await self.periodic()


async def setup(bot):
    v = Vatsim(bot)
    await bot.add_cog(v)
    await v.on_load()


async def teardown(bot):
    cog = bot.get_cog('Vatsim')
    await cog.on_unload()
    await bot.remove_cog('Vatsim')
