#!/usr/bin/env python3
"""Post-run audit only; never alters the freeze or runner."""
import sys, json, csv, io, collections, tarfile
from pathlib import Path
sys.dont_write_bytecode=True
from prospective import OUT, ROOT, OPS, SEEDS, digest, dump, write, inventory, now

m=json.loads((OUT/'freeze.json').read_text())
rows=json.loads((OUT/'results.json').read_text())
assert digest(OUT/'freeze.json')==(OUT/'freeze.sha256').read_text().split()[0]
assert digest(OUT/'prospective.py')==m['runner_sha256']
for rel,h in m['files'].items(): assert digest(OUT/rel)==h
assert all(digest(OUT/r['run']['raw_file'])==r['run']['raw_sha256'] for r in rows)
before=json.loads((OUT/'protected_before.json').read_text()); after=inventory()
changes=[p for p,h in before.items() if after.get(p)!=h]
added=sorted(set(after)-set(before))
dump(OUT/'protected_after.json',after)
dump(OUT/'invariance.json',dict(timestamp=now(),protected_roots=['audit_20261028','cimc'],protected_files=len(before),changed_or_deleted=changes,added=added,unchanged=not changes and not added,tree_version=m['tree_version'],tree_sha256=m['tree_sha256'],freeze_sha256=digest(OUT/'freeze.json')))
assert not changes and not added
pv={}; tm={}
for r in rows:
    qs=r['results']
    text=(OUT/r['run']['raw_file']).read_text()
    if r['tool']=='PV':
        # Verify complete ordered query headings against RESULTs, not just total rows.
        import re
        headings=re.findall(r'^-- Query (.*?) in process \d+\.$',text,re.M)
        results=re.findall(r'^RESULT (.*?) (is true|is false|cannot be proved)\.$',text,re.M)
        assert len(headings)==len(results)==len(qs),(r['seed'],r['operator'],r['group'])
        # Timestamp queries print an additional internal "encoded as" expansion
        # in the heading only. Compare the original formula, not that expansion.
        assert [h.split(' encoded as ',1)[0] for h in headings]==[v[0] for v in results],(r['seed'],r['operator'],r['group'],'order')
        for q in qs: pv[r['seed'],r['operator'],q['query']]=q['normalized']
    else:
        for q in qs: tm[r['seed'],q['query']]=q['normalized']
mutants=[]
for seed in SEEDS:
    for op in OPS:
        different=[]; unknown=[]
        for q in m['queries'][seed]:
            a=pv[seed,'control',q['name']]; b=pv[seed,op,q['name']]
            if 'UNDETERMINED' in [a,b]: unknown.append(q['name'])
            elif a!=b: different.append(q['name'])
        ordinary=[n for n in different if n!='reveal_guarded']
        mutants.append(dict(seed=seed,operator=op,different_queries=different,ordinary_different_queries=ordinary,
          detected=bool(different),input_guard_instrumentation_only=bool(different) and not ordinary,undetermined_queries=unknown,
          classification='detected' if different else 'undetermined' if unknown else 'survivor_not_proven_equivalent'))
dump(OUT/'mutation_assessment.json',mutants)
coverage=[]
for seed in SEEDS:
    for q in m['queries'][seed]:
        detections=[x['operator'] for x in mutants if x['seed']==seed and q['name'] in x['different_queries']]
        coverage.append(dict(seed=seed,query=q['name'],group=q['group'],kind=q['kind'],control=pv[seed,'control',q['name']],
          mutant_definite_count=sum(pv[seed,op,q['name']]!='UNDETERMINED' for op in OPS),mutant_undetermined_count=sum(pv[seed,op,q['name']]=='UNDETERMINED' for op in OPS),detected_operators=detections,
          tm_baseline=tm.get((seed,q['name']),'NOT_RUN'),tm_comparison='NOT_RUN' if (seed,q['name']) not in tm else 'UNDETERMINED' if tm[seed,q['name']]=='UNDETERMINED' else 'AGREE' if tm[seed,q['name']]==pv[seed,'control',q['name']] else 'DISAGREE'))
dump(OUT/'query_coverage.json',coverage)
buf=io.StringIO();w=csv.writer(buf);w.writerow(['seed','operator','query','kind','PV_normalized','PV_raw_verdict','rc','stop_reason','elapsed_s','raw_file','raw_sha256'])
for r in rows:
    if r['tool']!='PV': continue
    for q in r['results']:
        run=r['run'];w.writerow([r['seed'],r['operator'],q['query'],q['kind'],q['normalized'],q['raw_verdict'],run['rc'],run['stop_reason'],run['elapsed_s'],run['raw_file'],run['raw_sha256']])
