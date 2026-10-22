# 実験運用規約

この文書は、`experiments/` での実験の命名・作成・比較方法を定義します。共通規約は [AGENTS.md](../AGENTS.md)、コンペ固有の検証方針は [COMPETITION.md](COMPETITION.md)、結果の台帳は [EXPERIMENT_LOG.md](EXPERIMENT_LOG.md) を参照してください。

## Major / Minor

~~~text
experiments/
├── exp000_sample/              # 実行方法のデモ。学習はしない
│   ├── run.py
│   ├── config.yaml
│   └── exp/
│       ├── 000.yaml
│       └── 001.yaml
└── exp001_baseline/            # コンペで新規作成する例（未実装）
    ├── run.py
    ├── config.yaml
    └── exp/
        ├── 000.yaml
        └── 001.yaml
~~~

| 単位 | 名前 | 新規作成する基準 |
| --- | --- | --- |
| Major | `exp001_baseline`, `exp002_catboost` | アルゴリズム、特徴量生成・学習パイプライン、入出力の大きな変更 |
| Minor | `exp/000.yaml`, `exp/001.yaml` | 同一実装におけるパラメータ、Seed、損失関数・fold選択などの変更 |
| Run | UTC時刻+ランダムID | 同じMajor/Minorの再実行を独立した成果物ディレクトリに保存（`utils.artifacts.experiment_run`） |

MajorのNNや特徴量エンジニアリングの差分を安易にMinorへ詰め込まないこと。一方、些細な学習パラメータ変更だけで実験コードを複製しないこと。

**注意:** `exp000_sample/run.py` は約1秒待機してHydra/W&Bを初期化するサンプルです。実際の学習、CV計算、モデル保存は行いません。

## 実験作成手順

1. `docs/COMPETITION.md` の対象データ、評価指標、検証方式、提出制限を確認する。
2. 既存のMajorで表現できる差分なら、未使用の `exp/NNN.yaml` を追加する。
3. モデル・処理を大きく変えるときだけ新しい `experiments/expNNN_description/` を作る。初回は `exp000_sample/` を参照し、`run.py`・`config.yaml`・`exp/000.yaml` を整備する。
4. 実行前に**仮説・変更点・比較対象・評価基準**を明確にする。継続的に追跡する実験なら `docs/EXPERIMENT_LOG.md` に記す。必要な実装と計算予算を確認する。
5. CPUで可能な小規模テスト後、承認済みのGPU予算内で学習する。評価指標とfoldごとの結果を記録する。
6. 結果・採否・根拠を `docs/EXPERIMENT_LOG.md` に記録する。作業方針や進行中のジョブなど重要な状態が変わった場合にだけ `docs/HANDOVER.md` も更新する。成果物を黙って上書きしない。

## Hydra実行例

~~~bash
# 学習をしないサンプルの設定確認
uv run python -m experiments.exp000_sample.run exp=000 exp.debug=true

# 新規実験の実装が完成した後の例
uv run python -m experiments.exp001_baseline.run exp=000
uv run python -m experiments.exp001_baseline.run exp=001
~~~

実際に追加したMajor/Minorだけを指定すること。`exp001_baseline` はテンプレートに同梱されていません。`exp.debug=true` は現状、W&Bのオンライン送信を無効化するだけで、データ量・学習時間を短縮する仕組みではありません。

## CV・結果の比較

- 検証方式を `docs/COMPETITION.md` に記録し、同じfold割当・評価指標・データ版を用いて比較する。
- CVを改訂する際は理由と新しい版（例：`cv_v02`）を明示し、古いCVの結果と同列にランキングしない。
- OOF予測は `utils.validation.build_oof_frame` で行ID・fold・予測の長さを検証して整列し、`save_oof_csv` で保存する。test予測は別途コンペごとに形式・IDを検証する。
- 各実験について実行コマンド、Git commit、実行環境、CV版、Seed、メトリクス、実行時間、出力先、採否・所見を残す。

## 現状の成果物管理の制約

現在は `output/experiments/<major>/<minor>/<run_id>/` に保存します。`run.json`（Git commit・CV ID等のメタデータ）、`config.yaml`（解決済み設定）、実験が実際に評価値を記録した場合の `metrics.json`、実際にOOFを生成した場合の `oof.csv` が格納されます。

`metrics.json`と`oof.csv`は、学習やCVを実行しないサンプルには生成されません。成果物の場所・仮説・採否は引き続き `docs/EXPERIMENT_LOG.md` に記録してください。

**実装済みの仕組みと今後の予定を混同しないこと。**

## CV/OOF共通ユーティリティ（PR #4）

- `make_cv_plan(cv_id, row_ids, splits, groups=..., times=..., require_complete=True)`: scikit-learn等のsplitterが出すインデックスを検証。重複した行ID、fold内の学習/検証重複、fold間の検証重複、未カバー行を検出。必要に応じてGroup/Timeのリークをチェックする。
- `save_cv_plan` / `load_cv_plan`: **学習・検証双方のインデックスと行IDの順序**をJSONで永続化し、別実験で再利用する。保存済みのCVは上書きしない。`cv_fingerprint` もRunメタデータに記録できる。
- `build_oof_frame`: fold別の予測を元の行順に整列し、未予測・NaN/Inf・予測配列の形状不一致を検出。多クラス分類の2次元予測にも対応。
- `experiment_run`: 新しいrunディレクトリを作り、終了・失敗を`run.json`へ記録。`save_metrics`を明示的に呼んだ場合のみ、実測値を`metrics.json`へ保存する。

**重要:** CV手法・データ版・Group/Timeの指定は各コンペで決める。Groupまたはtimesを渡さなければそれらのリークは自動検証されない。TimeSeriesSplitなどvalidationが全行を覆わない方式では、`make_cv_plan(..., require_complete=False)` と `build_oof_frame(..., allow_partial=True)` を指定し、OOFの対象行だけを評価する。予測内容が正しいかや特徴量生成のリークを、この仕組みだけで保証できるわけではない。

合成データで一連の処理を確認するには：

~~~bash
uv run python -m tools.demo_cv
~~~

実行例と成果物の詳細は [README.md](../README.md) を参照してください。
