# Restricted ground scheduler lemma and generated-code audit

Date: 11 November 2026. Status: a non-circular, handwritten lemma for explicitly defined scheduler transition systems, a line-level code audit, and independent finite/native checks. **Not a theorem equating full ProVerif symbolic semantics with Tamarin semantics.** No upstream source or manuscript was modified. Source hashes and read-only copies are supplied.

## 1. What is actually closed

For the restricted transition systems below, the sets of finite observed event words are equal. The proof covers reservations, failed dispatch/abandonment, the unique successful parallel case, zero/one observed event, arbitrary finite lists of delayed outputs, successor release, and stopping at every prefix. Forward simulation uses a relation allowing an atomic scheduler to be ahead in output knowledge. Reverse trace construction uses a stricter stable-boundary relation; it does **not** use the forward relation backwards. No fairness, maximal-run, knowledge-equivalence-at-every-prefix, branching bisimulation, or liveness conclusion follows.

There is a real generated-code counterexample outside the fragment: a free variable under a constructor named `x` captures the ProVerif worker's internal state binder `x`. Existing checks return no FAIL. The generated ProVerif and Tamarin models give opposite reachability verdicts. Thus the unrestricted generated-code theorem cannot be recovered merely by completing a scheduling proof.

## 2. Exact domain (G)

G1. Use `proverif(...,'lin',...)` and `tamarin(...,'base',...)`, not replicated-state, misuse, or rollback variants. Condition on **exactly one initialized thread**. Subsequent scheduling of `!Thread()` / Init is disabled. This is a restriction on runs, not a claim that either printed model enforces one thread. The native smoke runs retain their actual multiple-initialization semantics; they do not certify this restriction.

G2. Fix one initial identity valuation up to alpha-renaming. The printers require `fresh[0]`, allocate `I`, and create a private state channel `st`. Accordingly, literally “no fresh at all” is impossible for these printers (the empty-list test raises IndexError). The precise restriction is **no fresh allocation during protocol updates**, one fixed initial identity, and one fixed private state channel. Fresh-name extrusion/alpha-equivalence across arbitrary threads is outside the lemma.

G3. Expanded states are ground numeral/pair terms. The finite reachable state graph is acyclic. Each case consumes one state and creates one successor. Each case's input, outputs, and event arguments are **ground after substituting the fixed initial names**: no additional message variables, including variables inside constructor equality patterns. `Case.checks` is empty for thread cases. Persistent tables, leaks, responders, Clone, Rollback and snapshots are absent. All reachable cases, not only the chosen fixture path, satisfy these conditions.

G4. The shared term algebra is free: public constants, fixed private names, pairs with public projections, free public/private constructors with no equations/destructors beyond pair projection. Ground-term printers agree by structural induction: numeral n maps to the same designated atom, literal to its designated atom, fixed name to its fixed name, constructors homomorphically, and pairs homomorphically. Public deduction D is monotone/idempotent and includes public constants and public constructors/pair projections, never private-constructor synthesis. Names and identifiers are hygienic, and both generated texts must parse. These are extra audited premises, **not established by the existing Sig report**.

G5. For each state and public message, at most one case's ground input matches. A missing case input matches every dispatch message, so cannot coexist with any other same-state case. Importantly, the ProVerif printer still waits for `in(c,y)` even for such a case. Public n0 supplies a harmless dispatch message, so the no-input atomic step can always be realized.

G6. A case has at most one event from a fixed observation alphabet O. Other events are hidden, not grouped into a new timestamp. Observations are event words with arguments and occurrence order; no numeric wall-clock time is preserved. With at most one observed event per atomic step, distinct observed occurrences retain distinct order/equality of occurrence positions. A transfer of a particular printed property still needs its own formula interpretation and is **not proved here**.

G7. Start after public initialization has completed, with K0 = D(public constants ∪ {P}), where P is the actual initial public output (or no added term if absent). The fixture publishes `(I,'a')`; hence I is available by pair projection, not by an invented publication assumption. Any designated initially public component must be pair-projectable or otherwise explicitly deducible from P. This lemma has no leak guard to enable, and does not require hidden names under private constructors to become public. Initial state publication on `st` is not a public output. No observer other than the Dolev--Yao sender/receiver and the single worker acts; no external stateful responder can exploit partially delivered messages.

These conditions deliberately exclude both existing signing CIMs (fresh secrets, persistent verification data, leaks and responders). They do not upgrade either model's Achievement Level.

## 3. Operational definitions