write(OUT/'results.csv',buf.getvalue())
summary=dict(timestamp=now(),existing_mutants_reevaluated=20,new_mutants_created=0,controls=2,unique_original_canonical_hashes=20,
  target_100_completed=False,shortfall_to_100=80,statistical_independence_proven=False,
  detected_instrumented=sum(x['detected'] for x in mutants),detected_without_guard_query=sum(bool(x['ordinary_different_queries']) for x in mutants),guard_instrumentation_only=sum(x['input_guard_instrumentation_only'] for x in mutants),
  remaining_survivors=[x for x in mutants if not x['detected']],
  pv_runs=sum(r['tool']=='PV' for r in rows),pv_query_outcomes=sum(len(r['results']) for r in rows if r['tool']=='PV'),pv_undetermined=sum(q['normalized']=='UNDETERMINED' for r in rows if r['tool']=='PV' for q in r['results']),
  tm_runs=sum(r['tool']=='TM' for r in rows),tm_definite=sum(q['normalized']!='UNDETERMINED' for r in rows if r['tool']=='TM' for q in r['results']),tm_undetermined=sum(q['normalized']=='UNDETERMINED' for r in rows if r['tool']=='TM' for q in r['results']),
  tm_mutant_runs=0,tm_existing_safety_reruns=0,tm_reference_reused=False,eight_class_accuracy=None,gold_causal_labels=False,independent_diagnostic_oracle=False,
  run_elapsed_sum_s=round(sum(r['run']['elapsed_s'] for r in rows),3),peak_group_rss_kib=max(r['run']['peak_group_rss_kib'] for r in rows),
  freeze_sha256=digest(OUT/'freeze.json'),tree_sha256=m['tree_sha256'],protected_files_unchanged=len(before))
