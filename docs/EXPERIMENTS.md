# 実験運用規約

この文書は、`experiments/` での実験の命名・作成・比較方法を定義します。共通規約は [AGENTS.md](../AGENTS.md)、コンペ固有の検証方針は [COMPETITION.md](COMPETITION.md)、結果の台帳は [EXPERIMENT_LOG.md](EXPERIMENT_LOG.md) を参照してください。

## このリポジトリでの適用

いまは初期段階で、環境を理解しながら進行方針を確定する。強化学習は候補であり、公式リーダーボードの更新は目的にしない。ルールと評価の正本は [COMPETITION.md](COMPETITION.md)、現在の段階は [HANDOVER.md](HANDOVER.md)。

- Major はエージェントの種類が変わる単位にする。実装済みは `exp001_random_eval`（シード付きランダム）と `exp002_nearest_eval`（最近傍惑星ヒューリスティック）。どちらも学習しない。
- Minor は同一エージェントの設定差分にする。評価プロトコル自体を変えるときは、新しいプロトコル ID を `orbit/protocols/` に追加し、COMPETITION.md に書く。
- 比較は、同じ評価プロトコル（環境コミット、seed、対戦相手、試合数、ゲーム設定）の実測だけを並べる。候補エージェントはプロトコルの外であり、実験設定で指定する。
- 公式スキルレーティング μ と、ローカルの勝率や艦数差を同じ列で比較しない。
- 学習実験は未実装。追加するかどうかは、進行方針が確定してから決める。

## Major / Minor

~~~text
experiments/
├── exp001_random_eval/         # シード付きランダム。学習しない
│   ├── run.py
│   ├── config.yaml
│   └── exp/
│       └── 000.yaml
└── exp002_nearest_eval/        # 最近傍惑星ヒューリスティック。学習しない
    ├── run.py
    ├── config.yaml
    └── exp/
        └── 000.yaml
~~~

| 単位 | 名前 | 新規作成する基準 |
| --- | --- | --- |
| Major | `exp003_ppo` のような新しい方策 | 方策の種類、学習アルゴリズム、入出力の大きな変更 |
| Minor | `exp/000.yaml`, `exp/001.yaml` | 同一実装の報酬、学習率、プロトコル ID の指定 |
| Run | UTC時刻+ランダムID | 同じ Major/Minor の再実行を独立した成果物ディレクトリに保存する |

方策そのものを変える差分を Minor に詰め込まない。学習率だけの変更で実験ディレクトリを複製しない。

## 実験作成手順

1. `docs/COMPETITION.md` の評価プロトコル、環境コミット、提出制限を確認する。
2. 既存の Major で表現できる差分なら、未使用の `exp/NNN.yaml` を追加する。
3. 方策や学習手続きを大きく変えるときだけ新しい `experiments/expNNN_description/` を作る。`exp001_random_eval/` の `run.py`・`config.yaml`・`exp/000.yaml` を参照する。
4. 実行前に仮説、変更点、比較対象、評価プロトコルを明確にする。継続的に追跡する実験なら `docs/EXPERIMENT_LOG.md` に記す。
5. 結果、採否、根拠を `docs/EXPERIMENT_LOG.md` に記録する。作業方針が変わったときだけ `docs/HANDOVER.md` を更新する。成果物を黙って上書きしない。

## 実行例

~~~bash
uv run python -m experiments.exp001_random_eval.run exp=000
uv run python -m experiments.exp002_nearest_eval.run exp=000
~~~

両方とも `orbit/protocols/eval_v01.yaml` を使う。対戦相手はプロトコルの `random` で、候補だけが実験ごとに違う。

## 結果の比較

- 検証条件は `docs/COMPETITION.md` と `orbit/protocols/*.yaml` に記録する。
- プロトコルを改訂するときは新しい ID（例: `eval_v02`）を付け、古い結果と直接ランキングしない。
- 各実行についてコマンド、Git commit、環境コミット、プロトコル ID とそのハッシュ、seed、メトリクス、出力先、採否を残す。

## 成果物

`output/experiments/<major>/<minor>/<run_id>/` に保存する。

- `run.json`: Git commit、評価プロトコル ID、プロトコルのハッシュ、環境コミット、終了状態
- `config.yaml`: 解決済み設定
- `metrics.json`: `save_metrics()` に渡した実測値だけ。勝率や艦数の集約であり、公式 μ ではない
- `games.json`: 試合ごとの勝敗、艦数、拒否された手、TIMEOUT / ERROR / INVALID の回数

`metrics.json` は評価を実行したときだけ生成される。仮説と採否は `docs/EXPERIMENT_LOG.md` に書く。
