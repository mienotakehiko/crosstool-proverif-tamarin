# Mutation series M

| Cohort | Cases | Recorded outcome |
| --- | --- | --- |
| [October 28 pilot](historical/oct28/pilot/) | Three mutations and one unchanged control | 2/3 detected, 0/1 control disagreements |
| [October 29 main experiment](historical/oct29/mutation_extension_20261029/) | Ten operators on each of two signer seeds, two unchanged controls | 12/20 detected after shared-reference completion, 0/2 control disagreements |
| [November 11 frozen-query re-evaluation](frozen_20261111/) | The same 20 known mutants with fixed additional observations | 20/20 with audit observations, 18/20 with ordinary observations only |

October 29 `results.json` preserves the 11 original LMS Tamarin timeouts. The separate `results_completed_reference.json` uses one shared 30-second reference whose Tamarin input has the same SHA-256 for those 11 cases. The auxiliary unpublished-identity case has its own record outside the 20-mutant and two-control counts.

November 11 records 66 ProVerif invocations (231 formulas) and 14 Tamarin invocations. `freeze.json` and the recorded times establish the order within the local archive. The follow-up reuses known inputs and measures a wider set of observations. The counts describe their own cohorts.

Run `python3 -B scripts/verify_recovery_20261117.py` at the root to check the records and source hashes. The historical scripts record their original inputs and working-directory conventions. The release checker verifies the redacted public copies against the [source ledger](../../registry/recovered-files.tsv) and relates those hashes to the original log and manifest digests.
