# Proposed English manuscript correction — cimc 0.1.2

This text is an additive correction proposal. It has not been applied to the
original manuscript. Keep the proposed inclusion chain's reviewed
process-to-rule simulation premise, the Horn-abstraction and normalization
obligations, and the conditional transfer-dependent Achievement Levels.

## Generator implementation / side-condition paragraph

An independent audit identified a variable-capture defect in the accepted
input domain of cimc 0.1.1. For a constructor equality pattern containing an
otherwise unbound variable named `x`, the ProVerif printer reused the worker's
internal state variable, whereas the Tamarin rule treated `x` as an independent
rule variable. A model publishing `(I,seal(n1))`, starting at `n0`, and accepting
`(a,seal(x))` therefore passed the existing report but separated the generated
reachability semantics. ProVerif proved the target event unreachable and
Tamarin verified its reachability. This is a generator-domain defect, not a
resource-related inconclusive result.

Version 0.1.2 adopts a conservative supported-domain repair rather than
claiming general constructor-pattern support. A shared validation gate rejects
backend-reserved identifiers, equality subterms with variables not bound before
the entire input pattern, and body terms with unbound variables. In particular,
a binding introduced in one component of a ProVerif tuple pattern is not assumed
to be in scope in an equality subpattern of the same pattern. Unsupported scalar
equality input patterns are also rejected. The gates are reported as Hygiene,
Binding, and PatternSupported, and are enforced directly by both printers as
well as by the command-line entry point. The rejected counterexample receives
no regenerated ProVerif or Tamarin security verdict: rejection is the intended
result, not a proof that the original model is safe.

## Experimental reproducibility paragraph

The repair was implemented in an isolated full copy of cimc. The original
source tree, saved generated outputs, stored verdict records, and previous
proof-audit files were preserved and checked with SHA-256 manifests. The nine
existing correspondence-guard tests and 37 Achievement-Level checks passed.
The complete unittest discovery run passed 22 tests, comprising the nine
existing guard tests and thirteen new supported-domain tests; importing that
suite also executes the separate 37 AL assertions. The AL script's import-time
exit was restricted to direct execution in the copy, without changing its
assertions or expected values. Both stored seed AL regressions remained equal.

For LM-OTS and LMS_S2, all sixteen generated protocol models remained exactly
unchanged relative to the current 0.1.1 printer, except for the version header.
The eight newly generated ProVerif files were executed and all 21 stored
expected query outcomes agreed. All eight Tamarin variants loaded successfully;
only the standard variants' normal-execution lemmas were selected for proof,
and both were verified. Nonselected security lemmas remain analysis incomplete
in these runs and are not represented as newly proved.

The original capture outputs were re-executed unchanged, retaining the
separating verdicts. Version 0.1.2 rejected the corresponding CIM at all four
ProVerif and all four Tamarin printer entry points; the CLI exited with status
1 before producing an output directory. As an independent supported positive
control, a simple tuple-leaf variable was bound and used in an output, and was
then consistently renamed. Generated text was identical up to that bound-variable
renaming and the source-file header. Both controls had the same event
reachability outcome in all four ProVerif encodings and the standard Tamarin
variant. This demonstrates the tested renaming case, not general semantic
preservation for all renamings or full symbolic-language equivalence.

## Scope and limitations paragraph

The repair narrows the supported domain; it neither silently changes the
meaning of the unsupported capture model nor implements capture-avoiding
constructor decomposition. Renaming the offending variable alone does not
make that model supported, since the equality subterm remains unbound.
Reserved-name rejection is intentionally conservative, and some harmless
source names may also be refused. A general hygienic printer and a complete
cross-language parser/semantic validation remain outside this repair.
The restricted ground scheduler lemma and its remaining language-adequacy
boundary are unchanged. Passing the repaired checks is not a certificate
of translation correctness and does not justify removing unproved manuscript
assumptions or upgrading transfer-dependent grades.
