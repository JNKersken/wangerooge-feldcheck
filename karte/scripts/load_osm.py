"""Parse map.osm into python structures (nodes, ways, relations) with tags + geometry."""
import xml.etree.ElementTree as ET, json, sys, pickle
src = sys.argv[1]; out = sys.argv[2]
root = ET.parse(src).getroot()
nodes, ways, rels = {}, {}, {}
for el in root:
    if el.tag == 'node':
        nodes[int(el.get('id'))] = dict(lat=float(el.get('lat')), lon=float(el.get('lon')),
            tags={t.get('k'): t.get('v') for t in el.findall('tag')},
            ts=el.get('timestamp'), user=el.get('user'), ver=int(el.get('version')))
    elif el.tag == 'way':
        ways[int(el.get('id'))] = dict(nds=[int(n.get('ref')) for n in el.findall('nd')],
            tags={t.get('k'): t.get('v') for t in el.findall('tag')}, ts=el.get('timestamp'), user=el.get('user'))
    elif el.tag == 'relation':
        rels[int(el.get('id'))] = dict(members=[(m.get('type'), int(m.get('ref')), m.get('role')) for m in el.findall('member')],
            tags={t.get('k'): t.get('v') for t in el.findall('tag')}, ts=el.get('timestamp'))
pickle.dump(dict(nodes=nodes, ways=ways, rels=rels), open(out, 'wb'))
print(len(nodes), len(ways), len(rels))