Write a case as c = (s,p,e,L,t), with predecessor s, ground input p or absent, observed label e in O or epsilon, output list L=[o1,...,or], and successor t. Nonobserved events are epsilon. Input enabledness is p in D(K), or true for absent input. Messages are reusable attacker knowledge, not linear resources.

The atomic system A has states `(s,K,w)`, K=D(K), and transitions

`(s,K,w) --e--> (t,D(K ∪ set(L)),w·e)`

for enabled c. Empty e appends nothing. All public deduction steps are already absorbed by D. No transition deletes K. This is the generated base protocol-rule shape with `!Thr(I)` fixed and `Start` hidden, not a definition of all native Tamarin infrastructure rules.

The sequential-worker system P has the following phases:

* `available(s,K,w)`: one pending private output of s;
* `reserved(s,K,w)`: a worker has received that output, but has not yet received its public dispatch;
* `dispatched(s,y,K,w)`: y in D(K) has been received and the parallel ground case checks have not all reduced;
* `selected(c,K,w)`: the unique matching case has passed pattern/state checks, before its observed event;
* `post(c,j,K,w)`: the case has committed and emitted its observed event (if any), and exactly its first j public outputs have been delivered; its successor t is held locally;
* `abandoned(s,K,w)`: the reserved state is lost, with no successful branch and no continuation capable of releasing a token.

Reservation is silent. Dispatch is silent and y must be deducible. Failed checks reduce to inactive processes. By G5 at most one branch survives. A successful branch reaches selected; no survivor reaches abandoned. From selected, commit emits e, sets the logical state to t and enters post(c,0). If e is empty this is a silent bookkeeping point after the checks and before the outputs. From post(c,j), j<r, a silent public delivery adds oj+1 and closes knowledge. From post(c,r) a silent private release reaches available(t). Unfolding worker replication and private-channel communication are silent; extra waiting workers do not carry a state and are irrelevant. Failed sibling branches never output a state. No second successful block can start before the unique successor is released.

This is a scheduler reduction model **defined here**, not a replacement specification for the full applied-pi-calculus. Splitting pattern/state checks into separate epsilon steps changes no rule in this model because ground checks have no side effects. Relating the full language semantics (including attacker processes, structural congruence and public asynchronous outputs) to this reduction model remains a separate semantic adequacy obligation. Code correspondence is audited in mapping.csv, not assumed as “translation correctness” inside the lemma.

## 4. Forward relation R and every transition case

Relate available, reserved, dispatched, selected, and abandoned at logical predecessor s to `(s,D(K),w)`. Dispatched/selected retain their local metadata; it is not part of A. Relate post(c,j,K,w) to

`(t, D(K ∪ {oj+1,...,or}), w)`.

Thus A may know a finite debt of outputs that P has not yet emitted. The relation neither asserts that a reserved state is still on the channel nor equates abandoned with executable concrete state. Relate additional inactive failed branches and empty waiting workers by ignoring them.

Initial stable pair satisfies R by G7. For every P step from a reachable related pair:

1. **Replication unfold / reserve / private receive.** Same state, K, w; A stutters. Only one worker can reserve the unique token.
2. **Public dispatch.** Same state, K, w; y∈D(K), so R is unchanged. An arbitrary attacker message outside successful patterns is allowed.
3. **Failed input pattern / failed state equality / failed sibling.** Silent. If no surviving case, transition to abandoned; A stutters retaining s. If one survives, reductions of other branches are ignored. G3 and G5 rule out additional successful branches. Waiting without a dispatch is also allowed.
4. **Selected case, before the observed event.** Checking is silent. R still relates predecessor s and identical knowledge. No successor is guessed before success.
5. **Commit with one observed event.** Input is absent or was received from D(K); the ground predecessor equality passed. A can fire the same c, emitting the same event and moving to t with all L. This is exactly R at post(c,0). Crucially, the old relation had no output debt, so input enabledness is not justified using a future output of this same case.
6. **Commit with zero observed events.** Same argument, with epsilon on both sides. Any unobserved internal event prefix is silent.
7. **Public output j+1.** A stutters. By idempotence and associativity of D,
   `D(D(K ∪ {oj+1}) ∪ remaining-tail) = D(K ∪ remaining-tail-before)`.
   Hence the debt equation is unchanged. This includes duplicate, pair, public-constructor, and private-constructor ground outputs; no inversion of a private constructor is assumed.
