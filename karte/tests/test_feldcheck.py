"""Rules for field-check submissions (feldcheck_merge) and the inbox copy (feldcheck_inbox).
Run: python -m unittest discover -s karte/tests"""
import json, os, shutil, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts'))
import feldcheck_merge as FM
import feldcheck_inbox as FI

T0 = 1760000000000   # Oct 2025
NOW = T0 + 1000
E, N = 424500, 5960000   # inside the map frame
A = lambda **k: {'name': 'Anna Müller', 'geraet_id': 'd-aaaa-1111', **k}
B = lambda **k: {'name': 'Ben', 'geraet_id': 'd-bbbb-2222', **k}
C = lambda **k: {'name': 'Cem', 'geraet_id': 'd-cccc-3333', **k}


class Merge(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(); self.e = self.d + '/data/feldcheck/eingang'; os.makedirs(self.e + '/abgelehnt')
    def tearDown(self): shutil.rmtree(self.d)
    def put(self, name, content, rejected=False):
        open(f"{self.e}/{'abgelehnt/' if rejected else ''}{name}", 'w').write(content if isinstance(content, str) else json.dumps(content))
    def load(self, now=NOW): return FM.load(self.d, now_ms=now)

    def test_broken_input_is_skipped_not_fatal(self):
        self.put('1.json', '{kaputt')
        self.put('2.json', A(name=['x'], verdicts={'BK001': {'st': 'ok', 't': T0}, 'BK002': {'st': 'xx', 't': T0}, 'BK003': {'st': 'ok', 't': 'gestern'},
                                                    '../x': {'st': 'ok', 't': T0}},
                             neu={'Nabc': {'t': T0, 'e': 1, 'n': 2}, 'Nok1': {'t': T0, 'e': E, 'n': N, 'typ': 'Bank'}}))
        r = self.load()
        self.assertEqual(list(r['verd']), ['BK001']); self.assertEqual(list(r['neu']), ['Nok1']); self.assertEqual(len(r['skipped']), 5)

    def test_corrected_position_survives_later_confirmation(self):
        self.put('1.json', A(verdicts={'BK001': {'st': 'woanders', 't': T0, 'e': E + 100, 'n': N}}))
        self.put('2.json', B(verdicts={'BK001': {'st': 'ok', 't': T0 + 5}}))
        v = self.load()['verd']['BK001']
        self.assertEqual((v['st'], v['e'], v.get('bestaetigt')), ('woanders', E + 100, True))

    def test_two_devices_not_found_means_missing(self):
        self.put('1.json', A(verdicts={'X1': {'st': 'nf', 't': T0}}))
        self.put('2.json', B(verdicts={'X1': {'st': 'nf', 't': T0 + 5}}))
        self.assertEqual(self.load()['verd']['X1']['st'], 'fehlt')

    def test_confirmation_in_between_resets_not_found(self):
        self.put('1.json', A(verdicts={'X1': {'st': 'nf', 't': T0}}))
        self.put('2.json', C(verdicts={'X1': {'st': 'ok', 't': T0 + 3}}))
        self.put('3.json', B(verdicts={'X1': {'st': 'nf', 't': T0 + 5}}))
        self.assertEqual(self.load()['verd']['X1']['st'], 'nf')

    def test_withdrawal_only_affects_own_device(self):
        self.put('1.json', A(verdicts={'X1': {'st': 'fehlt', 't': T0}}))
        self.put('2.json', B(verdicts={'X1': {'st': 'ok', 't': T0 - 5}}))
        self.put('3.json', A(verdicts={'X1': {'st': 'zurueck', 't': T0 + 9}}))
        self.assertEqual(self.load()['verd']['X1']['st'], 'ok')

    def test_rejected_entries_stay_out_and_device_learns(self):
        same = {'X2': {'st': 'fehlt', 't': T0}}
        self.put('8.json', A(verdicts=same), rejected=True); self.put('9.json', A(verdicts=same))
        r = self.load()
        self.assertNotIn('X2', r['verd']); self.assertEqual(r['stand']['d-aaaa-1111']['x'], {'X2': T0})

    def test_repeated_entry_belongs_to_first_file(self):
        same = {'X2': {'st': 'fehlt', 't': T0}}
        self.put('1.json', A(verdicts=same)); self.put('2.json', A(verdicts=same))
        self.assertEqual(self.load()['verd']['X2']['datei'], '1.json')

    def test_deleted_new_object_is_gone(self):
        self.put('1.json', A(neu={'Nq': {'t': T0, 'e': E, 'n': N}}))
        self.put('2.json', A(neu={'Nq': {'t': T0 + 1, 'geloescht': True}}))
        self.assertEqual(self.load()['neu'], {})

    def test_time_in_the_future_is_rejected(self):
        self.put('1.json', A(verdicts={'X3': {'st': 'ok', 't': T0 + 10 * 86400000}}))
        self.assertEqual(self.load(now=T0)['verd'], {})

    def test_old_file_without_device_uses_name(self):
        self.put('1.json', {'name': 'Alt', 'verdicts': {'X4': {'st': 'ok', 't': T0}}})
        self.assertEqual(self.load()['verd']['X4']['dev'], 'name:Alt')

    def test_position_outside_map_is_skipped(self):
        self.put('1.json', A(verdicts={'X5': {'st': 'woanders', 't': T0, 'e': 0, 'n': 0}}))
        r = self.load(); self.assertEqual(r['verd'], {}); self.assertEqual(len(r['skipped']), 1)


class Inbox(unittest.TestCase):
    def test_initials(self):
        self.assertEqual(FM.kurz('Anna Müller'), 'A. M.'); self.assertEqual(FM.kurz('ben'), 'B.'); self.assertEqual(FM.kurz(None), 'Feldcheck')

    def test_public_file_name(self):
        self.assertEqual(FI.public_name('2026-10-15-10-00_anna-muller_ab12.json', True), '2026-10-15-10-00_am_ab12.json')
        self.assertEqual(FI.public_name('2026-10-15-10-00_anna-muller_ab12.json', False), '2026-10-15-10-00_anna-muller_ab12.json')
        self.assertTrue(FI.public_name('irgendwas.json', True).startswith('x_'))

    def test_anonymized_copy_keeps_entries(self):
        raw = json.dumps(A(geraet='Mozilla/5.0', verdicts={'BK1': {'st': 'ok', 't': T0}})).encode()
        d = json.loads(FI.anonymize(raw))
        self.assertEqual(d['name'], 'A. M.'); self.assertNotIn('geraet', d); self.assertEqual(d['verdicts'], {'BK1': {'st': 'ok', 't': T0}})
        self.assertEqual(d['geraet_id'], 'd-aaaa-1111')
        self.assertEqual(FI.anonymize(b'{kaputt'), b'{kaputt')


if __name__ == '__main__':
    unittest.main()
