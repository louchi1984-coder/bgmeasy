import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

SCRIPTS=Path(__file__).resolve().parents[1]/'scripts'
sys.path.insert(0,str(SCRIPTS))
import instruments as K
import sf2_capabilities as SF
import soundfonts as F
import render_score as R


def chunk(tag,data):
    return tag+struct.pack('<I',len(data))+data+(b'\0' if len(data)%2 else b'')


def fixture(sample_id=0):
    ph=struct.pack('<20sHHHIII',b'Test',0,0,0,0,0,0)+struct.pack('<20sHHHIII',b'EOP',0,0,2,0,0,0)
    pb=b''.join(struct.pack('<HH',n,0) for n in [0,1,3])
    pg=b''.join(struct.pack('<HH',*g) for g in [(43,60|(72<<8)),(44,20|(100<<8)),(41,0)])
    ins=struct.pack('<20sH',b'Inst',0)+struct.pack('<20sH',b'EOI',2)
    ib=b''.join(struct.pack('<HH',n,0) for n in [0,2,7])
    ig=b''.join(struct.pack('<HH',*g) for g in [(43,55|(84<<8)),(44,10|(127<<8)),(43,64|(76<<8)),(44,40|(110<<8)),(58,65),(54,1),(53,sample_id)])
    sh=struct.pack('<20sIIIIIBbHH',b'Sample',0,1000,100,900,1000,60,0,0,1)+struct.pack('<20sIIIIIBbHH',b'EOS',0,0,0,0,1000,0,0,0,1)
    pdta=b'pdta'+b''.join(chunk(tag,data) for tag,data in [(b'phdr',ph),(b'pbag',pb),(b'pgen',pg),(b'inst',ins),(b'ibag',ib),(b'igen',ig),(b'shdr',sh)])
    return chunk(b'RIFF',b'sfbk'+chunk(b'LIST',pdta))


