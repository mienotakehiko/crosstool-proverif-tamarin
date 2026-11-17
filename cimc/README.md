# CIM compiler releases

- [0.1.0](v0.1.0/) produced the archived baseline fixtures in [models/generated](../models/generated/).
- [0.1.1](v0.1.1/) is the recovered October code with the earlier guard suite and Diagnosis v1.1. Generate outputs from its own `cims/` directory in a separate destination.
- [0.1.2](v0.1.2/) adds conservative hygiene and binding checks. The supplied files include the stored 9 guard checks, 13 new hygiene checks, 37 AL assertions and audit evidence. The [scheduler fixtures](../scheduler/restricted_20261111/) contain the capture and scalar-pattern controls. The [historical M auxiliary case](../runs/M/historical/oct29/mutation_extension_20261029/unpublished_identity/) records the unpublished-identity check.

Run the compiler unit suites independently of the provers:

```bash
(cd cimc/v0.1.1 && python3 -B tests/test_correspondence_guards.py)
(
  cd cimc/v0.1.2 &&
  python3 -B tests/test_correspondence_guards.py &&
  python3 -B tests/test_hygiene.py &&
  python3 -B tests/test_al.py
)
```

The version 0.1.2 full audit script records its original layout. The original read-only input locations and dependencies are needed to recreate that session. Use the commands above for the standalone Python tests, and the release verifier for the recorded evidence. The stored seed Tamarin rows are sandbox data. The separate 32-verdict G production run remains unrecovered.
