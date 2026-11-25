"""cimc core: parse a Common Iterative Model (CIM) written in TOML,
evaluate its terms case by case, and hold the expanded cases that all
back ends print.

Design rules (they are the reason why several hypotheses of the
correspondence theorem hold by construction):
  * every term of every case is evaluated once, here, and printed by
    both back ends from the same object (hypothesis Rul);
  * numerals are public constants n0, n1, ... in both tools, and every
    numeral variable ranges over a finite domain (hypothesis Grd);
  * n-tuples are printed as right-nested pairs in both tools, so the
    term encoding is the identity on pairs (hypothesis Sig, no nesting
    side condition);
  * a step has at most one input from the attacker; a block of a ProVerif
    encoding is (state input, attacker input, guards, events, outputs,
    state output) (hypothesis Blk).
"""
import ast
import itertools
import tomllib


class CimError(Exception):
    pass


# ---------------------------------------------------------------- terms
# Values: ('num', k) | ('const', s) | ('var', x) | ('fun', f, args) |
#         ('pair', a, b)

def num(k):
    return ('num', k)


def mk_tuple(items):
    items = list(items)
    if not items:
        raise CimError('empty tuple')
    if len(items) == 1:
        return items[0]
    return ('pair', items[0], mk_tuple(items[1:]))


def free_vars(v, acc=None):
    acc = [] if acc is None else acc
    if v[0] == 'var':
        if v[1] not in acc:
            acc.append(v[1])
    elif v[0] == 'fun':
        for a in v[2]:
            free_vars(a, acc)
    elif v[0] == 'pair':
        free_vars(v[1], acc)
        free_vars(v[2], acc)
    return acc


def consts(v, acc):
    if v[0] == 'const':
        acc.add(v[1])
    elif v[0] == 'num':
        acc.add(('num', v[1]))
    elif v[0] == 'fun':
        for a in v[2]:
            consts(a, acc)
    elif v[0] == 'pair':
        consts(v[1], acc)
        consts(v[2], acc)
    return acc


def funs(v, acc):
    if v[0] == 'fun':
        acc.add((v[1], len(v[2])))
        for a in v[2]:
            funs(a, acc)
    elif v[0] == 'pair':
        funs(v[1], acc)
        funs(v[2], acc)
    return acc


class Evaluator:
    """Evaluate a term written in a small Python-like syntax:
    f(t1, ..., tn), tup(t1, ..., tn), integers, 'literal', names,
    integer + and -, and macro calls with 'x if cond else y'."""

    def __init__(self, functions, macros):
        self.functions = functions          # name -> (arity, private)
        self.macros = {}                    # name -> (params, ast)
        for name, m in macros.items():
            self.macros[name] = (m['params'],
                                 ast.parse(m['body'], mode='eval').body)

    def eval(self, src, env):
        node = ast.parse(src, mode='eval').body if isinstance(src, str) else src
        return self._ev(node, env)

    def _int(self, node, env):
        v = self._ev(node, env)
        if v[0] != 'num':
            raise CimError(f'integer expected, got {v}')
        return v[1]

    def _ev(self, n, env):
        if isinstance(n, ast.Constant):
            if isinstance(n.value, bool):
                raise CimError('booleans are not terms')
            if isinstance(n.value, int):
                return num(n.value)
            if isinstance(n.value, str):
                return ('const', n.value)
            raise CimError(f'bad constant {n.value!r}')
        if isinstance(n, ast.Name):
            if n.id in env:
                return env[n.id]
            return ('var', n.id)
        if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub)):
            a, b = self._int(n.left, env), self._int(n.right, env)
            r = a + b if isinstance(n.op, ast.Add) else a - b
            if r < 0:
                raise CimError('negative numeral')
            return num(r)
        if isinstance(n, ast.IfExp):
            return self._ev(n.body if self._cond(n.test, env) else n.orelse, env)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            f = n.func.id
            args = [self._ev(a, env) for a in n.args]
            if f == 'tup':
                return mk_tuple(args)
            if f in self.macros:
                params, body = self.macros[f]
                if len(params) != len(args):
                    raise CimError(f'macro {f}: arity')
                return self._ev(body, dict(zip(params, args)))
            if f in self.functions:
                if self.functions[f][0] != len(args):
                    raise CimError(f'function {f}: arity')
                return ('fun', f, args)
            raise CimError(f'unknown function or macro {f}')
        raise CimError(f'unsupported syntax: {ast.dump(n)}')

    def _cond(self, n, env):
        if isinstance(n, ast.Compare) and len(n.ops) == 1:
            a, b = self._int(n.left, env), self._int(n.comparators[0], env)
            op = n.ops[0]
            return {ast.Eq: a == b, ast.NotEq: a != b, ast.Lt: a < b,
                    ast.LtE: a <= b, ast.Gt: a > b, ast.GtE: a >= b}[type(op)]
        if isinstance(n, ast.BoolOp):
            vals = [self._cond(x, env) for x in n.values]
            return all(vals) if isinstance(n.op, ast.And) else any(vals)
        raise CimError('conditions compare integers')


def parse_atom(src):
    """'Sign(I,q,a)' -> ('Sign', ['I','q','a'])"""
    n = ast.parse(src, mode='eval').body
    if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            and all(isinstance(a, ast.Name) for a in n.args)):
        raise CimError(f'event atom expected: {src}')
    return n.func.id, [a.id for a in n.args]


