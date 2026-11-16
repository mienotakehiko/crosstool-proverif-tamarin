# CCS26 Step 8 — 既存60補題の回帰試験

Step 7 の候補バイナリを使い、保存済みの Step 4 の52補題と Step 5 の8補題を再実行する。各補題について、Tamarinでの直接検証、PVへの翻訳、ProVerifでの検証を行う。固定イメージと工具のハッシュを照合し、各コマンドは60秒、コンテナは1 CPU・2 GiB、ネットワーク無効。実行対象は Step 7 でビルドしたバイナリ。

## 実行

WSL の Bash で本ディレクトリに移動し、次を実行する。バイナリを移動した場合は、その現在位置を指定する。

```bash
CCS7_RUN="$HOME/ccs26-step7.tdZAlLvE/ccs26_step7_20261115/step7-run.yk9OYiFV"
CCS7_BINARY="$CCS7_RUN/binaries/candidate/tamarin-prover"

sha256sum -c SHA256SUMS &&
bash run-step8.sh "$CCS7_BINARY"
```

## 事前に定めた照合条件

| 対象 | 件数 | 判定基準 |
|---|---:|---|
| Step 4 の全補題 | 52 | 直接検証とPVの判定を維持。生成PVが従来の候補版と一致 |
| Step 5 の `linear_pair` 以外 | 6 | 同上 |
| `linear_pair/good_reachable` | 1 | 到達可能を維持。新しいPVが Step 7 の実測生成物と一致し、復元トレースで異なる2行を取得 |
| `linear_pair/bad_reachable` | 1 | 直接検証は到達不能を維持。PVも到達不能になり、新しいPVが Step 7 の実測生成物と一致 |

比較する生成PVは空白と末尾のビルド情報を正規化する。参照元アーカイブの SHA-256 は `reference/source-archives.json`、証跡内の位置は `cases.json` に記録した。

合格時は `decision=PASS`、`MATCH=60`、`preserved=59`、`repaired=1`、`changed_pv=2`、`stage=complete`、`rc=0`。判定の差は `DIFFERENT`、判定不能や生成ファイルの不一致は `REVIEW` として `summary.tsv` に記録する。

終了時の `ARCHIVE=` が指すファイルに集計、差分、生成モデルおよび原ログが入る。アーカイブとそのSHA-256を共有する。

配布前に、過去の実測アーカイブからの入力と参照結果の抽出、判定処理およびアーカイブ作成を確認した。60補題を新しいバイナリで再実行した実測結果は、本キットで取得する。
