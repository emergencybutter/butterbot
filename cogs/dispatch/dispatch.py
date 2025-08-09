from discord.ext import commands
import discord
import cogs.dispatch.aircraft_lib as aircraft_lib
import cogs.dispatch.picker as picker
import cogs.dispatch.vatsimatc as vatsimatc
import re

_EMSERVER_DISPATCH_CHAN_ID = 1350203146558771261
_EMSERVER_DEBUG_CHAN_ID = 1350215563787374760

class Dispatch(commands.Cog):
    def __init__(self, bot, airports: picker.Airports, aircrafts: aircraft_lib.Aircrafts):
        self.bot = bot
        self.airports = airports
        self.aircrafts = aircrafts

    def choose(self, args, ch_name):
        vatsim = False
        ap_prefs = picker.AirportPreferences()
        nargs = []
        for arg in args:
            if arg == "vatsim":
                vatsim = True
            elif arg in {'AF', 'AN', 'SA', 'NA', 'AS', 'OC', 'EU'}:
                ap_prefs.continents.add(arg)
            elif arg in {'small', 'medium', 'large'}:
                ap_prefs.types.add(f'{arg}_airport')
            else:
                nargs.append(arg)
        args = nargs
        if vatsim:
            app = picker.AirportPairPickerVatsim(self.airports, self.aircrafts)
        else:
            app = picker.AirportPairPicker(self.airports, self.aircrafts)
        if len(args) >= 1:
            error = app.set_aircraft_type(args[0].upper())
            if error:
                return f"I do not know this aircraft type: {args[0].upper()}.", None
        duration_h = 1.0
        if len(args) >= 2:
            m = re.match(r"([0-9.]+)h", args[1], re.IGNORECASE)
            if not m:
                return f"Usage: Cannot parse duration {args[1]}. It should look like 1.5h", None
            duration_h = float(m[1])

        (
            airport1,
            airport2,
            debugdict,
        ) = app.pick_pair(hours=duration_h, ap_prefs=ap_prefs)
        if airport1 is None or airport2 is None:
            return "Cannot find suitable airports, sorry", None
        pretty_distance = "{0:0.2f}".format(airport2.distance(airport1))
        pretty_aircraft = self.aircrafts.get(app.aircraft_type).Model_FAA
        simbrief_url = f"https://dispatch.simbrief.com/options/custom?airline=VYA&type={app.aircraft_type}&orig={airport1.code}&dest={airport2.code}&manualrmk=Callsign%20Voyager%20-%20visit%20flyvoyager.net"
        resp = f"Fly the {pretty_aircraft} from {airport1.code} to {airport2.code} ({pretty_distance}nm). [File in Simbrief]({simbrief_url})."

        print(f'{debugdict}')
        
        emdbg = discord.Embed(
            title="dispatch bot log log",
            description=f'debug for command in channel {ch_name}: !dispatch {" ".join(args)}',
        )
        for k, v in debugdict.items():
            emdbg.add_field(name=k, value=v)
        return resp, emdbg

    @commands.command()
    @commands.check(commands.is_owner())
    async def dispatch_admin(self, ctx, *args):
        ctx.send("you be admin")

    @commands.command()
    async def dispatch(self, ctx, *args):
        if len(args) >= 1 and args[0] == "help":
            await ctx.send(
                f"Usage, in #dispatch: !dispatch [icao type] [duration] [network] [continent]\n" +
                f"Returns two small to medium airports that could be flown in " +
                f"approximately [duration] hours. Duration defaults to 1h, icao " +
                f"type to the SF50, and no network. You can specify a continent by adding on of 'AF', 'AS', 'SA', 'OC', 'NA', 'AN', 'EU'."
            )
            return
        
        if not ctx.channel.id in (1347570976677822474, 1285386906451972096, _EMSERVER_DISPATCH_CHAN_ID):
            return
        resp, emdbg = self.choose(args, ctx.channel.name)
        await ctx.send(resp)
        if emdbg:
            debugchannel = self.bot.get_channel(_EMSERVER_DEBUG_CHAN_ID)
            if debugchannel:
                await debugchannel.send(embed=emdbg)


async def setup(bot):
    aircrafts = aircraft_lib.Aircrafts()
    aircrafts.load_database()
    airports = picker.Airports()
    airports.load()
    await bot.add_cog(Dispatch(bot, airports, aircrafts))

async def teardown(bot):
    await bot.remove_cog('Dispatch')
