"""Plain-language texts for the field-check app: what the object is, what to look for, where it is, why it needs checking.
Turns OSM tags and analysis notes (e.g. 'fire_hydrant:type=underground', 'Ø 16.0 m, Tiefe 0.95 m, Form deutlich') into sentences."""
import math, re

def _tags(notiz):
    return dict(kv.split('=', 1) for kv in re.split(r',\s*', notiz or '') if '=' in kv)

def _num(s, pat):
    m = re.search(pat, s or ''); return float(m.group(1).replace(',', '.')) if m else None

def _m(x):
    return f'{x:.0f}' if x >= 3 else f'{x:.1f}'.replace('.', ',')

RECYC = {'glass_bottles': 'Glas', 'glass': 'Glas', 'paper': 'Papier', 'clothes': 'Altkleider', 'cans': 'Dosen', 'plastic': 'Plastik', 'waste': 'Restmüll'}
SPORT = {'tennis': 'Tennis', 'multi': 'Mehrzweck', 'soccer': 'Fußball', 'basketball': 'Basketball', 'handball': 'Handball'}
FELD = {'rzsign': ('Ruhezonen-Schild', 'Schild „Ruhezone“ des Nationalparks.'), 'rzpost': ('Ruhezonen-Pfahl', 'Markierungspfahl der Ruhezone.'),
        'beachaccess': ('Strandaufgang', 'Strandaufgang bzw. Dünenübergang, oft mit Nummer.'), 'boulder': ('Findling / Stein', 'Einzelner großer Stein.'),
        'post': ('Pfahl / Pfosten', 'Einzelner Pfahl oder Pfosten.'), 'flagpole': ('Fahnenmast', 'Fahnenmast.'), 'sign': ('Schild', 'Schild.'),
        'pond': ('Tümpel', 'Kleine Wasserfläche oder feuchte Senke.'), 'steeppt': ('Steilhang / Abbruch', 'Steile Abbruchkante im Gelände.'),
        'sandfence': ('Sandfangzaun', 'Zaun aus Pfählen oder Reisig, der Sand fängt.'), 'boardwalk': ('Holzsteg', 'Steg oder Bohlenweg aus Holz.'), 'dot': ('Landmarke', '')}

