# コンペ情報

> 公式情報は 2026-10-22（JST）に、導入済み Kaggle CLI 2.2.4 で取得した。認証は `~/.kaggle/access_token`。ページ本文の一部（参加締切・チームマージ締切）は `${competition....}` のまま未展開だった。未確認の条件は許可済みとみなさない。

## このリポジトリでの位置づけ

公式コンペは終了している。このリポジトリの目的は、終了後に同じルールへ再挑戦し、学習済みの強化学習を実践して、さらに学ぶことである。公式リーダーボードの順位を更新することは目的にしない。

Kaggle への再提出が今も対戦・順位に効くかは未確認。外部アップロードと提出は、明示的に許可されるまで実行しない。

## 基本情報

| 項目 | 内容 |
| --- | --- |
| コンペ名称 | Orbit Wars（slug: `orbit-wars`）。「orbit wars revisited」という別コンペは CLI 検索では見つからなかった |
| Kaggle URL / 公式ルールURL | https://www.kaggle.com/competitions/orbit-wars （ルールは同サイトの rules ページ） |
| 主催 | Google LLC |
| 開始・終了日時（タイムゾーン付き） | 開始: 2026-04-16。最終提出締切: 2026-06-23 23:59 UTC。評価期間: 2026-06-24 からおおよそ 2026-07-08 まで（リーダーボード収束まで、と Timeline ページ）。一覧 API の `deadline` は `2026-07-07T23:59:00`。参加締切・チームマージ締切はページ上で未展開 |
| 区分・賞金 | Featured。総額 $50,000。1位から10位まで各 $5,000 |
| タスクの種類・目的 | Kaggle Environments のシミュレーション。1対1または4人フリーフォーオールで、エージェントが艦隊を動かし惑星を取る。2010年 Planet Wars を基にした再設計 |
| 評価指標と計算方法 | エピソードの勝敗でスキルレーティングを更新する。各提出は正規分布 N(μ, σ²)。μ が推定スキル、σ は不確実性。初期 μ=600。近いレーティング同士を対戦させる。勝敗の点差は更新に使わない。検証エピソードで自己対戦に失敗すると Error。リーダーボード表示はチーム内の最良ボット。Private LB はない。最終順位は提出締切後も対戦を続けたあとのリーダーボード |
| 提出ファイル形式 | ルートに `agent` 関数を持つ `main.py`。複数ファイルなら `main.py` をルートにした tar.gz。Notebook 提出も公式ガイドに記載がある。CSV 提出ではない |
| `sample_submission.csv` | 存在しない。提出物はエージェント |
| 1日・総提出回数、実行時間・サイズ制限 | ルール: 1日最大 5 提出。最終評価に使うのは最新 2 提出。ターン制限 `actTimeout` の既定は 1 秒。ファイルサイズ上限は未確認。2026-10-22 の `kaggle competitions submission-limits orbit-wars --json` は `{"numTotal": 36, "numAllowedNow": 100}`。日次5件とは一致しないため、残提出枠とは解釈しない |
| チーム・共有・外部コードの制約 | 最大 5 人。チーム外へのコードの非公開共有は禁止。公開するならコンペのフォーラムまたは Notebook で、商用利用を制限しない OSI 承認ライセンス。優勝解法のライセンスは CC-BY 4.0。一般に入手できる商用ソフトや、ライセンスが両立しない入力データ・事前学習モデルは、その部分のオープンソース化義務の対象外とルールに書かれている |

取得時点の参加状況（このアカウント）: 参加済み。一覧上の順位 3031 / 4729 チーム。これはスナップショットであり、再挑戦の目標値ではない。

取得時点のリーダーボード上位（スキルレーティング。提出日はいずれも 2026-06-23）:

| 順位 | チーム | スコア |
| --- | --- | --- |
| 1 | Isaiah @ Tufa Labs | 1865.1 |
| 2 | Hober Malloc | 1800.1 |
| 3 | Felix M Neumann | 1772.1 |
| 4 | Jake Will | 1758.2 |
| 5 | TonyK | 1754.6 |
| 6 | flg | 1754.2 |
| 7 | Audun Ljone Henriksen | 1717.3 |
| 8 | Ender | 1701.0 |
| 9 | Boey | 1687.1 |
| 10 | Xiangyu Liu | 1681.5 |