dump(OUT/'summary.json',summary)
table='\n'.join('| '+x['seed']+' | '+x['operator']+' | '+', '.join(x['different_queries'])+' |' for x in mutants)
write(OUT/'survivors_analysis.md',f'''# 生存変異の前向き再評価

## 結論と定義
既存20変異を新規凍結クエリで再評価した。対照PVと変異PVの確定判定が異なる場合だけ「検出」とした。
計測付きモデルで20/20に差があるが、2件は入力ガード監査だけによる検出である。
これは20件の診断正解率でも100件評価でもない。無差分を意味的同値とは判定しない。

| 種 | 演算子 | 対照と異なったクエリ |
|---|---|---|
{table}

## 従来の生存8件
- `remove_reveal_event`：両種で revealreach が YES→NO、seed_without_reveal が YES→NO。
  秘密出力自体は残り seedreach は YES。イベント消去と秘密出力消去を区別する。
- `unguarded_reveal`：両種で reveal_guarded のみ YES→NO。到達可能性・既存安全性・秘密到達は対照と同じ。
  監査イベント AuditGuard は実際の in(c,=I) の直後にだけ挿入した。
  公開Iは対照でも攻撃者が入力できるので、この検出を通常トレースの安全性悪化・非同値証明と呼ばない。
  監査を除けば2件は本クエリ集合で生存する。追加イベントを観測可能にした入力因果性の検出である。
- `private_to_public`：両種で prf_public_probe が NO→YES。
  公開入力 n0 に対する prf の構成可能性を測る。秘密sdの漏洩・偽造成功を意味しない。
- `reveal_wrong_secret`：両種で seedreach が YES→NO。RevealSeed の到達自体は YES。
  実際の新鮮秘密sdと識別子Iの取り違えを区別する。

## 診断妥当性の限界
演算子名は出所ラベルであり、診断8クラスのgold causal labelではない。
独立oracle・クラス別正解ラベルがないため、accuracy・precision・recall・混同行列は作成しない。
診断木v1.1は読取りハッシュのみで、診断木を実行していない。古いIR checksを変異出力の妥当性証拠には使わない。

## TMとの関係
新規TM実行は計測付き基準モデルのみ。既存の秘密漏洩規則に公開Iの要求入力とPendingReveal中間段階を追加した。
AuditSeedは初期化アクション、AuditGuardは要求入力段階のアクションで、PV監査式に対応する7式を追加した。
公開Iの要求段階追加による到達性保存は設計上の意図であり、一般的双模倣の形式証明はしていない。
14式中13式がPV対照と一致。lms_s2 acceptreach は30秒TIMEOUTで未判定。
既存TM参照結果は独立再実行に数えていない。変異20件のTM・既存安全性のTM再実行もしていない。

## 独立性と未了
元モデルの完全SHA-256およびコメント・空白除去後ハッシュが20件すべて異なることを確認した。
パラメータ名だけを変えた条件変種は作成していない。相異なるハッシュだけでは意味的独立性は証明できない。
例えば disable_accept と wrong_public_key は本クエリの判定指紋が同じになる。
100件計画は未了、20件再評価・80件不足。新規独立変異生成は0件。
''')
ct='\n'.join('| '+c['seed']+' | '+c['query']+' | '+c['kind']+' | '+c['control']+' | '+str(len(c['detected_operators']))+' | '+c['tm_baseline']+' |' for c in coverage)
write(OUT/'query_coverage.md',f'''# クエリ網羅性

YES/NOは到達可能性なら「到達する/しない」、安全性なら「成立/不成立」。PVの生のtrue/falseをそのまま到達性と解釈しない。
既存のexists-trace相当クエリも反例による到達性として極性反転する。
式の全文・事前の狙いはfreeze.jsonに記録。

| 種 | query | 種別 | 対照PV | 差のある変異数 | 新規TM基準 |
|---|---|---|---|---|---|
{ct}

PV：LMOTS 10式×11モデル=110、LMS_S2 11式×11モデル=121、合計231判定。
新規7式×22モデル=154、既存式再実行77。モデルは変異20＋対照2。
未判定0。実行はモデルごとにreach/audit/existingの3群に分離し66回。
TM：新規7式×2基準モデル=14回、確定13・未判定1。既存安全性TMはNOT_RUN。
TMの一致は基準モデルに限り、PV変異のcross-tool検出数を意味しない。
''')
write(OUT/'README_ja.md',f'''# 前向き変異再評価 2026-11-11

## 達成と未達
- 採用案：既存10演算子×2種（lmots/lms_s2）の20変異を、新しい包括クエリで前向き再評価。
- 新規変異は0。whole100は未了、80件不足。条件変種5の水増しは実施しない。
- 計測込みの対照差：20/20。入力ガード監査を除くと18/20で差、unguarded_revealの2件は生存。
- PV：66回、231式、未判定0、全rc=0。1回上限15秒、逐次。
- TM：新規基準実行14回、判定13、未判定1。1式上限30秒、逐次。
- TM未判定：lms_s2/acceptreach、TIMEOUT、rc=-9。既存結果のreuseではないが変異TM再実行でもない。
- 8-class accuracyは未評価。gold causal labelと独立oracleなし。discrepancyをaccuracyと呼ばない。

## 実行前凍結
凍結時刻：{m['timestamp']}。freeze.json SHA-256：`{digest(OUT/'freeze.json')}`。
runner・元モデル・計測付き入力・全query・極性・判定基準・予算・tools hashを凍結した後に実行。
実行開始はexecution_started.json、終了はexecution_finished.json。
検査では全PVのQuery見出しとRESULT本文の順序・件数も照合した。
LMSの時刻付きquery見出しにはPV内部のencoded as展開が付くため、元の式部分を比較した。
集計初回はこの表示差で厳密一致検査が停止し、実行結果を変更せず検査側のみ修正した。
凍結に外部タイムスタンプ署名はなく、ローカルの順序記録である。

## 保全
既存audit_20261028およびcimc全{len(before)}ファイルを前後SHA-256比較し、変更・削除・追加0。
既存20変異結果と診断木v1.1は不変。
tree SHA-256：`{m['tree_sha256']}`。
この処理が作るファイル・HOME/TMPDIR/cacheはすべて指定mutations配下。
凍結初回は大きな既存ログの一括ハッシュ読込みで実行基盤がChildProcess.killを返し、
検証実行前にストリーム読込みへ変更した。初回にfreezeや実験結果は生成されず、最終freeze後のrunner変更・実験再試行はない。

## 資源と証跡
PV RLIMIT_AS=800MiB、プロセス群RSS停止650MiB、TM heap=400MiB、1コア。
各runに実際のrc、停止理由、経過秒、1秒間隔RSS、rawout SHA-256を保存。
合計run経過時間：{summary['run_elapsed_sum_s']}秒、最大群RSS：{summary['peak_group_rss_kib']}KiB。
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
''')
artifacts={str(p.relative_to(OUT)):digest(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name not in ['artifacts.sha256','prospective_mutations_20261111.tar.gz']}
write(OUT/'artifacts.sha256',''.join(h+'  '+p+'\n' for p,h in artifacts.items()))
with tarfile.open(OUT/'prospective_mutations_20261111.tar.gz','w:gz') as t:
    for rel in list(artifacts)+['artifacts.sha256']: t.add(OUT/rel,arcname='mutations/'+rel,recursive=False)
with tarfile.open(OUT/'prospective_mutations_20261111.tar.gz','r:gz') as t:
    assert len(t.getmembers())==len(artifacts)+1
print(json.dumps(summary,ensure_ascii=False,indent=2))
print('ARCHIVE', (OUT/'prospective_mutations_20261111.tar.gz').stat().st_size, 'bytes')
