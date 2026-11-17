# cimc 0.1.2 コピー修正報告

## 修正方式

backendの全面的な束縛翻訳変更ではなく、**安全側の予約名・束縛検査による生成拒否**を実装した。未対応入力を対応済みと偽装しない。

- `cimc/validation.py` を追加。内部変数・channel・生成binder接頭辞などの衝突を拒否する `Hygiene`、入力等値項と本体の束縛を確認する `Binding`、既知の未対応scalar入力を拒否する `PatternSupported`。
- 等値パターン内の変数は、**入力パターン全体に入る前**から束縛済みでなければならない。同一tuple内の新規束縛や繰返し参照を等値項から利用する構成は未対応として拒否する。
- 両backendの全変種が共通gateを実行。CLIはgate失敗時に終了コード1、モデルも出力ディレクトリも作らない。直接APIでは `CimError`。
- 版番号は0.1.2。正当入力に対するprinter本体の出力規則は変更していない。
- `test_al.py` のimport時 `SystemExit: 0` だけを直接実行時に限定し、全探索が正常終了できるようにした。ALの37件の期待値・評価規則は不変。

## 最終検査

| 項目 | 結果 |
|---|---|
| 既存guard | 9/9成功 |
| AL単独実行 | 37/37成功 |
| 全unittest探索 | 22/22成功＝既存9＋新規13。ALの37 assertionもimport時に成功 |
| 保存済みAL回帰 | LM-OTS / LMS_S2ともSAME |
| seed生成モデル | 計16本、現行元0.1.1出力と版番号以外完全一致 |
| seed PV実行 | 8ファイル実行、保存期待値21/21一致。実際の全query行は28件 |
| seed TM | 全8変種読込み成功。baseの正常実行補題のみ各1件を選択しverified |
| 捕獲反例 | 両backend計8入口で拒否。CLIも拒否・出力なし |
| 元反例の実ツール再実行 | 古い生成物を変更せず、PV非到達／TM到達を再現 |
| 正当入力とalpha-renaming対照 | 束縛変数を出力に利用。生成テキストが名前変更以外一致、PV全4符号化とTM baseで同じ到達結果 |
| 原本・旧証拠 | 元cimc全ファイル、コピー内のout/tests/data、前回proof全体のハッシュ不変 |

`audit_0_1_2/results.json` は39件の逐次コマンドを記録する。意図したCLI拒否1件だけ終了コード1、残りは0。TMの `analysis incomplete` は未選択補題であって成功証明とは数えない。OOMやtimeoutを成功扱いしていない。子プロセスは仮想メモリ750MiB上限、TMは1コア・heap450MiB、個別期限付き。

## 初回失敗を隠さない

最初の正当入力対照案は、同一tupleの先頭で束縛した変数を後続の等値パターンが参照した。PVは `v_Payload not declared`、終了コード2。この実証を受けてguardを強化した。最初のログと結果JSONは `audit_0_1_2/initial_failed_attempt/` に保存し、最終成功ログと区別した。

予約名だけ変えてコンストラクタの自由変数を残したモデルも依然拒否される。**元反例について「alpha renameで意味を保存して修復した」とは主張しない。** 正当入力の対照試験は別モデルである。

## 成果物と再現

- `cimc/`：修正した0.1.2コード。全体copyには元のcims/tests/outも保持。
- `audit_0_1_2/fix.diff`：元ソースとの差分（新規検査とテスト探索修正を含む）。README差分は別途最終packagingで含める。
- `audit_0_1_2/original_before.json`, `original_after.json`：元全体のハッシュ照合。
- `audit_0_1_2/rejections.json`：8入口の拒否理由。
- `audit_0_1_2/seed_comparison.json`, `pv_expected_comparison.json`：出力・期待値照合。
- `audit_fix.py`：逐次再現。作業場所はこのcopy、出力先もcopy内のみ。
- `manuscript_correction_en.md`：原稿へ追加する英語修正文案。元原稿は不変。

このcopyで `PYTHONDONTWRITEBYTECODE=1 python -B audit_fix.py` を実行する。元の配置を読み取る再現スクリプトなので、別環境への移送時は先頭の読取りパスを明示的に調整する必要がある。

## 未実施・残る限界

完全なhygienic backend、全入力構文・命名の一般的な正当性証明、全Tamarin安全性補題の再証明、Docker比較は行っていない。予約名リストは保守的で、無害でも拒否する名前がある。一般化した対応定理やAL引上げは主張しない。新gateが通ることを全翻訳の安全証明とは扱わない。
