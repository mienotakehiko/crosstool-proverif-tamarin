"""0.1.2 conservative supported-domain regressions (no upstream imports)."""
import copy
from pathlib import Path
import sys, unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cimc.core import Model, CimError
from cimc.checks import run
from cimc.backends import proverif, tamarin
from cimc.validation import RESERVED

ROOT=Path(__file__).resolve().parents[1]
class Hygiene(unittest.TestCase):
    def setUp(self): self.m=Model(ROOT/'cims/lmots.toml')
    def rejected(self,m):
        self.assertTrue(any(s=='FAIL' for _,s,_ in run(m)))
        for enc in ('U','Urb','lin','rep'):
            with self.assertRaisesRegex(CimError,'unsupported'):proverif(m,enc,2,'0.1.2','test')
        for variant in ('base','cl1','rb1','omega'):
            with self.assertRaisesRegex(CimError,'unsupported'):tamarin(m,variant,'0.1.2','test')
    def test_all_reserved_binders_rejected(self):
        for name in RESERVED | {'v_I','c_I','n12','Thr_R','Start_R','Leak_R'}:
            with self.subTest(name=name):
                z=copy.deepcopy(self.m);z.thread_cases[0].outputs=[('var',name)]
                self.rejected(z)
    def test_constructor_free_x_rejected(self):
        self.m.thread_cases[0].inp=('pair',('const','sign'),('fun','ch',[('var','x'),('num',0),('num',0)]))
        self.rejected(self.m)
    def test_alpha_renaming_does_not_hide_unsupported_constructor_binder(self):
        for name in ('Z','Payload','Renamed'):
            z=copy.deepcopy(self.m);z.thread_cases[0].inp=('pair',('num',0),('fun','ch',[('var',name),('num',0),('num',0)]))
            self.rejected(z)
    def test_same_pattern_binding_not_visible_to_equality(self):
        self.m.thread_cases[0].inp=('pair',('var','Payload'),('fun','ch',[('var','Payload'),('num',0),('num',0)]))
        self.rejected(self.m)
    def test_preexisting_thread_name_in_constructor_equality_allowed(self):
        self.m.thread_cases[0].inp=('pair',('var','Payload'),('fun','ch',[('var','I'),('num',0),('num',0)]))
        self.assertNotIn('FAIL',[s for _,s,_ in run(self.m)])
    def test_later_binding_cannot_repair_earlier_equality(self):
        self.m.thread_cases[0].inp=('pair',('fun','ch',[('var','Payload'),('num',0),('num',0)]),('var','Payload'))
        self.rejected(self.m)
    def test_fresh_public_channel_collision(self):
        self.m.fresh=['I','c'];self.rejected(self.m)
    def test_state_channel_collision(self):
        self.m.fresh=['I','st'];self.rejected(self.m)
    def test_generated_pattern_binder_collision(self):
        self.m.fresh=['I','v_Payload'];self.rejected(self.m)
    def test_body_variable_not_bound(self):
        self.m.thread_cases[0].outputs=[('var','Payload')];self.rejected(self.m)
    def test_scalar_pattern_explicitly_unsupported(self):
        self.m.thread_cases[0].inp=('const','sign');self.rejected(self.m)
    def test_no_fresh_list_diagnostic(self):
        self.m.fresh=[]
        for fn,args in ((proverif,('lin',2)),(tamarin,('base',))):
            with self.assertRaisesRegex(CimError,'unsupported'):fn(self.m,*args,'0.1.2','test')
    def test_both_seeds_all_variants_generate(self):
        for seed in ('lmots','lms_s2'):
            z=Model(ROOT/'cims'/f'{seed}.toml')
            self.assertNotIn('FAIL',[s for _,s,_ in run(z)])
            for e in ('U','Urb','lin','rep'): self.assertIn('0.1.2',proverif(z,e,z.bound,'0.1.2','test'))
            for v in ('base','cl1','rb1','omega'):self.assertIn('0.1.2',tamarin(z,v,'0.1.2','test'))

if __name__=='__main__':unittest.main()
