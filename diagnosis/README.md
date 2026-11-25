# Decision tree of the diagnosis procedure

The file [`v1.1/diagnose.py`](v1.1/diagnose.py) is decision tree 1.1, which assigns a cause to a disagreement or to a missing verdict. Its SHA-256 hash is `d45347db969b78a5209adb13dbee3cc00b7d6047ec0c60a14d40be7cfc0de8e6`. The generator versions 0.1.1, 0.1.2 and 0.1.3 ship the same file as `cimc/diagnose.py`, and the frozen run of series M and the predictions of series V3 record this hash.

Version 0.1.0 of the generator ships the earlier tree 1.0 as [`cimc/v0.1.0/cimc/diagnose.py`](../cimc/v0.1.0/cimc/diagnose.py).

Series V3 evaluates tree 1.1 against 41 sealed labels. The records and the commands are in [`validation/V3-diagnosis/`](../validation/V3-diagnosis/).