def title_hint(p):
    """(title, what to look for)"""
    k, t, nm, no = p['kategorie'], p['typ'] or '', (p['name'] or '').strip(), p.get('notiz') or ''
    tg = _tags(no)
    if k == 'Bank':
        lehne = {'yes': ' mit Lehne', 'no': ' ohne Lehne'}.get(tg.get('backrest'), '')
        mat = {'wood': 'Holz', 'plastic': 'Kunststoff', 'metal': 'Metall', 'stone': 'Stein'}.get(tg.get('material'))
        return 'Bank' + lehne, f"Sitzbank{lehne}{' aus ' + mat if mat else ''}. Prüfe, ob sie hier steht."
    if k == 'Trichter':
        d, z = _num(no, r'Ø (?:ca\. )?([\d.,]+) m'), _num(no, r'Tiefe ([\d.,]+) m')
        size = (f'etwa {_m(d)} m breit' if d else '') + (f' und {_m(z)} m tief' if z else '')
        return 'Grube / Bombentrichter', f"Runde Mulde im Gelände{', ' + size if size else ''}, oft mit Gras oder Büschen bewachsen. Prüfe, ob die Mulde da ist und ungefähr hier liegt."
    if k == 'Rettungspunkt':
        return (f'SOS-Schild Nr. {nm}' if nm else 'SOS-Schild'), f"Rettungspunkt-Schild{' mit der Nummer ' + nm if nm else ''}, meist an einem Pfahl am Weg, Dünenübergang oder Strandaufgang. Prüfe Nummer und Standort."
    if k == 'Hydrant':
        return 'Unterflurhydrant' + (f' {nm}' if nm else ''), 'Hinweisschild (weiß mit rotem Rand und „H“) an Pfahl oder Wand; der Hydrant selbst ist ein Deckel im Boden. Prüfe, ob Schild oder Deckel da sind.'
    if k == 'Kleinobjekt':
        if t == 'Infotafel': return ('Infotafel „' + nm + '“' if nm else 'Infotafel'), 'Info- oder Schautafel am Weg. Prüfe, ob sie hier steht.'
        if t == 'firepit': return 'Feuerstelle', 'Feuer- oder Grillstelle (Steinring, Grillrost). Prüfe, ob sie da ist.'
        if t == 'picnic_site': return 'Picknickplatz', 'Tisch mit Bänken. Prüfe, ob er hier steht.'
        if t == 'monitoring_station': return 'Messstation' + (f' „{nm}“' if nm else ''), 'Pegel oder Messeinrichtung (Mast, Kasten oder Messlatte am Wasser).'
    if k == 'Gewässer':
        d = _num(no, r'Ø≈([\d.,]+) m')
        return 'Tümpel / Wasserloch', f"Kleine Wasserfläche oder feuchte Senke{', etwa ' + _m(d) + ' m groß' if d else ''}. Kann im Sommer trocken sein – dann zählt die Senke."
    if k == 'Durchgang':
        return {'gate': ('Tor / Gatter', 'Tor oder Gatter in einem Zaun oder quer über den Weg. Prüfe, ob es da ist.'),
                'coupure': ('Deichscharte', 'Durchfahrt durch den Deich, die bei Sturmflut mit Toren oder Balken verschlossen wird.'),
                'cycle_barrier': ('Umlaufsperre', 'Versetzte Metallbügel quer über den Weg („Drängelgitter“).'),
                'lift_gate': ('Schranke', 'Schlagbaum quer über den Weg.'),
                'bollard': ('Poller', 'Pfosten mitten im Weg, der Autos sperrt.')}.get(t, ('Tor / Durchlass', 'Tor oder Durchlass am Weg.'))
    if k == 'Einrichtung':
        if t == 'life_ring': return 'Rettungsring', 'Rettungsring an einem Pfahl oder Gestell, meist nahe am Wasser.'
        if t == 'lifeguard': return 'Rettungsschwimmer-Station', 'Turm oder Hütte der Rettungsschwimmer am Strand (evtl. nur im Sommer aufgebaut).'
        if t == 'toilets': return 'WC', 'Öffentliche Toilette – Toilettenhäuschen oder WC im Gebäude.'
    if k == 'Gastronomie':
        art = {'cafe': 'Café', 'restaurant': 'Restaurant'}.get(t, 'Gastronomie')
        return (nm or art), f"{art}{' „' + nm + '“' if nm else ''}. Prüfe, ob es hier ist und noch betrieben wird."
    if k == 'Bauwerk' and t == 'Schutzhütte': return 'Schutzhütte', 'Unterstand bzw. Wetterschutzhütte mit Dach.'
    if k == 'Historisch' and t == 'war_memorial': return (nm or 'Gedenkstätte'), 'Gedenkstein, Kreuz oder Gedenktafel.'
    if k == 'km-Stein': return (f'km-Stein {nm}' if nm else 'km-Stein'), f"Kleiner Stein oder Schild{' mit „' + nm + '“' if nm else ''} direkt neben dem Gleis der Inselbahn."
    if k == 'Recycling':
        was = RECYC.get(no.strip())
        return (f'Container für {was}' if was else 'Wertstoff-Container'), f"Wertstoff-Container{' für ' + was if was else ''}. Prüfe, ob er hier steht."
    if k == 'Fahrradständer':
        n = no.strip()
        return 'Fahrradständer', f"Fahrradständer{' für etwa ' + n + ' Räder' if n.isdigit() else ''}."
    if k == 'Fitness': return 'Fitnessgerät', 'Outdoor-Trainingsgerät am Weg.'
    if k == 'Umspannstation': return 'Trafostation', 'Kleines Gebäude oder Kasten mit Blitz-Warnschild (Strom).'
    if k == 'Feldobjekt':
        tt, h = FELD.get(t, ('Landmarke', '')); return (nm if nm and nm != tt else tt), h
    if k == 'Kuppe': return (f'Dünenkuppe {nm} m' if nm else 'Dünenkuppe'), 'Höchster Punkt einer Düne.'
    if k == 'Steilhang': return 'Steilhang', 'Steile Abbruchkante an einer Düne.'
    if k == 'Busch': return 'Markanter Busch', 'Einzelner, auffälliger Busch.'
    if k == 'Baum': return 'Einzelbaum', 'Einzeln stehender Baum.'
    if k == 'Buhne': return (f'Buhne {nm}' if nm else 'Buhne'), 'Buhne am Strand; der Punkt ist ihr landseitiges Ende.'
    if k == 'Dünenübergang': return 'Dünenübergang' + (' (Treppe)' if t == 'Treppe' else ''), 'Weg oder Treppe über die Düne zum Strand.'
    if k == 'Bahnübergang': return 'Bahnübergang', 'Weg kreuzt das Gleis der Inselbahn.'
    if k == 'Haltepunkt': return (f'Haltepunkt {nm}' if nm else 'Haltepunkt'), 'Haltestelle der Inselbahn.'
    if k == 'Brücke': return ('Durchlass' if t == 'Durchlass' else 'Brücke' + (f' ({nm})' if nm else '')), ''
    if k == 'Spielplatz': return 'Spielplatz', ''
    if k == 'Sportplatz':
        art = ' / '.join(SPORT.get(s, s) for s in t.split(';'))
        return f'Sportplatz ({art})' if art else 'Sportplatz', ''
    if k == 'Vegetation': return 'Wäldchen', 'Kleine Baumgruppe.'
    if k in ('Unterkunft', 'Gebäude', 'Bauwerk', 'Historisch', 'Einrichtung', 'Gelände'):
        return (nm.replace(' - ', ' – ') or {'Unterkunft': 'Unterkunft', 'Gebäude': 'Gebäude', 'Bauwerk': 'Bauwerk', 'Historisch': 'Gedenkort', 'Einrichtung': 'Einrichtung', 'Gelände': 'Düne'}[k]), ''
    return (nm or t or k), ''

