def jd(jd, *args):
    for arg in args:
        jd = jd.get(arg, {})
        if not jd:
            jd = {}
    if jd:
        return jd
    return ''

def dump_flight(flight):
    print(flight)
    user_name = jd(flight, 'user', 'name')
    aircraft_icao = jd(flight, 'aircraft', 'icao')
    aircraft_name = jd(flight, 'aircraft', 'name')
    departure_icao = jd(flight, 'departure', 'icao')
    departure_name = jd(flight, 'departure', 'name')
    arrival_icao = jd(flight, 'arrival', 'icao')
    arrival_name = jd(flight, 'arrival', 'name')
    ret = []
    ret.append('<tr>')
    ret.append(f'<td>{user_name}</td><td>{aircraft_icao}</td><td>{aircraft_name}</td><td>{departure_icao}</td><td>{departure_name}</td><td>{arrival_icao}</td><td>{arrival_name}</td>')
    ret.append('</tr>')
    return '\n'.join(ret)

def compile(flightarray):
    ret = []
    ret.append('<table>')
    ret.append('''<thead>
    <tr>
      <th>Pilot</th>
      <th></th>
      <th>Aircraft</th>
      <th></th>
      <th>Departure</th>
      <th></th>
      <th>Arrival</th>
    </tr>
  </thead>
 ''')
    ret.append('<tbody>')
    for flight in flightarray:
            ret.append(dump_flight(flight))
    ret.append('</tbody>')
    ret.append('</table>')
    return '\n'.join(ret)

def dump_to_file(path:str, flight_array):
    with open(path, 'w') as f:
        f.write(compile(flight_array))

