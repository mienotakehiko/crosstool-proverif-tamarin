# LMS and HSS application

The [application export table](lms_hss_application_cndk8z5k/results/comparison.tsv) lists the ten LMS/HSS model–lemma pairs exported by both B0 and B2. Its statuses are translation results. The separate legacy LMS and HSS pilot directories hold the available ProVerif decisions. For legacy LMS, the B0/B2 pilot ran `exec` and `LS1`. The application package records other exports without a corresponding B2 proof run.

The [candidate assumption matrix](hss-candidate-comparison.tsv) aligns the four HSS premise combinations with the archived ProVerif inputs and statuses. The [full HSS table](hss-assumptions.tsv) retains individual archived result lines and includes the native results.

The [native DgInj runs](hss_native_dginj/) verify `exec` and `LS7` in 14 and 408 steps. The [translation comparison](hss_model_link/comparison.tsv) binds each native model export to the corresponding DgInj-only ProVerif input. Under those premises the negated `exec` query returns false with a reachability witness, and `LS7` returns true. A timed-out assumption combination supplies no logical verdict for that run.
