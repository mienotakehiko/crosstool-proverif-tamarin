"""Regression checks for the proof-domain guards added 2026-10-29."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cimc.core import Model
from cimc.checks import run

ROOT=Path(__file__).resolve().parents[1]


def status(m):
    return {k:s for k,s,_ in run(m)}


class Guards(unittest.TestCase):
    def setUp(self):
        self.m=Model(ROOT/'cims/lmots.toml')

    def test_both_existing_seeds_pass(self):
        for seed in ('lmots','lms_s2'):
            self.assertNotIn('FAIL', status(Model(ROOT/'cims'/f'{seed}.toml')).values())

    def test_absent_publication_fails(self):
        self.m.publish_val=None
        self.assertEqual(status(self.m)['LeakGuard'],'FAIL')

    def test_hidden_constructor_occurrence_fails(self):
        self.m.publish_val=('fun','ch',[('var','I'),('num',0),('num',0)])
        self.assertEqual(status(self.m)['LeakGuard'],'FAIL')

    def test_nested_tuple_publication_passes(self):
        self.m.publish_val=('pair',('num',0),('pair',('var','I'),('num',1)))
        self.assertEqual(status(self.m)['LeakGuard'],'OK')

    def test_no_leaks_no_publication_needed(self):
        self.m.leaks=[]
        self.m.publish_val=None
        self.assertEqual(status(self.m)['LeakGuard'],'OK')

    def test_observed_events_cannot_share_block(self):
        self.m.thread_cases[0].events.append(('Accept',[('var','I'),('num',0)]))
        self.assertEqual(status(self.m)['ObsOne'],'FAIL')

    def test_positive_leak_reachability_outside_fragment(self):
        self.m.properties=[dict(name='r',kind='phi3',events=['RevealSeed(I)'])]
        self.assertEqual(status(self.m)['LeakUse'],'FAIL')

    def test_leak_equality_outside_fragment(self):
        self.m.properties=[dict(name='r',kind='phi2',premise=['RevealSeed(I)@i','RevealSeed(I)@j'],conclusion='i = j')]
        self.assertEqual(status(self.m)['LeakUse'],'FAIL')

    def test_unguarded_dispatch_overlaps_guarded_case(self):
        self.m.thread_cases[0].inp=None
        self.assertEqual(status(self.m)['Det'],'FAIL')


if __name__=='__main__':unittest.main()
