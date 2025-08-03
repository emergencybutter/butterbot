#!/bin/python3

import os
import requests
import codecs
import json
import aiohttp
import asyncio

class UnhandledStatusException(Exception):
    pass

class FsHub():
    def __init__(self):
        pass

    def load_key(self):
        with open('fshub.token.txt') as key:
           self._api_key = key.readline().rstrip()

    async def get_json(self, session, path):
        headers = {'X-Pilot-Token': self._api_key}
        retrying = True
        print('https://fshub.io/api' + path)
        while retrying:
            retrying = False
            async with session.get('https://fshub.io/api' + path, headers=headers) as r:
                if r.status == 200:
                    js = await r.json()
                    return js
                if r.status == 404:
                    return None
                print(r)
                print(r.status)
                if r.status == 500:
                    print(f'Got 500, retrying in 60s. {r}')
                    await asyncio.sleep(60)
                    retrying = True
                else:
                    raise UnhandledStatusException(r)

    async def get_airline_flights(self, session, airline, cursor, limit=100):
        return await self.get_json(session, f'/v3/airline/{airline}/flight?cursor={cursor}&limit={limit}')

    async def get_airline_flights_from(self, session, airline, cursor=0):
        ret = []
        while True:
            flights = await self.get_airline_flights(session, airline, cursor)
            if not flights or 'data' not in flights or not flights['data']:
                return ret
            for x in flights['data']:
                ret.append(x)
            cursor = flights['meta']['cursor']['next']

    async def get_flight(self, session, flightid):
        return await self.get_json(session, f'/v3/flight/{flightid}')

    async def get_flight_screenshots(self, session, flightid):
        return await self.get_json(session, f'/v3/flight/{flightid}/screenshot')

    async def get_achievement(self, session, va, flightid):
        return await self.get_json(session, f'/v3/flight/{flightid}/achievement')


    async def get_pilot(self, session, airline, pilotid):
        return await self.get_json(session, f'/v3/airline/{airline}/pilot/{pilotid}/stats')
    
    async def get_airline_stats(self, session, airline_id):
        return await self.get_json(session, f'/v3/airline/{airline_id}/stats')


if __name__ == '__main__':
    async def main():
        fshub = FsHub()
        fshub.load_key()
        AIRLINE=2639
        async with aiohttp.ClientSession() as session:
            flights = await fshub.get_airline_flights_from(session, airline=AIRLINE, cursor=3862478)
        print(flights)
    asyncio.run(main())
