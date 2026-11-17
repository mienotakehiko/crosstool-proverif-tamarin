# GitHub公開候補の審査記録（2026-11-17）

**技術検査済みの公開候補。公開確定は権利確認後。** 受領ZIPを基準に、回収した実験原本・コード、検証スクリプト、来歴表を追加した。READMEと[論文対応表](PAPER_MAPPING.md)を更新した。GitHub上のブランチは変更していない。

| 審査対象 | 判定 | 確認結果・残件 |
| --- | --- | --- |
| 研究結果 | 一致 | 受領版と統合版で再計算した61項目の値・項目名・期待値が全行一致し、不一致0件。拡張チェックを含む89項目も不一致0件。[61項目の照合表](../registry/paper_baseline_20261117.tsv) |
| 歴史的M | 確認済み | 10月28日パイロットは2/3。10月29日の主試験は12/20、対照0/2。原記録のLMS側11件の時間打切りを保存し、同じモデルハッシュの30秒参照結果を補った集計を別ファイルに収録した。11月11日の凍結クエリによる再評価は監査用観測込み20/20、通常観測のみ18/20。[系列Mの記録](../runs/M/) |
| Lemma 1 | 限定範囲で確認済み | 保存ログの21件が成功。単一初期化スレッドの接地フィクスチャを扱うPythonテストを再実行し、21件成功・失敗0・エラー0を確認した。意味論の一般的同値性、分岐双模倣、ライブネスはこのテストの範囲外。[テストと対象範囲](../scheduler/) |
| U7 | 確認済み | P5の225ジョブ×5試行は1,125件（verified 965、falsified 160）。U7 G4のメモリ梯子は別の9件で、すべてHEAP、終了コード251。過去の56 GiB参照点およびAWS 96 GiBの7件も別扱い。P5の判定記録と計測補助ファイルを収録し、全試行の標準出力アーカイブは未収録。[P5](../runs/P5/)・[梯子](../runs/L/ladder/) |
| Diagnosis | 未回収を明記 | v1.1のソースは回収し、凍結記録のSHA-256と一致。**歴史的な24テストの実行原本は未回収**。[Diagnosis](../diagnosis/) |
| G本番 | 未回収を明記 | **本番Tamarinの32判定、対応JSONL、出力一式は未回収**。既存のサンドボックス記録とProVerifの直接検証28判定を保持する。U7 G4はメモリ梯子の系列に属する。[系列目録](../registry/series_map.tsv) |
| X1 | 内容・来歴確認済み、原本の公開権限は保留 | Step 3〜8の原本6件のSHA-256が一致。全3,375ファイルメンバーを確認。Step 4〜8の内部ハッシュ計3,351件を照合し、Step 3の19件はアーカイブとファイル来歴表を照合した。Step 4内のStep 3の重複アーカイブも一致。原本にはローカルパスが残るため、確認済みの展開データと来歴表を掲載候補にした。原本アーカイブ一式の再配布には権限確認が必要。[内容・ハッシュ・権限の目録](../registry/x1_archive_review.tsv)・[原本の検査集計](../registry/x1_original_metadata_scan.tsv) |
| 個人情報 | 公開用写しを確認済み | ローカルユーザー名を含むパス、マシン名、READMEの直接連絡先を公開用コピーから除去した。原文のハッシュと整形後のハッシュを併記する。著者表示、公開GitHubの識別子、上流の著作権表示を保持した。[除去箇所の目録](../registry/privacy_redactions.tsv) |
| 秘密情報 | 検査範囲内で検出0件 | 配布対象を列挙し、APIキー・アクセストークン・Authorization値・秘密鍵・認証設定ファイル名と非テキストファイルを静的検査した。結果の範囲は収録ファイルと検出パターンに限る。入れ子の配布アーカイブと生成PDFは公開用から外した。[検査コード](../scripts/audit_release_metadata.py)・[除外目録](../registry/release_exclusions.tsv) |
| 第三者コード | 出典・条件を確認、権利者確認は保留 | Tamarin派生コードのGPL v3本文、原著作権表示と改変日を収録。Morioらの評価データにCC0本文とDOIを添付。外部KUDOSモデルは取得手順と入力ハッシュを示した。原本アーカイブ全体と著者側のコード・データに適用する公開条件は権利者確認待ち。[第三者資料の出典と条件](THIRD_PARTY_NOTICES.md) |

## 再点検コマンド

リポジトリのルートで実行する。集計と保存証跡の確認はプローバーを起動しない。

```bash
python3 -B scripts/update_manifest.py --check
python3 -B scripts/verify_evidence.py
python3 -B scripts/recompute_paper_numbers.py --baseline-only
python3 -B scripts/verify_recovery_20261117.py
python3 -B scripts/check_x1_archives.py
python3 -B scripts/audit_release_metadata.py --findings
python3 -B scheduler/restricted_20261111/run_checks.py
```

X1原本の保管場所が分かる場合は、`python3 -B scripts/check_x1_archives.py --originals /path/to/evidence` で6件を再照合できる。原本の保存場所は公開データに含めない。

## 原本と公開版の対応

[回収ファイル目録](../registry/recovered-files.tsv) は、原アーカイブ名、内部ファイル名、原本・公開版のSHA-256を記録する。パスなどを整形したログは公開版のハッシュで検査し、当時の凍結記録が参照するSHA-256は原本の列で照合する。歴史的チェックサムが参照する配布ZIP2件は未入手で、その状態を[原マニフェストの検査表](../registry/reviewed_source_manifests.tsv)に残した。新規のProVerif・Tamarin計測は実施していない。
