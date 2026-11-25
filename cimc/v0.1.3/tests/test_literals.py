"""0.1.3 guard on string literals that collide with printed numerals."""
import copy
from pathlib import Path
import sys, unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cimc.core import Model, CimError
from cimc.checks import run
from cimc.backends import proverif, tamarin

ROOT = Path(__file__).resolve().parents[1]


class Literals(unittest.TestCase):
    def setUp(self):
        self.m = Model(ROOT / 'cims/lmots.toml')

    def rejected(self, m):
        self.assertTrue(any(k == 'Hygiene' and s == 'FAIL' for k, s, _ in run(m)))
        for enc in ('U', 'Urb', 'lin', 'rep'):
            with self.assertRaisesRegex(CimError, 'unsupported'):
                proverif(m, enc, 2, '0.1.3', 'test')
        for variant in ('base', 'cl1', 'rb1', 'omega'):
            with self.assertRaisesRegex(CimError, 'unsupported'):
                tamarin(m, variant, '0.1.3', 'test')

    def test_numeral_shaped_literals_rejected(self):
        for literal in ('n0', 'n1', 'n12'):
            with self.subTest(literal=literal):
                z = copy.deepcopy(self.m)
                z.thread_cases[0].outputs = [('const', literal)]
                self.rejected(z)

    def test_literal_inside_a_check_rejected(self):
        z = copy.deepcopy(self.m)
        name, _ = z.resp_cases[0].checks[0]
        z.resp_cases[0].checks[0] = (name, ('fun', 'ch', [('var', 'I'), ('const', 'n1'), ('num', 1)]))
        self.rejected(z)

    def test_non_identifier_literal_rejected(self):
        for literal in ('a b', '1x', 'x-y', ''):
            with self.subTest(literal=literal):
                z = copy.deepcopy(self.m)
                z.thread_cases[0].outputs = [('const', literal)]
                self.rejected(z)

    def test_ordinary_literals_accepted(self):
        for literal in ('sign', 'm', 'k', 'n', 'nx1', 'N1', 'node1'):
            with self.subTest(literal=literal):
                z = copy.deepcopy(self.m)
                z.thread_cases[0].outputs = [('const', literal)]
                self.assertNotIn('FAIL', [s for k, s, _ in run(z) if k == 'Hygiene'])

    def test_signer_inputs_unchanged(self):
        for cim in ('lmots', 'lms_s2'):
            with self.subTest(cim=cim):
                self.assertNotIn('FAIL', [s for _, s, _ in run(Model(ROOT / f'cims/{cim}.toml'))])


if __name__ == '__main__':
    unittest.main()
