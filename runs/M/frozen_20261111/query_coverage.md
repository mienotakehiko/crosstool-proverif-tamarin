# クエリ網羅性

YES/NOは到達可能性なら「到達する/しない」、安全性なら「成立/不成立」。PVの生のtrue/falseをそのまま到達性と解釈しない。
既存のexists-trace相当クエリも反例による到達性として極性反転する。
式の全文・事前の狙いはfreeze.jsonに記録。

| 種 | query | 種別 | 対照PV | 差のある変異数 | 新規TM基準 |
|---|---|---|---|---|---|
| lmots | acceptreach | reach | YES | 3 | YES |
| lmots | signreach | reach | YES | 1 | YES |
| lmots | revealreach | reach | YES | 1 | YES |
| lmots | seedreach | reach | YES | 1 | YES |
| lmots | seed_without_reveal | safety | YES | 1 | YES |
| lmots | reveal_guarded | safety | YES | 1 | YES |
| lmots | prf_public_probe | reach | NO | 1 | NO |
| lmots | exec_accept | reach | YES | 3 | NOT_RUN |
| lmots | LS1_unforge | safety | YES | 3 | NOT_RUN |
| lmots | forge | reach | NO | 3 | NOT_RUN |
| lms_s2 | acceptreach | reach | YES | 3 | UNDETERMINED |
| lms_s2 | signreach | reach | YES | 1 | YES |
| lms_s2 | revealreach | reach | YES | 1 | YES |
| lms_s2 | seedreach | reach | YES | 1 | YES |
| lms_s2 | seed_without_reveal | safety | YES | 1 | YES |
| lms_s2 | reveal_guarded | safety | YES | 1 | YES |
| lms_s2 | prf_public_probe | reach | NO | 1 | NO |
| lms_s2 | exec | reach | YES | 3 | NOT_RUN |
| lms_s2 | LS4_pure | safety | YES | 1 | NOT_RUN |
| lms_s2 | LS1 | safety | YES | 3 | NOT_RUN |
| lms_s2 | LS3_forge | reach | NO | 3 | NOT_RUN |

PV：LMOTS 10式×11モデル=110、LMS_S2 11式×11モデル=121、合計231判定。
新規7式×22モデル=154、既存式再実行77。モデルは変異20＋対照2。
未判定0。実行はモデルごとにreach/audit/existingの3群に分離し66回。
TM：新規7式×2基準モデル=14回、確定13・未判定1。既存安全性TMはNOT_RUN。
TMの一致は基準モデルに限り、PV変異のcross-tool検出数を意味しない。
