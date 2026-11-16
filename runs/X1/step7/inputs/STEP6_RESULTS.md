# Step 6 実測結果

提出アーカイブの SHA-256 は `9bf0efd338ec53e499e94821bd55f30b70ff05798ca3f9b602a4f6841bc14fd1`。内部マニフェストの43ファイルと内容が一致した。ProVerif の4実行は終了コード0・タイムアウトなしで、`MATCH=4`、`diagnosis=SUPPORTED`。

| 入力 | 補題 | 結果 | 復元トレースの取得行ID |
|---|---|---|---|
| Step 5候補版の生成PV | `good_reachable` | 到達可能 | `stR_St_5`、`stR_St_5` |
| Step 5候補版の生成PV | `bad_reachable` | 到達可能 | `stR_St_6`、`stR_St_6` |
| 2回目の取得に行IDの不等号を追加したPV | `good_reachable` | 到達可能 | `stR_St_5`、`stR_St_6` |
| 同上 | `bad_reachable` | 到達不能 | なし |

負例の `RESULT not event(eBad(...))` は `false` から `true` へ変化した。正例の `eGood` は、追加条件の下で2つの異なるテーブル行を取得するトレースを持つ。

合わせて確認できた範囲は `linear_pair` の一規則内の行再取得。Step 7 の生成器候補ではこの条件を自動生成し、読みが3回の場合、パターンと単純な取得が混在する場合、および永続事実からの取得を対象に小規模確認を行う。
