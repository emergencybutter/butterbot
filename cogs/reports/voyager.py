import discord
import random
import datetime
import dateutil.relativedelta

VOYAGER_GREEN = discord.Color.from_str("#3EA2AA")
VOYAGER_ORANGE = discord.Color.from_str("#F05A28")
YELLOW = discord.Color.from_str("#ffff00")
BLACK = discord.Color.from_str("#000000")


BOT_TEST_ID = 1285386906451972096
BOT_ID = 1287483856446033920
VOY_EMOJI = 1064727097421090817
PAPERPLANE_EMOJI = 1368584175980122253
SCREENSHOT_ID = 1056720051111219253 
FLIGHT_REPORTS_ID = 1059611234535747705
VYA_AIRLINE = 2639


def link_to_airport(x: str):
    return f'[{x}](https://skyvector.com/airport/{x})'

def fshub_time_to_datetime(x: str):
    return datetime.datetime.fromisoformat(x)

def fshub_time_to_human(x: str):
    return fshub_time_to_datetime(x).strftime('%H%Mz')

def fshub_time_to_timestamp(x: str):
    return int(fshub_time_to_datetime(x).timestamp())


def set_footer(embed):
    embed.set_footer(text='ButterBot © Voyager Aviation', icon_url='https://flyvoyager.net/logov.png')

def set_footer_orange(embed):
    embed.set_footer(text='ButterBot © Voyager Aviation', icon_url='https://flyvoyager.net/paperairplaneorange.png')

def set_bot_author(embed):
    embed.set_author(name="ButterBot", url='https://flyvoyager.net', icon_url='https://flyvoyager.net/paperairplaneorange.png')

def user_to_author(embed, userjson):
    if not userjson:
        return
    if 'user' in userjson:
        userjson = userjson['user']
    name = userjson['name']
    avatar = None
    if 'profile' in userjson and 'avatar_url' in userjson['profile']:
        avatar = userjson['profile']['avatar_url']
    embed.set_author(name=name, url='https://flyvoyager.net', icon_url=avatar)

def process_aircraft(embed, data):
    aircraft = data['aircraft']
    icao = aircraft['icao']
    icao_name = aircraft['icao_name']
    livery = aircraft['name']
    tail = aircraft['user_conf']['tail']
    ret = []
    if tail:
        ret.append( f'Tail: {tail}')
    ret.append(f'{icao_name} ({icao})')
    ret.append(f'{livery}')
    embed.add_field(name='Aircraft', value='\n'.join(ret), inline=True)

class Airport():
    def __init__(self, data):
        self.name, self.icao, self.time = data['name'], data['icao'], data['time']
        self.data = data

    def human_time(self):
        return f'<t:{self.timestamp()}> ({fshub_time_to_human(self.time)})'

    def datetime(self):
        return fshub_time_to_datetime(self.time)

    def timestamp(self):
        return fshub_time_to_timestamp(self.time)

    def md_link(self):
        return link_to_airport(self.icao)


def process_airport(data):
    if not data:
        return None
    if 'name' in data and 'icao' in data and 'time' in data:
        return Airport(data)
    return None

def process_flight(data):
    departure = process_airport(data['departure'])
    arrival = process_airport(data['arrival'])
    ret = []
    if departure:
        ret.append(f'Departure: {departure.name} ({departure.md_link()}) at {departure.human_time()}')
    if arrival:
        ret.append(f'Arrival: {arrival.name} ({arrival.md_link()}) at {arrival.human_time()}')
    return '\n'.join(ret)

def process_timestamp_datetime(data):
    departure = process_airport(data['departure'])
    arrival = process_airport(data['arrival'])
    if arrival:
        return arrival.datetime()
    if departure:
        return departure.datetime()
    return None