## ゲームルール（公式「How to Play Orbit Wars」の要約）

- 盤面は 100×100 の連続空間。太陽は (50, 50)、半径 10。太陽を横切る艦隊は消滅する。
- 惑星と彗星は中心に対する 4 回鏡映対称。惑星数は 20–40（5–10 組）。内側（`orbital_radius + planet_radius < 50`）は角速度 `angular_velocity`（1ゲーム内で 0.025–0.05 rad/turn）で公転し、外側は静止。静止グループは少なくとも 3、公転グループは少なくとも 1。
- 惑星は `[id, owner, x, y, radius, ships, production]`。owner は 0–3、中立は -1。production は 1–5。半径は `1 + ln(production)`。所有惑星は毎ターン production 体の艦を生む。初期駐留は 5–99 に偏った分布。ホームは対称組から選ばれ、初期艦数 10。2人戦は対角、4人戦は組の各惑星に1人。
- 行動は `[[from_planet_id, direction_angle, num_ships], ...]`。角度はラジアン（0 が右、π/2 が下）。所有惑星から、現在艦数以下だけ発射できる。空リストは無行動。
- 艦隊速度は `1.0 + (maxSpeed - 1.0) * (log(ships) / log(1000)) ** 1.5`。既定の最大速度は 6.0。1艦は 1.0/turn。直線移動。盤外・太陽・惑星衝突で除去され、惑星衝突は戦闘になる。判定は線分全体。
- 彗星はステップ 50, 150, 250, 350, 450 に4個1組で出現。半径 1、production 1、速度既定 4.0。盤外に出ると駐留艦ごと消える。発射処理より前に除去される。
- ターン順: 彗星消滅 → 彗星出現 → 発射 → 生産 → 艦隊移動 → 惑星公転と彗星移動 → 戦闘。
- 戦闘: 到着艦隊を所有者ごとに合算し、最大勢力と第二勢力が相殺し、生き残った攻撃側が駐留と戦う。同着の攻撃側は全滅。攻撃が駐留を上回れば所有者交代。
- 終了: 500 ターン、または惑星・艦隊を持つプレイヤーが1人以下。得点は所有惑星の艦数 + 所有艦隊の艦数。多い方が勝ち。
- 観測の主なフィールド: `planets`, `fleets`, `player`, `angular_velocity`, `initial_planets`, `comets`, `comet_planet_ids`, `remainingOverageTime`。
- 既定設定: `episodeSteps=500`, `actTimeout=1`, `shipSpeed=6.0`, `sunRadius=10.0`, `boardSize=100.0`, `cometSpeed=4.0`。

ローカル実行: 環境名 `orbit_wars`。PyPI の `kaggle-environments` 1.33.2 wheel にはこの環境が無い。このリポジトリは git commit `aeb49aea5f50eb02f287f3e4db4415dc61429791` を依存に固定している。

## データ

| 項目 | 内容 |
| --- | --- |
| 入力データ・取得元 | コンペの Python スターターキット。2026-10-23 に `kaggle competitions download orbit-wars` で取得し、`input/orbit-wars/` に展開した。`input/` は Git 管理外。中身は `README.md`（ルール）、`agents.md`（作成・ローカル実行・提出の手順）、`main.py`（最近傍惑星へ garrison+1 を送る例） |
| train/testの対応と推論時に使える情報 | 表形式の train/test はない。対戦中に使えるのはエピソードの観測だけ |
| Target列・ID列・Group列・時刻列 | 該当なし |
| データ数、主な型、欠損・重複 | 該当なし。マップはゲームごとに生成される |
| データ・特徴量の版 / checksum | zip 内の更新日時は 2026-05-01 20:46。SHA-256: `README.md` `973458c1bb931bec675b8117450ebdbc5c2b2ac7e14da8bd16ddfa58857c3885`、`agents.md` `1c5486aab027957366025b55d918eb26dd359281da3007da8700370f35886f52`、`main.py` `5253fa86a6191f3d718b8b9850e9d4aaf0bb2aa5e514e87d6b0fb40396daeeff`。`README.md` は導入済みシミュレータの `orbit_wars/README.md` と一致 |
| ライセンス | コンペデータは Apache 2.0 |
| 外部データ・事前学習モデルの許可条件 | ルール上、全員が無償で同等に使える公開物、または Host の Reasonableness を満たす最小費用のもの。非公開データの利用許可とは読まない |
| インターネット・外部API利用条件 | 評価中の ingress / egress は禁止。開発時の外部 API 利用可否は、評価時禁止とは別に未確認 |

