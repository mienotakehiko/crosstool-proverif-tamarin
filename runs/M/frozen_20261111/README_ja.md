# 前向き変異再評価 2026-11-11

## 達成と未達
- 採用案：既存10演算子×2種（lmots/lms_s2）の20変異を、新しい包括クエリで前向き再評価。
- 新規変異は0。whole100は未了、80件不足。条件変種5の水増しは実施しない。
- 計測込みの対照差：20/20。入力ガード監査を除くと18/20で差、unguarded_revealの2件は生存。
- PV：66回、231式、未判定0、全rc=0。1回上限15秒、逐次。
- TM：新規基準実行14回、判定13、未判定1。1式上限30秒、逐次。
- TM未判定：lms_s2/acceptreach、TIMEOUT、rc=-9。既存結果のreuseではないが変異TM再実行でもない。
- 8-class accuracyは未評価。gold causal labelと独立oracleなし。discrepancyをaccuracyと呼ばない。

## 実行前凍結
凍結時刻：2026-11-11T03:11:59.901321+00:00。freeze.json SHA-256：`951ca532cd49b670c440d9b67a5025504cce4917093ce1c3322777c427bc7a31`。
runner・元モデル・計測付き入力・全query・極性・判定基準・予算・tools hashを凍結した後に実行。
実行開始はexecution_started.json、終了はexecution_finished.json。
検査では全PVのQuery見出しとRESULT本文の順序・件数も照合した。
LMSの時刻付きquery見出しにはPV内部のencoded as展開が付くため、元の式部分を比較した。
集計初回はこの表示差で厳密一致検査が停止し、実行結果を変更せず検査側のみ修正した。
凍結に外部タイムスタンプ署名はなく、ローカルの順序記録である。

## 保全
既存audit_20261028およびcimc全7028ファイルを前後SHA-256比較し、変更・削除・追加0。
既存20変異結果と診断木v1.1は不変。
tree SHA-256：`d45347db969b78a5209adb13dbee3cc00b7d6047ec0c60a14d40be7cfc0de8e6`。
この処理が作るファイル・HOME/TMPDIR/cacheはすべて指定mutations配下。
凍結初回は大きな既存ログの一括ハッシュ読込みで実行基盤がChildProcess.killを返し、
検証実行前にストリーム読込みへ変更した。初回にfreezeや実験結果は生成されず、最終freeze後のrunner変更・実験再試行はない。

## 資源と証跡
PV RLIMIT_AS=800MiB、プロセス群RSS停止650MiB、TM heap=400MiB、1コア。
各runに実際のrc、停止理由、経過秒、1秒間隔RSS、rawout SHA-256を保存。
合計run経過時間：61.708秒、最大群RSS：377836KiB。
rawはstdout+stderr、タイムアウトとメモリ停止は分ける。未判定は反証でも成功でもない。

## ファイル
- freeze.json / freeze.sha256：実行前固定manifest
- prospective.py：凍結済み生成・実行スクリプト
- analyze.py：実行後検査と集計
- pv/：66入力、tm/：2入力
- raw/：80回分のraw.outとrun.json
- results.json / results.csv：全実行結果、PVの縦持ち表
- summary.json / mutation_assessment.json：件数・変異ごとの対照差
- query_coverage.json / query_coverage.md：式別網羅性
- survivors_analysis.md：生存8件の識別と限界
- protected_before.json / protected_after.json / invariance.json：既存不変検査
- artifacts.sha256：成果物ハッシュ一覧（自己自身と配布archiveを除く）

## 再現
同一環境では `python3 prospective.py freeze` → `python3 prospective.py run` → `python3 analyze.py`。
既存freeze・実行の上書き防止assertがあるので、本実行先に再実行しない。
別コピーで検証する場合は元のaudit_20261028/cimcを相対配置し、許可された別出力先を用意する。
元の成果物とfreezeは保存し、変更版は別実験とする。

## 解釈上の注意
本スイートは既知の変異と過去の生存者を見て設計したもので、盲検hold-outではない。
「prospective」は今回の新規クエリ判定を得る前に式・手順を固定した意味に限定する。
診断精度、統計的独立性、100件完了、非計測モデルの20/20検出は主張しない。
