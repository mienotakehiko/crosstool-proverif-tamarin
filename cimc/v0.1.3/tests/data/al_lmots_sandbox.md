# Achievement Levels for LMOTS

cimc 0.1.0; diagnosis tree 1.1 (sha256 d45347db969b); side conditions: all OK; Theorem 1(e): applies, n = 1; parameters fixed (w = 2, p = 2), scope P

## exec_accept (phi3): AL-P4

| System | Scope | Outcome | Level | AL | Evidence | Basis |
|---|---|---|---|---|---|---|
| T | P | reachable | 4 Cross-validated | AL-P4 | U1:false, lin:false, base:verified | both tools |
| Trb | P_R | reachable | 4 Cross-validated | AL-P_R4 | U1:false, Urb1:false, lin:false, base:verified, rb1:verified | both tools |
| Tcl | P_C | reachable | 4 Cross-validated | AL-P_C4 | U1:false, lin:false, base:verified, cl1:verified | both tools |
| Tom | P_w | reachable | 4 Cross-validated | AL-P_w4 | U1:false, Urb1:false, lin:false, rep:false, base:verified, rb1:verified, cl1:verified | both tools |

## LS1_unforge (phi1): AL-P4

| System | Scope | Outcome | Level | AL | Evidence | Basis |
|---|---|---|---|---|---|---|
| T | P | holds | 4 Cross-validated | AL-P4 | U1:true, base:verified | both tools |
| Trb | P_R | attack | 1 Single-model | AL-P_R1^a | rb1:falsified | one tool |
| Tcl | P_C | attack | 1 Single-model | AL-P_C1^a | cl1:falsified | one tool |
| Tom | P_w | attack | 4 Cross-validated | AL-P_w4^a | rep:false, rb1:falsified, cl1:falsified | both tools |

Diagnosis:

- **ENC-clone**: LMOTS_PV_U1, LMOTS_T_base, LMOTS_PV_rep, LMOTS_T_cl1, LMOTS_T_rb1; holds on U1 (Tle), base (T); fails on rep (Tom), cl1 (Tcl), rb1 (Trb): the difference is the reuse of a state value
- **PV-abs**: LMOTS_PV_lin; the property holds on this model (from U1, base): false alarm

## forge (phi3): AL-P4

| System | Scope | Outcome | Level | AL | Evidence | Basis |
|---|---|---|---|---|---|---|
| T | P | unreachable | 4 Cross-validated | AL-P4 | U1:true, base:falsified | both tools |
| Trb | P_R | reachable | 1 Single-model | AL-P_R1 | rb1:verified | one tool |
| Tcl | P_C | reachable | 1 Single-model | AL-P_C1 | cl1:verified | one tool |
| Tom | P_w | reachable | 4 Cross-validated | AL-P_w4 | rep:false, rb1:verified, cl1:verified | both tools |

Diagnosis:

- **ENC-clone**: LMOTS_PV_U1, LMOTS_T_base, LMOTS_PV_rep, LMOTS_T_cl1, LMOTS_T_rb1; holds on U1 (Tle), base (T); fails on rep (Tom), cl1 (Tcl), rb1 (Trb): the difference is the reuse of a state value
- **PV-abs**: LMOTS_PV_lin; the property holds on this model (from U1, base): false alarm