8. **Private successor release.** All debt has been paid; post(c,r) and available(t) have the same K. A stutters. A worker may immediately reserve the successor, which is case 1.
9. **Abandoned / terminal state / stop at a prefix.** Abandoned has no productive outgoing step; A need not take one. Terminal states can still be reserved and abandoned by the replicated worker, with no event. Finite runs can stop in any phase, including just after the event and before any output. There is no obligation to drain debt to match the already observed word.
10. **Attacker deduction/delivery-only administrative moves.** Normalizing D(K) is idempotent; receiving public outputs is case 7, and supplying inputs is case 2. There are no responder, table, leak, allocation, clone, rollback, or second-init cases under G.

Induction on the finite P reduction length proves `Tr(P) ⊆ Tr(A)`. Acyclicity ensures finite blocks on each execution and bounds completed updates, but the local forward argument does not need an assumed theorem about translation.

## 5. Reverse construction B (not R reversed)

Let B relate only available(s,K,w) to `(s,K,w)` with exact knowledge and no debt, ignoring dormant workers. For each atomic transition from a B-related pair, reserve s, send its enabled ground p, or public n0 for an absent input, reduce all failed branches, select the unique successful case, execute the event, emit all r outputs in printed order, and release t. This finite P path returns to B with exactly `D(K ∪ set(L))` and the same appended observation. This proves all atomic-step cases:

* ground matching input: send the deducible p;
* absent input: send n0 (the generated wait must not be omitted);
* zero observed event: all steps silent;
* one observed event: exactly one matching observation;
* zero outputs: immediate private release after commit;
* one/multiple outputs: r deliveries, no intervening successful worker because t is not yet released;
* terminal A state: zero transitions matched by the finite P prefix;
* empty A run: initial B pair itself.

Induction on finite A run length yields `Tr(A) ⊆ Tr(P)`. There is no schedule-independent reverse simulation from every R-related pair: after reserving q=0 and receiving a bad public value, P is abandoned while A still has q=0 and can emit EvA. This is a concrete failed reverse case, confirmed by the explorer. Reverse matching requires the constructed B representative, never an arbitrary abandoned representative.

Therefore **the two explicitly defined scheduler systems have equal finite event-word languages**. This is an existence-of-schedules statement with stuttering, not branching bisimulation. In particular, it does not claim equality of knowledge at the same event prefix: A knows `seal(I)` immediately at EvA; P can stop just after EvA without knowing it. Serializing before the next successful block is valid only because there is one token and no other productive role.

## 6. Initialization and actual printer audit

The ProVerif order is fresh identity, private channel, table insertions (excluded), initial public output, then parallel initial private token / replicated worker. Tamarin Init produces `!Thr`, `St`, and Out in one step. By conditioning on completed initialization, setting K0 from the actual output and hiding Start, the scheduler initial states agree without assuming translation correctness. Pre-init prefixes have empty observation and can be matched by stopping before any protocol event. A proof for arbitrary concurrent initialization, output extrusion, tables, and names is **not** supplied by this observation.

The lin worker is `in(st,x); in(c,y); (case1 | ... | casen)`. State tests occur inside those branches; mismatching states do not create tokens. `_case_block` places events before all public outputs and the private state output last. Tamarin prints St, optional In and !Thr premises, all events together, then the successor and all public outputs. These concrete ordering facts justify the audited scheduler shape under G; they do not justify unseen operational/Horn semantics.

The U fixture is generated and its reachability is checked, but this lemma does not silently cover U's unrolled parallel alternatives or rep's persistent outputs. It is a lin/base lemma only.

## 7. Counterexamples and guard gaps

### 7.1 Missing constructor-variable closure/hygiene: native separation

`capture.pv` and `capture.spthy` are generated without patching the backends. Fix initial q=0. Publish `(I,seal(n1))`. Change the first input to `('a',seal(x))`, retain event EvA(I), and retain no other update. In Tamarin, x is an independent rule variable: the attacker projects seal(n1), constructs `('a',seal(n1))`, binds x=n1, and reaches EvA. In ProVerif, `p_pattern` prints the whole constructor as equality `=seal(x)` rather than binding x; worker `x` is already q=n0. It consequently demands seal(n0), which is not deducible: seal is private, only seal(n1) was published, and its output seal(I) follows the unreachable event. Distinct n0,n1 and I cannot unify. Thus the generated PV event is unreachable, TM event reachable.