def process_stats(embed, data):
    departure = process_airport(data['departure'])
    arrival = process_airport(data['arrival'])
    duration = None
    if departure and arrival:
        duration = str(arrival.datetime() - departure.datetime())
    ret = []
    ret.append(f"Distance: {data['distance']['nm']} nm")
    if duration:
        ret.append(f"Duration: {duration}")
    if data['fuel_used']:
        ret.append(f"Fuel Burnt: {data['fuel_used']} kg")
    if data['max']:
        max = data['max']
        ret.append(f"Max altitude: {max['alt']} ft")
        ret.append(f"Max speed: {max['spd']} kts")
    if data['average']:
        avg = data['average']
        ret.append(f"Average speed: {avg['spd']} kts")
    embed.add_field(name='Flight Stats', value='\n'.join(ret), inline=True)
    ret = []
    ret.append(f"Landing rate: {data['landing_rate']} fpm")
    ret.append(f"Pitch: {arrival.data['pitch']}")
    ret.append(f"Bank: {arrival.data['bank']}")
    ret.append(f"Speed (TAS): {arrival.data['spd']['tas']} kts")
    ret.append(f"Wind: {arrival.data['wind']['dir']}° {arrival.data['wind']['spd']} kts")
    embed.add_field(name='Landing Stats', value='\n'.join(ret), inline=True)

def process_flags(embed, data):
    if data['flags']:
        flags = data['flags']
        embed.add_field(name='Flags', value='\n'.join(flags), inline=True)


def process_achievement(embed, requestjson):
    if '_data' in requestjson:
        achievement = requestjson['_data']['achievement']
        achievement_title = achievement['title']
        achievement_url = f'https://fshub.io/achievement/{achievement["slug"]}/overview'
        descr = f'[{achievement_title}]({achievement_url})'
        embed.add_field(name='Achievement completed!', value=descr)
    else:
        achievement_url = requestjson['overview_url']
        achievement_title = requestjson['title']
        descr = f'[{achievement_title}]({achievement_url})'
        embed.add_field(name='Achievement completed!', value=descr)
        embed.set_thumbnail(url=requestjson['emblem_url'])

def make_flight_embed(id_, title, data, shots_data, ach_data, user_data):
    flight = process_flight(data)
    url = None
    if id_:
        url = f'https://fshub.io/flight/{id_}/report'
    color = VOYAGER_ORANGE
    if ach_data:
        color = VOYAGER_GREEN
    ts = process_timestamp_datetime(data)
    embed = discord.Embed(title=title, description=flight, color=color, url=url, timestamp=ts)
    if shots_data:
        rando = shots_data[0]
        embed.set_image(url=rando['urls']['fullsize'])
    user_to_author(embed, user_data)
    process_aircraft(embed, data)
    process_stats(embed, data)
    process_flags(embed, data)
    if ach_data:
        process_achievement(embed, ach_data)
        set_footer(embed)
    else:
        set_footer_orange(embed)
    return embed

def stats_to_embed(stats: dict, milestone:bool):
    url = "https://flyvoyager.net/"
    flights = stats['data']['all_time']['total_flights']
    if milestone:
        embed = discord.Embed(title="Voyager Aviation Statistics", description=f"Voyager has just reached a milestone of {flights} flights. Keep up the good work aviators.", color=YELLOW, url=url)
    else:
        embed = discord.Embed(title="Voyager Aviation Statistics", description=f"I am a bot and I like to count flights. Voyager Aviation reached {flights} flights. Keep up the good work aviators.", color=BLACK, url=url)
    set_bot_author(embed)
    for xi in ['month', 'all_time']:
        x = stats['data'][xi]
        data = []
        data.append(f'Flights: {x["total_flights"]}')
        data.append(f'Hours: {x["total_hours"]} h')
        data.append(f'Distance: {x["total_distance"]} nm')
        if xi == 'month':
            name = 'This month'
        else:
            name = 'All time'
        embed.add_field(name=name, value='\n'.join(data), inline=True)
    set_footer_orange(embed)
    return embed