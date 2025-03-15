import collections

airports_to_FIR = {}
FIR_to_callsigns = collections.defaultdict(set)
with open('VATSpy.dat', 'r') as f:
    airports = False
    firs = False
    for line in f.readlines():
        if line.startswith(';'):
            continue
        l = line.rstrip()
        if l == '' or l.startswith('['):
            airports = False
            firs = False
        if airports:
            s = l.split('|')
            airports_to_FIR[s[0]] = s[5]
        if firs:
            s = l.split('|')
            if s[2]:
                FIR_to_callsigns[s[0]].add(s[2])
            if s[3]:
                FIR_to_callsigns[s[0]].add(s[3])
        if l == '[Airports]':
            airports = True
        if l == '[FIRs]':
            firs = True

for ap in airports_to_FIR:
    fir = airports_to_FIR[ap]
    cs = '|'.join(FIR_to_callsigns[fir])
    if cs:
        print(f'{ap},{cs}')