## 検証設計

公式指標は対戦相手の分布に依存するスキルレーティングであり、固定テストセットのスコアではない。ローカルの勝率や艦数差は公式 μ と同じものではない。

現在の比較プロトコルは `eval_v01`（`orbit/protocols/eval_v01.yaml`）。

- **評価プロトコル ID**: `eval_v01`
- **内容**: 2 人戦、seed `[42]`、各 seed 1 試合、対戦相手はシード付き `random`、`episodeSteps=500`、`actTimeout=1`、`shipSpeed=6.0`、`cometSpeed=4.0`
- **環境**: `kaggle-environments` git `aeb49aea5f50eb02f287f3e4db4415dc61429791`。インストール済みコミットが違うと `orbit.match` は実行を止める
- **候補**: プロトコルには含めない。`exp001_random_eval` はランダム、`exp002_nearest_eval` は現在座標へ garrison+1 を送る最近傍ヒューリスティック
- **1 試合の限界**: このプロトコルは動作確認と最初の実測用である。勝率の安定した比較には使わない。試合数を増やすときは `eval_v02` として別に記録する
- **学習データ**: 将来の学習で、評価用 seed の手順を学習データに混ぜない
- **公式 LB との差**: 公式 LB は終了済みのスキルレーティング。ローカル指標は勝敗、艦数、拒否された手、TIMEOUT / ERROR / INVALID

実験を比較するときは、同じプロトコル ID だけを並べる。プロトコルを変えたら新しい ID を付け、旧結果と直接ランキングしない。

## 実行・提出環境

| 項目 | 内容 |
| --- | --- |
| ローカル / GPU VM / Kaggle Notebook の役割 | ローカル uv で対戦評価を実行する。GPU 学習と公式提出は未着手 |
| 利用可能なGPU・実行時間・予算 | 未設定。有料 GPU は承認前に開始しない。`eval_v01` の 1 試合は CPU で 1 秒前後 |
| Kaggle Notebookに持ち込める成果物 | 未確認。評価中は外部通信不可 |
| 評価時の推論処理・ネットワーク制限 | 1ターンあたり既定 1 秒。エピソード評価中の外部情報の取得・送信は禁止。リプレイは公開され得る |
| Kaggle API・認証・Dataset公開範囲 | CLI は導入済み。トークンは文書に書かない。Dataset の新規公開は未許可 |

## 根拠・更新履歴

- 最終確認日: 2026-10-22（JST）
- 参照した公式ページ（CLI `kaggle competitions pages orbit-wars list orbit-wars --content`）: Description, Evaluation, rules, data-description, abstract, Timeline, Prizes, Getting Started, How to Play Orbit Wars, AGENTS.md
- 併せて実行: `kaggle competitions list -s "orbit wars"`、`kaggle competitions list -s orbit`、`kaggle competitions list -s revisited`、`kaggle competitions files orbit-wars`、`kaggle competitions submission-limits orbit-wars --json`、`kaggle competitions leaderboard orbit-wars -s --page-size 10`
- 判断が必要な項目: `eval_v01` より多い試合数にするか、GPU 予算、終了後の再提出がプラットフォーム上で何を意味するか

公式ルール・送信先・公開範囲が未確認の操作（外部データ利用、モデルの外部アップロード、Kaggle提出など）は、必要な条件を確認するまで実行しない。ユーザーによって明示的に許可されたGPU環境・予算・対象データの範囲では、実験ごとの再承認は不要。規約・予算・送信範囲を超える操作は別途承認を得る。

## 提出前チェック

ローカルでは、採用した評価プロトコルで `orbit_wars` を実行し、`games.json` と `metrics.json` を残す。Kaggle への提出は、ユーザーが明示したときだけ行う。このリポジトリは提出を自動実行しない。
