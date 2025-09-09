from discord.ext import tasks, commands
import aiohttp
import asyncio
import cogs.reports.table as table
import cogs.reports.voyager as voyager
import discord
import hashlib
import json
import lib.fshub as fshub
import math
import os

_EMERGENCY_SERVER_TEST_CHANEL = 1294385730830995487
_FLIGHT_BACKREAD = 10
_ACHIEVEMENT_REACTION = '✅'

class TrackState():
    def __init__(self, dev_mode:bool):
        self.state_path = 'var/reports-state.json'
        if dev_mode:
            self.state_path = 'var/dev-reports-state.json'

    def gc(self):
        to_gc = []
        for k in self.reports_stats['reports'].keys():
            if int(k) < self.reports_stats['last-bookmarked-flight']:
                to_gc.append(k)
        for k in to_gc:
            del self.reports_stats['reports'][k]

    def reload_reports_state(self):
        with open(self.state_path, 'r') as f:
            self.reports_stats = json.loads(f.read())

    def save_reports_state(self):
        self.gc()
        with open(self.state_path + '.tmp', 'w') as f:
            f.write(json.dumps(self.reports_stats))
        os.rename(self.state_path + '.tmp', self.state_path)

    def is_known_flight(self, fid:str) -> bool:
        return fid in self.reports_stats['reports'] and 'message_id' in self.reports_stats['reports'][fid]

    def init_fid(self, fid:str):
        if not 'reports' in self.reports_stats:
            self.reports_stats['reports'] = {}
        if not fid in self.reports_stats['reports']:
            self.reports_stats['reports'][fid] = {}

    def set_message_hash(self, fid:str, embed_hash):
        self.init_fid(fid)
        self.reports_stats['reports'][fid]['hash'] = embed_hash
        self.save_reports_state()

    def get_message_hash(self, fid:str) -> str:
        return self.reports_stats['reports'][fid]['hash']
    
    def get_discord_message_id(self, fid:str) -> int:
        return self.reports_stats['reports'][fid]['message_id']

    def set_discord_message_id(self, fid:str, message_id:int):
        self.init_fid(fid)
        self.reports_stats['reports'][fid]['message_id'] = message_id
        self.save_reports_state()

    def get_last_bookmarked_flight(self):
        return self.reports_stats['last-bookmarked-flight']

    def set_last_bookmarked_flight(self, fid:int):
        self.reports_stats['last-bookmarked-flight'] = fid
        self.save_reports_state()


