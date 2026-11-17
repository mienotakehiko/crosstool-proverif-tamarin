# 生存変異の前向き再評価

## 結論と定義
既存20変異を新規凍結クエリで再評価した。対照PVと変異PVの確定判定が異なる場合だけ「検出」とした。
計測付きモデルで20/20に差があるが、2件は入力ガード監査だけによる検出である。
これは20件の診断正解率でも100件評価でもない。無差分を意味的同値とは判定しない。

| 種 | 演算子 | 対照と異なったクエリ |
|---|---|---|
| lmots | event_accept_argument | LS1_unforge, forge |
| lmots | event_sign_argument | LS1_unforge, forge |
| lmots | remove_reveal_event | revealreach, seed_without_reveal |
| lmots | replicate_signer | LS1_unforge, forge |
| lmots | disable_signer | acceptreach, signreach, exec_accept |
| lmots | disable_accept | acceptreach, exec_accept |
| lmots | unguarded_reveal | reveal_guarded |
| lmots | wrong_public_key | acceptreach, exec_accept |
| lmots | private_to_public | prf_public_probe |
| lmots | reveal_wrong_secret | seedreach |
| lms_s2 | event_accept_argument | LS1, LS3_forge |
| lms_s2 | event_sign_argument | LS1, LS3_forge |
| lms_s2 | remove_reveal_event | revealreach, seed_without_reveal |
| lms_s2 | replicate_signer | LS4_pure, LS1, LS3_forge |
| lms_s2 | disable_signer | acceptreach, signreach, exec |
| lms_s2 | disable_accept | acceptreach, exec |
| lms_s2 | unguarded_reveal | reveal_guarded |
| lms_s2 | wrong_public_key | acceptreach, exec |
| lms_s2 | private_to_public | prf_public_probe |
| lms_s2 | reveal_wrong_secret | seedreach |

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