def why(p):
    """Why the object still needs a look (empty for objects that are already certain)."""
    if p['status'] == 'sicher': return ''
    q, no = p.get('quellen') or '', p.get('notiz') or ''
    bits = []
    if 'liegt auf einem OSM-Pfad' in no: bits.append('Liegt genau auf einem Pfad – entweder die Grube oder der Pfad ist ungenau eingezeichnet.')
    m = re.search(r'Nr\. (\S+) ist in OSM (\d+)x an verschiedenen Stellen eingetragen', no)
    if m: bits.append(f'Die Nummer {m.group(1)} steht in OpenStreetMap {m.group(2)}× an verschiedenen Stellen – welche stimmt?')
    if 'Position?' in no: bits.append('In OpenStreetMap ist die Lage als unsicher markiert.')
    src = {'nur OSM': 'Nur aus OpenStreetMap bekannt, im Luftbild nicht zu erkennen.',
           'OSM; im Luftbild nicht erkennbar': 'In OpenStreetMap eingetragen, im Luftbild aber nicht zu sehen.',
           'OSM; im Luftbild unsicher': 'In OpenStreetMap eingetragen, im Luftbild nur undeutlich zu sehen.',
           'OSM; im Luftbild nicht eindeutig': 'In OpenStreetMap eingetragen, im Luftbild nicht eindeutig.',
           'OSM; Betrieb nicht geprüft': 'In OpenStreetMap eingetragen – ob es noch geöffnet ist, ist unbekannt.',
           'Höhenmodell': 'Nur im Höhenmodell (Laserscan) erkannt, im Luftbild nicht zu sehen.',
           'Luftbild (manuell ausgewertet)': 'Nur im Luftbild gesehen.'}.get(q)
    if src and not (bits and q == 'Höhenmodell + Luftbild'): bits.append(src)
    if p['kategorie'] == 'Trichter' and 'Form wahrscheinlich' in no: bits.append('Die Form ist im Höhenmodell nicht ganz eindeutig.')
    return ' '.join(bits) or 'Bisher nur aus einer Quelle bekannt.'

def description(p):
    """Free-text description worth showing (OSM description of SOS points / memorials, or the helper's own note)."""
    k, no = p['kategorie'], p.get('notiz') or ''
    if k in ('Rettungspunkt', 'Historisch') or 'Feldbegehung' in (p.get('quellen') or ''):
        s = re.split(r' \| (?:OSM-Hinweis|Nr\. )', no)[0].strip()
        return s if s and '=' not in s else ''
    return ''

DIRS = ['nördlich', 'nordöstlich', 'östlich', 'südöstlich', 'südlich', 'südwestlich', 'westlich', 'nordwestlich']
def where(e, n, anchors, self_name=''):
    """'ca. 120 m nordöstlich von Inselheim Rüstringen' from the nearest named anchor (within 700 m)."""
    best = None
    for name, ax, ay, w in anchors:
        if self_name and (self_name in name or name in self_name): continue
        d = math.hypot(e - ax, n - ay)
        if d <= 700 and (best is None or d * w < best[0]): best = (d * w, d, name, ax, ay)
    if not best: return ''
    _, d, name, ax, ay = best
    if d < 20: return f'direkt bei {name}'
    r = 5 if d < 100 else (10 if d < 400 else 50)
    a = math.degrees(math.atan2(e - ax, n - ay)) % 360
    return f'ca. {int(round(d / r) * r)} m {DIRS[int((a + 22.5) // 45) % 8]} von {name}'

def anchors_from(points, labels):
    """Named, easy-to-find places: map labels + named buildings, cafés, stops, memorials."""
    out, seen = [], set()
    SKIP = {'W E S T G R O D E N', 'Westlagune', 'Salinenbucht', 'Ruhezone I/32', 'Strand', 'Straße zum Westen', 'Standort alter Westturm'}
    for lab in labels:
        t = lab[0].replace('\n', ' ')
        if t in SKIP or t in seen: continue
        seen.add(t); out.append((t, lab[1], lab[2], 0.6))   # printed map names are the easiest to find
    for p, (e, n) in points:
        k, nm = p['kategorie'], (p['name'] or '').strip()
        if not nm or k not in ('Unterkunft', 'Gebäude', 'Gastronomie', 'Bauwerk', 'Haltepunkt', 'Einrichtung', 'Historisch', 'Gelände'): continue
        if k == 'Einrichtung' and p['typ'] in ('lifeboat', 'boat_storage'): continue   # boat names are no help on the ground
        nm = nm.replace(' - ', ' – ')
        if k == 'Haltepunkt': nm = f'Haltepunkt {nm}'
        if any(nm in s or s in nm for s in seen): continue
        seen.add(nm); out.append((nm, e, n, 1.0))
    return out
