# Step 5 追加対照の実測結果

提出アーカイブの SHA-256 は
`2457476b4a63a0f6ecbec30175561f6737e61cacaa06665567d162f1e8746683`。
内部のマニフェストと296ファイルを照合し、全48工程で終了コード0・タイムアウトなしを確認した。

| モデル | 補題数 | 未修正版 | 候補版 |
|---|---:|---|---|
| `session_join` | 2 | 2一致・0差 | 2一致・0差 |
| `linear_pair` | 2 | 1一致・1差 | 1一致・1差 |
| `name_constructor` | 4 | 3一致・1差 | 4一致・0差 |
| 計 | 8 | 6一致・2差 | 7一致・1差 |

両版とも `REVIEW` は0件。候補版では、`name_constructor/bad_ctor_reachable` の取得が等値照合になり、翻訳後も到達不能になった。Step 4 の52補題の集計と Step 5 の8補題の集計は、それぞれの診断集合として扱う。

## 線形事実の多重度

Tamarin 原モデル `linear_pair.spthy` では、1個だけ存在する `St(sid,'one',z)` に対し、`Bad` 規則が同一内容の線形事実を2個要求する。直接検証では `Bad` は到達不能だった。

Step 5 アーカイブ内の候補版の `candidate/multiplicity/linear_pair/bad_reachable/translated.pv` では、70–71行で2回取得する。2回目はセッションと値を照合するが、行IDは新しい変数に束縛する。37–40行の `DistinctFact` 制約は同一の事実について規則IDの一致を要求する。実トレースでは1回の `rBad` 実行内なので2つのイベントの規則IDがすでに同じであり、制約を満たしたまま同一行を2回取得できる。

`candidate/multiplicity/linear_pair/bad_reachable/pv.stdout.txt` の107・109行は同じ `stR_St_6`、117行は `eBad` の実行、120–121行はトレース成立と `RESULT … is false.` を記録している。正例の `candidate/multiplicity/linear_pair/good_reachable/pv.stdout.txt` の107・109行も同じ行ID `stR_St_5` を読んでいた。

Step 6 では、候補版の保存済み `.pv` を使い、2回目の取得で先の行IDを除く条件の有無だけを変えて比較する。これによりこのモデルの一規則内の重複読取りについて検証する。複数回の規則適用や一般の線形消費はそれぞれ別条件である。