Existing `run` accepts this model with no FAIL. Native results: ProVerif `not event(EvA(I)) is true`; Tamarin `capture (exists-trace): verified`. Multiple initializations do not repair PV: every initial worker has n0 and publishes only seal(n1). This is not a memory-limit discrepancy and not an inference from matching Horn clause sets.

The `Z` variant instead has an undefined identifier: report still has no FAIL but ProVerif exits 2 (`Z not declared`). The standalone `unbound_guard` x mutant is parseable but also captures the internal binder; its verdict alone is not used as the separation proof. A proposed new guard should require closure at each equality subterm and reject backend-reserved identifier capture (or perform capture-avoiding binding). No production fix is applied.

### 7.2 Existing Det is necessary, and works here

Duplicate the q=0 input into two parallel case branches with different observed events EvA and EvDup. On one public dispatch the printed PV worker runs both branches; base TM can consume its single per-identity St only once. Native PV finds both for the same identity; TM falsifies their joint reachability. Existing Det rejects this mutant, so this is a validated **existing guard**, not a newly missing one. Multiple identities cannot satisfy the same-I query because Init identities are fresh.

### 7.3 Parseability is not certified by OK

A ground scalar input `'a'` prints `let =c_a = y`, rejected by ProVerif 2.05 (exit 2), even with no FAIL in the report. The final restricted fixture uses pair inputs and parses in both tools. An earlier fixture named an event F and hit a Tamarin formula parse error at F's application (exit 1); the final fixture uses EvA/EvB. These failed exploratory names/inputs do not establish security or successful correspondence. The final package retains a reproducible scalar negative control; the earlier F variant is recorded here, not counted as a final successful run. A text-parse guard and reserved-name validation are required beyond the current report.

## 8. Executed evidence and its limits

`results.json` is authoritative for commands, exit codes and result lines. `tests.log` contains 21 passing unittest checks: nine copied original guard regressions plus twelve independent audit tests. Expected parse failures are recorded as failures of those generated models, not successful protocol proofs. For the finite explorer fixture: A has 3 states/2 edges; P has 13 states/12 edges, including 3 abandoned states; each has 3 event words (empty, EvA, EvA·EvB). The explorer checks R for every reachable P configuration and exact stable representatives of every reachable A state. It uses the ground subterms of the fixture; it does not enumerate all attacker terms. Ground inputs make membership in its relevant-term projection sufficient here; the general lemma uses unbounded D, not this finite enumeration.

Native ProVerif 2.05 reports joint EvA/EvB reachable for lin and U. Native Tamarin 1.12.0 / Maude 3.5.1 verifies the fixture's exists-trace lemma, verifies the capture counterexample, and falsifies the overlapping-case same-identity joint query. These runs are smoke/negative controls, not proof of equality of full trace languages. Versions are observed executable versions, not a claim of pristine upstream builds. Tamarin reports a locally modified build in `--version`; the read-only Python sources are pinned by SHA-256, not by a discovered Git commit.

The old bounded result (19 atomic states, 251 concrete states, 61 with abandonment, 19 traces each) is preserved as input. Its model is hand-written, uses two threads, and gives the atomic side b but not c; it does not check the actual printer or solve semantic adequacy. It was read and not reclassified as a proof. The current counterexamples and generated fixtures are independent new evidence, not replacements for saved LM-OTS/LMS verdicts.

## 9. Difference from the manuscript hypothesis and open boundary

`sections/5_method.tex:94` expressly assumes “a reviewed process-to-rule simulation for the generated blocks.” Assuming that to prove the same correspondence would leave the desired work in the premises. Here G is a list of structural/term/scheduling conditions and A/P are explicitly given reductions. Equality of their finite observed languages is derived case by case without a process-to-rule-correctness premise. **But** the remaining bridge from complete native PV/TM semantics to A/P is not thereby proved. The word “restricted scheduler lemma” is essential, not cosmetic.

The insertion is additive. Keep all manuscript caveats, the reviewed-simulation premise, event-normalization/Horn-abstraction obligations and conditional transfer-dependent grades. Do not replace the proposed inclusion chain by this lemma. Still open: arbitrary input-variable patterns (known concrete counterexample), capture-avoiding naming, parse validation across generated models, general fresh allocation, attacker/structural-congruence adequacy, multiple threads/roles, interleaving responders, table-to-public initialization, leaks and reveal formulas, replicated state/Horn abstraction, U normalization, Clone/Rollback and knowledge-enabled rollback requests, and property-formula preservation. No full PV symbolic-semantics ↔ TM theorem is claimed.