class CapabilityTests(unittest.TestCase):
    def test_preset_and_instrument_key_velocity_intersections(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.sf2';p.write_bytes(fixture());info=SF.inspect(p)[(0,0)]
        self.assertEqual(info['covered_midi_keys'],list(range(64,73)))
        self.assertEqual(info['velocity_ranges'],[(40,100)])
        z=info['zones'][0]
        self.assertEqual((z['root_midi'],z['loop_mode'],z['duration_seconds']),(65,1,1))

    def test_bad_sample_reference_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.sf2';p.write_bytes(fixture(99))
            with self.assertRaisesRegex(ValueError,'sample'):
                SF.inspect(p)

    def test_truncated_riff_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.sf2';p.write_bytes(fixture()[:-20])
            with self.assertRaises(ValueError):SF.inspect(p)

    def test_every_actual_entry_has_profile_and_sources(self):
        d=K.knowledge();sources=json.loads(K.SOURCES.read_text(encoding="utf-8"))
        for entry in F.build_catalog()['entries']:
            with self.subTest(entry=entry['id']):
                key=K.profile_for(entry,d);p=d['profiles'][key]
                self.assertIn(p['family'],d['families'])
                self.assertTrue(p['sources'])
                self.assertTrue(set(p['sources'])<=sources.keys())
                self.assertTrue(p['mechanism'] and p['techniques'] and p['writing_guidance'])

    def test_builtin_and_drum_coverage(self):
        d=K.knowledge()
        self.assertEqual(set(d['builtin_profiles']),set(R.INST)|{'drums'})
        import render_score_sf2 as S
        self.assertEqual(set(d['drum_profiles']),set(S.DRUM_NOTE)|set(S.MELODIC_DRUMS))

    def test_variants_with_different_instruments_do_not_inherit_base(self):
        d=K.knowledge();catalog={e['id']:e for e in F.build_catalog()['entries']}
        for ident,expected in [('generaluser-gs:8:24','ukulele'),('generaluser-gs:16:25','mandolin'),
                              ('generaluser-gs:13:48','woodwind-ensemble'),('generaluser-gs:8:107','taisho-koto')]:
            self.assertEqual(K.profile_for(catalog[ident],d),expected)

    @unittest.skipUnless((F.ROOT/'DSK-Asian-DreamZ.sf2').is_file(), 'optional local DSK font is not redistributed')
    def test_uncertain_dsk_identity_is_not_asserted_by_chinese_tags(self):
        d=K.knowledge();catalog=F.build_catalog()
        entry=next(e for e in catalog['entries'] if e['id']=='dsk-asian-dreamz:0:2')
        self.assertEqual(d['profiles'][K.profile_for(entry,d)]['evidence_level'],'identity_unverified')
        self.assertNotIn('柳琴',entry['tags'])
        entry=next(e for e in catalog['entries'] if e['id']=='dsk-asian-dreamz:0:5')
        self.assertNotIn('竹笛',entry['tags'])

    @unittest.skipUnless((F.ROOT/'DSK-Asian-DreamZ.sf2').is_file(), 'optional local DSK font is not redistributed')
    def test_real_pipa_structure_is_not_a_round_robin_claim(self):
        entry=next(e for e in F.build_catalog()['entries'] if e['id']=='dsk-asian-dreamz:0:0')
        c=K.capability(entry,K.knowledge(),True)
        self.assertEqual(c['listening_status'],'not_listened')
        self.assertEqual({tuple(z['velocities']) for z in c['sf2']['zones']},{(0,127)})
        self.assertEqual(c['sf2']['loop_modes'],[0])

    def score(self,config,bar='C4:4',performance=None,backend='sf2'):
        s={'bpm':100,'tracks':{'v':config},'sections':{'A':{'v':[bar]}},'arrangement':['A'],
           'design':{'performance':{'v':performance or {'instrument':'flute','technique':'连句','implementation':'普通单音近似'}}}}
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'score.json';p.write_text(json.dumps(s), encoding="utf-8");return K.audit_score(p,backend)

    def test_parameters_are_checked_against_actual_backend(self):
        cfg={'inst':'dizi','preset':'generaluser-gs:0:73','params':{'breath':.1,'bend':.3,'vibrato':.006}}
        a=self.score(cfg);self.assertEqual(a['tracks']['v']['ignored_params'],['bend','breath','vibrato'])
        b=self.score(cfg,backend='synth');self.assertEqual(b['tracks']['v']['ignored_params'],[])

    @unittest.skipUnless((F.ROOT/'DSK-Asian-DreamZ.sf2').is_file(), 'optional local DSK font is not redistributed')
    def test_erhu_pitch_support_depends_on_score_inst_not_catalog_default(self):
        a=self.score({'inst':'erhu','preset':'dsk-asian-dreamz:0:4','params':{'bend':.2,'vibrato':.003}},
                     performance={'instrument':'erhu','implementation':'MIDI弯音'})
        self.assertEqual(a['tracks']['v']['ignored_params'],[])

    def test_unknown_preset_cannot_silently_receive_generic_profile(self):
        with self.assertRaises(ValueError):K.profile_for({'id':'unknown:0:0','source':'unknown'},K.knowledge())
        with self.assertRaises(ValueError):K.lookup('unknown:0:0')

    def test_dantranh_outside_nearest_sample_is_reported(self):
        a=self.score({'inst':'guzheng','engine':'sampler:dantranh'},bar='C0:4',performance={'instrument':'dan-tranh'})
        self.assertTrue(any('夹住' in s for s in a['issues']))

    def test_custom_world_drum_mapping_beats_taiko_default(self):
        a=self.score({'inst':'drums','preset':'freepats-light/world-percussion:0:0'},bar='taiko: X...............',performance={'instrument':'hand-percussion'})
        route=a['tracks']['v']['drum_routing']['taiko']
        self.assertEqual(route,{'route':'custom_midi_note','note':69})

    def test_default_taiko_is_reported_as_bass_drum_sample(self):
        a=self.score({'inst':'drums'},bar='taiko: X...............',performance={'instrument':'drum-kit'})
        self.assertEqual(a['tracks']['v']['drum_routing']['taiko']['route'],'vcsl:bassdrum')

    def test_cli_rejects_unknown_id(self):
        r=subprocess.run([sys.executable,'-I','-B',str(SCRIPTS/'instruments.py'),'preset','missing:0:0'],capture_output=True,text=True, encoding="utf-8", errors="replace")
        self.assertNotEqual(r.returncode,0)


if __name__=='__main__':unittest.main(verbosity=2)
