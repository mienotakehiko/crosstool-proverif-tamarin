# Achievement Levels for LMS_S2

cimc 0.1.0; diagnosis tree 1.1 (sha256 d45347db969b); side conditions: all OK; Theorem 1(e): applies, n = 2; parameters fixed (h = 1, w = 2, p = 2), scope P

## exec (phi3): AL-P4

| System | Scope | Outcome | Level | AL | Evidence | Basis |
|---|---|---|---|---|---|---|
| T | P | reachable | 4 Cross-validated | AL-P4 | U2:false, lin:false, base:verified | both tools |
| Trb | P_R | reachable | 4 Cross-validated | AL-P_R4 | U2:false, Urb2:false, lin:false, base:verified | both tools, via Theorem 1 |
| Tcl | P_C | reachable | 4 Cross-validated | AL-P_C4 | U2:false, lin:false, base:verified | both tools, via Theorem 1 |
| Tom | P_w | reachable | 4 Cross-validated | AL-P_w4 | U2:false, Urb2:false, lin:false, rep:false, base:verified | both tools |

Diagnosis:

- **TM-res** (provisional): LMS_S2_T_rb1; time limit; no memory curve recorded

## LS4_pure (phi2): AL-P4

| System | Scope | Outcome | Level | AL | Evidence | Basis |
|---|---|---|---|---|---|---|
| T | P | holds | 4 Cross-validated | AL-P4 | U2:true, base:verified | both tools |
| Trb | P_R | attack | 4 Cross-validated | AL-P_R4^a | Urb2:false, rb1:falsified | both tools |
| Tcl | P_C | - | 0 Inconclusive | AL-P_C0 | - | no outcome |
| Tom | P_w | attack | 4 Cross-validated | AL-P_w4^a | Urb2:false, rep:false, rb1:falsified | both tools |

Diagnosis:

- **ENC-clone**: LMS_S2_PV_U2, LMS_S2_T_base, LMS_S2_PV_Urb2, LMS_S2_PV_rep, LMS_S2_T_rb1; holds on U2 (Tle), base (T); fails on Urb2 (Trb), rep (Tom), rb1 (Trb): the difference is the reuse of a state value
- **PV-abs**: LMS_S2_PV_lin; the property holds on this model (from U2, base): false alarm
- **TM-res** (provisional): LMS_S2_T_cl1; time limit; no memory curve recorded

## LS4 (phi2): AL-P4

| System | Scope | Outcome | Level | AL | Evidence | Basis |
|---|---|---|---|---|---|---|
| T | P | holds | 4 Cross-validated | AL-P4 | U2:true, base:verified | both tools |
| Trb | P_R | holds | 1 Single-model | AL-P_R1 | rb1:verified | one tool |
| Tcl | P_C | - | 0 Inconclusive | AL-P_C0 | - | no outcome |
| Tom | P_w | attack | 1 Single-model | AL-P_w1^a | Urb2:false, rep:false | one tool |

Diagnosis:

- **ENC-clone**: LMS_S2_PV_U2, LMS_S2_T_base, LMS_S2_PV_rep; holds on U2 (Tle), base (T); fails on rep (Tom): the difference is the reuse of a state value
- **PV-abs**: LMS_S2_PV_lin; the property holds on this model (from U2, base): false alarm
- **TM-res** (provisional): LMS_S2_T_cl1; time limit; no memory curve recorded

## LS1 (phi1): AL-P4

| System | Scope | Outcome | Level | AL | Evidence | Basis |
|---|---|---|---|---|---|---|
| T | P | holds | 4 Cross-validated | AL-P4 | U2:true, base:verified | both tools |
| Trb | P_R | attack | 4 Cross-validated | AL-P_R4^a | Urb2:false, rb1:falsified | both tools |
| Tcl | P_C | - | 0 Inconclusive | AL-P_C0 | - | no outcome |
| Tom | P_w | attack | 4 Cross-validated | AL-P_w4^a | Urb2:false, rep:false, rb1:falsified | both tools |

Diagnosis:

- **ENC-clone**: LMS_S2_PV_U2, LMS_S2_T_base, LMS_S2_PV_Urb2, LMS_S2_PV_rep, LMS_S2_T_rb1; holds on U2 (Tle), base (T); fails on Urb2 (Trb), rep (Tom), rb1 (Trb): the difference is the reuse of a state value
- **PV-abs**: LMS_S2_PV_lin; the property holds on this model (from U2, base): false alarm
- **TM-res** (provisional): LMS_S2_T_cl1; forced termination; exit code alone does not distinguish timeout escalation from OOM

## LS3_forge (phi3): AL-P4

| System | Scope | Outcome | Level | AL | Evidence | Basis |
|---|---|---|---|---|---|---|
| T | P | unreachable | 4 Cross-validated | AL-P4 | U2:true, base:falsified | both tools |
| Trb | P_R | reachable | 4 Cross-validated | AL-P_R4 | Urb2:false, rb1:verified | both tools |
| Tcl | P_C | reachable | 1 Single-model | AL-P_C1 | cl1:verified | one tool |
| Tom | P_w | reachable | 4 Cross-validated | AL-P_w4 | Urb2:false, rep:false, rb1:verified, cl1:verified | both tools |

Diagnosis:

- **ENC-clone**: LMS_S2_PV_U2, LMS_S2_T_base, LMS_S2_PV_Urb2, LMS_S2_PV_rep, LMS_S2_T_cl1, LMS_S2_T_rb1; holds on U2 (Tle), base (T); fails on Urb2 (Trb), rep (Tom), cl1 (Tcl), rb1 (Trb): the difference is the reuse of a state value
- **PV-abs**: LMS_S2_PV_lin; the property holds on this model (from U2, base): false alarm

