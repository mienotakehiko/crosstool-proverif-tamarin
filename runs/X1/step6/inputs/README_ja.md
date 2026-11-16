# CCS26 Step 6 — 線形事実を読む行の区別

対象は Step 5 で残った `linear_pair` の差。保存済みの候補版モデルを `models/original/` に収録した。`models/distinct_ids/` は、そのファイルの2回目の取得に `suchthat (stL_St_1 <> stL_St)` を足したコピー。`rGood` と `rBad` の両方に同じ変更を適用し、クエリ、制約、イベントおよび初期データを維持した。確認用の差分は `diffs/` にある。

WSLのBashで、このディレクトリから次を実行する。

```bash
sha256sum -c SHA256SUMS &&
bash run-step6.sh
```

Step 5 と同じ固定イメージおよび ProVerif のハッシュを確認する。実行はProVerifの4回。各回の上限は60秒で、コンテナはネットワーク無効、1 CPU・2 GiB。対象モデルの生成とTamarinバイナリのビルドは既存の成果を使用する。

| 入力 | 補題 | 期待する生判定 | トレースで見る条件 |
|---|---|---|---|
| `original` | `good_reachable` | `not event(eGood) = false` | 2回の取得の後に実行。行IDの一致・不一致を記録 |
| `original` | `bad_reachable` | `not event(eBad) = false` | 同じ行IDを2回取得して実行 |
| `distinct_ids` | `good_reachable` | `not event(eGood) = false` | 異なる行IDを1回ずつ取得して実行 |
| `distinct_ids` | `bad_reachable` | `not event(eBad) = true` | `eBad` は到達不能 |

`stage=complete` と `rc=0` は4ケースの収録完了。`diagnosis=SUPPORTED` は、生判定と復元されたトレースの両方で表の条件がそろったことを示す。`REVIEW` は判定不能・実行エラー・トレース形式の不一致などで要確認。`UNEXPECTED` は判定または行IDの出方が事前期待と異なる場合。

出力の `ARCHIVE=` が指すファイルとそのSHA-256を共有する。アーカイブには `summary.tsv`、`decision.json`、入力モデル、差分、4ケースの標準出力・標準エラーと実行記録が入る。

配布前に、結果判定と行IDの抽出を実測ログおよび模擬出力で、アーカイブ作成を模擬Dockerで確認した。行ID条件を加えたモデルを固定ProVerifで実行するのは今回が初回。

構文の参照先は ProVerif 2.05 User Manual の表取得および不等号の節。 [ProVerif User Manual](https://bblanche.gitlabpages.inria.fr/proverif/manual.pdf)