class FlightReport(commands.Cog):
    def __init__(self, bot):
        self.dev_mode = bot.vya_dev_mode
        self.bot = bot
        self.tick = 0
        self.state = TrackState(self.dev_mode)
        self.state.reload_reports_state()
        self.lock = asyncio.Lock()
        self.channel = None

    async def on_load(self):
        if not self.channel:
            self.channel = self.bot.get_channel(voyager.FLIGHT_REPORTS_ID)
            if self.dev_mode:
                self.channel = self.bot.get_channel(_EMERGENCY_SERVER_TEST_CHANEL)
        if not self.channel:
            raise Exception('no channel configured')

        self.state.reload_reports_state()
        self.fshub = fshub.FsHub()
        self.fshub.load_key()
        self.periodic.start()
        self.stats_refresh.start()


    async def on_unload(self):
        self.state.save_reports_state()
        self.stats_refresh.cancel()
        self.periodic.cancel()
        self.injest_wehooks.cancel()

    async def sync_to_discord(self, ctx, fid:str, embed, is_achievement:bool):
        embed_hash = str(hashlib.sha256(json.dumps(embed.to_dict()).encode('utf-8')).hexdigest())
        if self.state.is_known_flight(fid):
            message_hash = self.state.get_message_hash(fid)
            if message_hash == embed_hash:
                print(f'message {message_hash} was unchanged')
                return
            print(f'updating message {message_hash}.')
            message_id = self.state.get_discord_message_id(fid)
            try:
                msg = await ctx.fetch_message(message_id)
                await msg.edit(embed=embed)
                if is_achievement:
                    await msg.add_reaction(_ACHIEVEMENT_REACTION)
                self.state.set_message_hash(fid, embed_hash)
            except discord.errors.NotFound as f:
                print(f)
        else:
            message = await ctx.send(embed=embed)
            if is_achievement:
                await message.add_reaction(_ACHIEVEMENT_REACTION)
            print(f'saving {fid} {message.id}')
            self.state.set_discord_message_id(fid, message.id)
            self.state.set_message_hash(fid, embed_hash)
        self.state.save_reports_state()

    async def sync_from_fshub(self, ctx):
        print('detected flight')
        async with self.lock:
            async with aiohttp.ClientSession() as session:
                flights = await self.fshub.get_airline_flights_from(session, airline=voyager.VYA_AIRLINE, cursor=self.state.get_last_bookmarked_flight())
                if len(flights) >= _FLIGHT_BACKREAD:
                    self.state.set_last_bookmarked_flight(int(flights[-_FLIGHT_BACKREAD]['id']))
                table.dump_to_file('/var/www/html/data/flights-table.html', flights)
                for flight in flights:
                    fid = str(flight['id'])
                    pilot_data = await self.fshub.get_pilot(session, voyager.VYA_AIRLINE, flight['user']['id'])
                    if pilot_data is not None:
                        pilot_data = pilot_data['data']
                    achievement_data = None
                    achievements_data = await self.fshub.get_achievement(session, voyager.VYA_AIRLINE, fid)
                    if achievements_data:
                        for achievement in achievements_data['data']:
                            if achievement['airline_id'] == voyager.VYA_AIRLINE:
                                if achievement_data:
                                    print(f"Multiple VYA achievements for flight {fid}")
                                achievement_data = achievement
                    shots_data = None
                    if 'SCREENSHOTS' in flight['flags']:
                        shots_data = await self.fshub.get_flight_screenshots(session, fid)
                        print(f'shots_data: {shots_data}')
                        if shots_data:
                            shots_data = shots_data['data']
                        else:
                            print(f'Flight {flight} should have shots data')
                    embed = voyager.make_flight_embed(fid, f'Flight #{fid}', flight, shots_data, achievement_data, pilot_data)
                    await self.sync_to_discord(ctx, fid, embed, achievement_data is not None)

    @tasks.loop(seconds=3*60)
    async def periodic(self):
        print('Running periodic')
        await self.sync_from_fshub(self.channel)

    @tasks.loop(seconds=60)
    async def stats_refresh(self):
        root = '/var/www/html/data/'
        if self.dev_mode:
            root = 'var/dev/'
        async with aiohttp.ClientSession() as session:
            stats = await self.fshub.get_airline_stats(session, voyager.VYA_AIRLINE)
        path = root + 'voy-stats.json'
        with open(path + '.tmp', 'w') as tmp:
            tmp.write(json.dumps(stats))
        if os.path.isfile(path):
            os.rename(path, path + '.old')
        os.rename(path + '.tmp', path)
        if not os.path.isfile(root + 'voy-stats.json.old'):
            return
        with open(root + 'voy-stats.json.old', 'r') as f:
            oldstats = json.loads(f.read())
        new_flights = int(stats['data']['all_time']['total_flights'])
        old_flights = int(oldstats['data']['all_time']['total_flights'])
        print(f'new: {new_flights} old: {old_flights}')
        if new_flights != old_flights:
            await self.sync_from_fshub(self.channel)
        old_hundreds = math.floor(old_flights/100)
        new_hundreds = math.floor(new_flights/100)
        if old_hundreds != new_hundreds:
            embed = voyager.stats_to_embed(stats, True)
            message = await self.channel.send(embed=embed)
            await message.add_reaction(_ACHIEVEMENT_REACTION)

    @commands.command()
    async def stats(self, ctx, *args):
        async with aiohttp.ClientSession() as session:
            stats = await self.fshub.get_airline_stats(session, voyager.VYA_AIRLINE)
            embed = voyager.stats_to_embed(stats, False)
            await ctx.send(embed=embed)

    @commands.command()
    async def report(self, ctx, *args):
        #if len(args):
        #    self.state.set_last_bookmarked_flight(int(args[0]))
        await self.periodic()

async def setup(bot):
    cog = FlightReport(bot)
    await bot.add_cog(cog)
    await cog.on_load()

async def teardown(bot):
    cog = bot.get_cog('FlightReport')
    await cog.on_unload()
    await bot.remove_cog('FlightReport')
