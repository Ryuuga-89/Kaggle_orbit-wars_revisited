# 実験ログ（暫定・追記型）

コンペの各実験について、**仮説 → 変更 → 実行 → 検証 → 判断**を残すための台帳です。`docs/HANDOVER.md` は現在の状態の要約であり、実験履歴の保管先にはしません。W&Bや `output/` の成果物がある場合は、その参照先を記録してください。

`utils.artifacts.experiment_run` は一意の run ID と設定、Git commit、評価プロトコルを自動記録します。**この Markdown 台帳への追記、学習、公式レーティングの取得、W&B へのメトリクス転送は自動ではありません。**

## 読み方

対象は終了済みのシミュレーションコンペです。目的は強化学習の実践と学習であり、公式順位の更新ではありません。詳細は [COMPETITION.md](COMPETITION.md)。

- **CV ID・データ版・Seed**: 評価プロトコル ID、`kaggle-environments` の git commit、対戦 seed を書く。
- **fold別/全体CV**: 試合数、対戦相手、勝敗、艦数差の実測を書く。未計測は `未計測`。
- **LB**: 公式スキルレーティング。再提出しない実験は `未提出`。ローカル勝率はここに書かない。
- プロトコル、環境コミット、対戦相手が違う結果は、数値を直接比較しない。

| 実行識別子 | 仮説・変更点 | Git commit / コマンド | CV ID・データ版・Seed | fold別/全体CV | LB | 成果物・W&B URL | 判断・次の仮説 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `20261022T153600581436Z_f4162e8f1c` | シード付きランダム同士が `eval_v01` で完走するか | コマンドは `uv run python -m experiments.exp001_random_eval.run exp=000`。`run.json` の git_commit は `400d461`（実行時の HEAD。この実験コードは未コミット） | `eval_v01` / `aeb49aea` / seed 42。fingerprint `ac301f71c1d5fd4c32e0043d87af51a9a9d9c51077f81f007a90e018f7845534` | 1試合。候補の勝ち。艦数 604 対 552。final_step 499。拒否手・TIMEOUT・ERROR・INVALID は 0 | 未提出 | `output/experiments/exp001_random_eval/000/20261022T153600581436Z_f4162e8f1c/` | 実行経路は動く。1試合の勝ちは強さの推定にしない |
| `20261022T153602122756Z_d2addd54e6` | 最近傍ヒューリスティックが同じプロトコルのランダム相手に対して手を返せるか | `uv run python -m experiments.exp002_nearest_eval.run exp=000`。git_commit の記録は上と同じ `400d461` | 上と同じ `eval_v01` | 1試合。候補の勝ち。相手の艦数 0 で step 137 に終了。候補艦数 2135。拒否手・TIMEOUT・ERROR・INVALID は 0 | 未提出 | `output/experiments/exp002_nearest_eval/000/20261022T153602122756Z_d2addd54e6/` | この seed では相手を排除した。試合数が 1 なのでランダムとの優劣は未判定。次は試合数を増やした別プロトコル |

## 記録規則

- Major/Minorが同じでも実行ごとに区別できる識別子（日時やW&B run ID等）を付ける。
- 未計測は `未計測`、未提出は `未提出` と記録し、推測値を埋めない。
- 評価プロトコル、環境コミット、対戦相手が違う実験は、スコアを直接比較しない。
- 新しい結果は既存の結果を上書きせず追記する。公式ルールに反する成果物や機密情報の公開リンクは載せない。
- `run.json`、`config.yaml`、実測した `metrics.json`、`games.json` が一次情報。台帳には run ディレクトリの相対パスを記録する。