# ---------------------------------------------------------------- model

class Case:
    """One instance of a step for fixed values of its domain variables."""

    def __init__(self, step, binding, state_in, state_out, inp, events,
                 outputs, checks):
        self.step = step            # step name
        self.binding = binding      # domain var -> int
        self.state_in = state_in    # value or None
        self.state_out = state_out  # value or None
        self.inp = inp              # value or None (pattern)
        self.events = events        # list of (name, [values])
        self.outputs = outputs      # list of values
        self.checks = checks        # list of (persist name, value)

    @property
    def label(self):
        return self.step + ''.join(f'_{k}{v}' for k, v in self.binding.items())


class Model:
    def __init__(self, path):
        with open(path, 'rb') as f:
            self.spec = tomllib.load(f)
        s = self.spec
        self.name = s['name']
        self.functions = {f['name']: (f['arity'], f.get('private', False))
                          for f in s['signature']['functions']}
        self.ev = Evaluator(self.functions, s.get('macros', {}))
        t = s['thread']
        self.role = t.get('role', 'Thread')
        self.fresh = t['fresh']
        self.state_vars = t['state']
        self.bound = t.get('bound')
        self.init = self._state_value({k: self.ev.eval(str(v), {})
                                       for k, v in t['init'].items()})
        self.persist = [(p['name'], p['term']) for p in t.get('persist', [])]
        self.publish = t.get('publish')
        self.leaks = t.get('leak', [])
        self.steps = t['step']
        self.responders = s.get('responder', [])
        self.properties = s.get('property', [])
        self.event_decl = {}
        self._expand()

    # state values are numerals or tuples of numerals
    def _state_value(self, d):
        return mk_tuple([d[x] for x in self.state_vars])

    def _cases(self, step, ctx_env, state=True):
        dom = step.get('domain', {})
        names = list(dom)
        for combo in itertools.product(*[dom[n] for n in names]):
            b = dict(zip(names, combo))
            env = dict(ctx_env)
            env.update({k: num(v) for k, v in b.items()})
            yield b, env

    def _events(self, srcs, env):
        out = []
        for e in srcs:
            n = ast.parse(e, mode='eval').body
            name = n.func.id
            args = [self.ev.eval(a, env) for a in n.args]
            prev = self.event_decl.setdefault(name, len(args))
            if prev != len(args):
                raise CimError(f'event {name}: arity')
            out.append((name, args))
        return out

    def _expand(self):
        self.thread_cases = []
        svars = self.state_vars
        for st in self.steps:
            for b, env in self._cases(st, {}):
                if not all(x in b for x in svars):
                    raise CimError(f'step {st["name"]}: domain must cover the state')
                sin = self._state_value({x: env[x] for x in svars})
                upd = {x: self.ev.eval(str(st['update'].get(x, x)), env) for x in svars}
                sout = self._state_value(upd)
                inp = self.ev.eval(st['input'], env) if 'input' in st else None
                evs = self._events(st.get('events', []), env)
                outs = [self.ev.eval(o, env) for o in st.get('outputs', [])]
                self.thread_cases.append(Case(st['name'], b, sin, sout, inp,
                                              evs, outs, []))
        self.resp_cases = []
        for r in self.responders:
            for b, env in self._cases(r, {}):
                inp = self.ev.eval(r['input'], env)
                evs = self._events(r.get('events', []), env)
                chk = [(k, self.ev.eval(v, env)) for k, v in r.get('check', {}).items()]
                self.resp_cases.append(Case(r['name'], b, None, None, inp, evs,
                                            [], chk))
        self.leak_events = []
        for lk in self.leaks:
            self.leak_events.append(self._events([lk['event']], {})[0])
        self.persist_vals = [(n, self.ev.eval(t, {})) for n, t in self.persist]
        self.publish_val = self.ev.eval(self.publish, {}) if self.publish else None
        for p in self.properties:
            for a in self._prop_atoms(p):
                nm, args = parse_atom(a)
                if self.event_decl.get(nm) != len(args):
                    raise CimError(f'property {p["name"]}: unknown event {a}')

    @staticmethod
    def _prop_atoms(p):
        atoms = []
        if p['kind'] == 'phi1':
            atoms.append(p['premise'])
            for d in p['conclusion']:
                atoms.extend(d)
        elif p['kind'] == 'phi2':
            atoms.extend(x.split('@')[0] for x in p['premise'])
        elif p['kind'] == 'phi3':
            atoms.extend(p['events'])
            atoms.extend(p.get('absent', []))
        return atoms

    # ------------------------------------------------ derived information
    def state_values_reachable(self):
        """State values reachable from init by the step cases."""
        seen, todo = [self.init], [self.init]
        while todo:
            s = todo.pop()
            for c in self.thread_cases:
                if c.state_in == s and c.state_out not in seen:
                    seen.append(c.state_out)
                    todo.append(c.state_out)
        return seen

    def all_constants(self):
        acc = set()
        vals = [self.init, self.publish_val] if self.publish_val else [self.init]
        vals += [v for _, v in self.persist_vals]
        for c in self.thread_cases + self.resp_cases:
            vals += [x for x in (c.state_in, c.state_out, c.inp) if x]
            vals += c.outputs + [v for _, v in c.checks]
            vals += [a for _, args in c.events for a in args]
            vals += [num(k) for k in c.binding.values()]
        for v in vals:
            consts(v, acc)
        return acc
