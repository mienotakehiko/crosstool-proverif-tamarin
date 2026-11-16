"""Unit tests of the transfer rules (Table 4) and of the frozen
diagnosis tree on synthetic records. Run: python3 tests/test_al.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cimc.evidence import Chain, Record, applies
from cimc.diagnose import diagnose
from cimc.al_assign import level_for

P1 = {'name': 'p', 'kind': 'phi1'}
OK = {'Sig': ('OK', ''), 'Bound(e)': ('OK', 'n = 2')}
BAD = {'Sig': ('OK', ''), 'Dist': ('FAIL', '')}
ch = Chain(bound_ok=False, n=2)
chb = Chain(bound_ok=True, n=2)


def R(model, o, why=None, **feat):
    return Record('X_' + model, 'p', o, why, o, feat)


def causes(recs, checks=OK, c=ch, prop=P1):
    return sorted(f['cause'] for f in diagnose(prop, recs, checks, c))


n = bad = 0
def check(name, got, exp):
    global n, bad
    n += 1
    if got != exp:
        bad += 1
        print(f'FAIL {name}: got {got}, expected {exp}')

# transfer (Table 4)
check('lin true -> T', applies(ch, P1, R('PV_lin', 'H'), 'T'), 'H')
check('lin true -/-> Tcl', applies(ch, P1, R('PV_lin', 'H'), 'Tcl'), None)
check('rep true -> Tcl', applies(ch, P1, R('PV_rep', 'H'), 'Tcl'), 'H')
check('rep false -/-> T', applies(ch, P1, R('PV_rep', 'W'), 'T'), None)
check('U2 true -/-> T without (e)', applies(ch, P1, R('PV_U2', 'H'), 'T'), None)
check('U2 true -> T with (e)', applies(chb, P1, R('PV_U2', 'H'), 'T'), 'H')
check('U2 false -> T', applies(ch, P1, R('PV_U2', 'W'), 'T'), 'W')
check('Urb2 false -> Trb', applies(ch, P1, R('PV_Urb2', 'W'), 'Trb'), 'W')
check('Urb2 false -/-> T', applies(ch, P1, R('PV_Urb2', 'W'), 'T'), None)
check('cl1 falsified -> Tom', applies(ch, P1, R('T_cl1', 'W'), 'Tom'), 'W')
check('base verified -/-> Tcl', applies(ch, P1, R('T_base', 'H'), 'Tcl'), None)
# Corollary 2: impossible pairs
check('lin true vs base falsified', causes([R('PV_lin', 'H'), R('T_base', 'W')]), ['ENC-map'])
check('U2 false vs base verified', causes([R('PV_U2', 'W'), R('T_base', 'H')], c=chb), ['ENC-map'])
check('rep true vs rb1 falsified', causes([R('PV_rep', 'H'), R('T_rb1', 'W')]), ['ENC-map'])
check('failed side condition', causes([R('PV_lin', 'H'), R('T_base', 'W')], checks=BAD), ['ENC-map'])
# ENC-clone, PV-abs (Corollary 1), PV-rec
check('rep false vs base verified', causes([R('PV_rep', 'W'), R('T_base', 'H')]), ['ENC-clone'])
check('lin cannot, base verified', causes([R('PV_lin', 'N', 'cannot'), R('T_base', 'H')]), ['PV-abs'])
check('lin cannot, base falsified', causes([R('PV_lin', 'N', 'cannot'), R('T_base', 'W')]), ['PV-rec'])
check('lin cannot, only cl1 falsified', causes([R('PV_lin', 'N', 'cannot'), R('T_cl1', 'W')]), ['PV-abs'])
check('lin cannot alone', causes([R('PV_lin', 'N', 'cannot')]), ['undetermined'])
check('PV timeout', causes([R('PV_rep', 'N', 'noterm'), R('T_base', 'H')]), ['PV-term'])
# Tamarin resources: memory curve
check('HEAP', causes([R('T_base', 'N', 'HEAP'), R('PV_lin', 'H')]), ['TM-res'])
check('timeout growing', causes([R('T_base', 'N', 'TIMEOUT', rss_growth_early_mb_per_min=300,
                                   rss_growth_late_mb_per_min=200), R('PV_lin', 'H')]), ['TM-res'])
check('timeout flat', causes([R('T_base', 'N', 'TIMEOUT', rss_growth_early_mb_per_min=300,
                                 rss_growth_late_mb_per_min=5), R('PV_lin', 'H')]), ['TM-search'])
check('SPEC-expr', causes([R('PV_lin', 'H'), R('T_base', 'H')], prop={'kind': 'phi1', 'rewrite': 'ProVerif'}), ['SPEC-expr'])
# levels
recs = [R('PV_lin', 'H'), R('T_base', 'H')]
check('level 4', level_for(ch, P1, recs, 'T', [], diagnose(P1, recs, OK, ch))[1], 4)
recs = [R('PV_lin', 'H'), R('T_base', 'N', 'HEAP')]
check('level 3', level_for(ch, P1, recs, 'T', [], diagnose(P1, recs, OK, ch))[1], 3)
recs = [R('PV_lin', 'H'), R('T_base', 'N', 'ERROR')]
check('level 1 (undiagnosed)', level_for(ch, P1, recs, 'T', [], diagnose(P1, recs, OK, ch))[1], 1)
recs = [R('PV_lin', 'H')]
check('level 1 (one tool)', level_for(ch, P1, recs, 'T', [], diagnose(P1, recs, OK, ch))[1], 1)
recs = [R('T_base', 'H'), Record('X_T_base__tri', 'p', 'H', None, 'true')]
check('level 2', level_for(ch, P1, recs, 'T', ['Dist'], diagnose(P1, recs, BAD, ch))[1], 2)
check('level 0', level_for(ch, P1, [R('PV_lin', 'N', 'cannot')], 'T', [], [])[1], 0)
# monotonicity: a translator record never lowers a level
recs = [R('T_base', 'H'), R('PV_lin', 'N', 'cannot'), R('PV_U2', 'H')]
f0 = diagnose(P1, recs, OK, ch)
l0 = level_for(ch, P1, recs, 'T', [], f0)[1]
recs2 = recs + [Record('X_T_base__tri', 'p', 'H', None, 'true')]
l1 = level_for(ch, P1, recs2, 'T', [], diagnose(P1, recs2, OK, ch))[1]
check('translator does not lower level', l1 >= l0, True)
recs = [R('T_rb1', 'W'), R('PV_lin', 'N', 'cannot'), R('T_base', 'H')]
l0 = level_for(ch, P1, recs, 'Trb', [], diagnose(P1, recs, OK, ch))[1]
recs2 = recs + [Record('X_T_rb1__tri', 'p', 'W', None, 'false')]
l1 = level_for(ch, P1, recs2, 'Trb', [], diagnose(P1, recs2, OK, ch))[1]
check('Trb level 3 kept with translator', (l0, l1), (3, 3))
print(f'{n - bad}/{n} tests passed')
sys.exit(1 if bad else 0)
