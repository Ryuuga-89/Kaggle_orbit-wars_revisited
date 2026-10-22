# MLコンペ用実験テンプレート

## 特徴
- Kaggle公式イメージを利用したDocker環境（uv環境との完全一致は未検証）
- Hydra による実験管理
- 実験用スクリプトファイルを major バージョンごとにフォルダごとに管理 & 実験パラメータ設定を minor バージョンとしてファイルとして管理
   - 実験用スクリプトと実験パラメータ設定を同一フォルダで局所的に管理して把握しやすくする
- dataclass を用いた config 定義を用いることで、エディタの補完機能を利用できるように

### Hydra による Config 管理
- Config は yamlとdictで定義するのではなく、dataclass を用いて定義することで、エディタの補完などの機能を使いつつタイポを防止できるようにする
- 各スクリプトに共通する環境依存となる設定は utils/env.py の EnvConfig で定義される
- 各スクリプトによって変わる設定は、実行スクリプトのあるフォルダ(`{major_exp_name}`)の中に `exp/{minor_exp_name}.yaml` として配置することで管理。
    - 実行時に `exp={minor_exp_name}` で上書きする
    - `{major_exp_name}` と `{minor_exp_name}` の組み合わせで実験が再現できるようにする

## Structure
```text
.
├── AGENTS.md
├── docs
│   ├── COMPETITION.md
│   ├── EXPERIMENTS.md
│   ├── EXPERIMENT_LOG.md
│   └── HANDOVER.md
├── experiments
├── input
├── notebooks
├── output
├── tools
├── utils
├── .python-version
├── Dockerfile
├── Dockerfile.cpu
├── LICENSE
├── Makefile
├── README.md
├── compose.cpu.yaml
├── compose.yaml
└── pyproject.toml

```

## AIエージェントによる開発

Codex・Cursor・Antigravityなどを併用する場合も、共通ルールは以下のファイルで管理します。作業内容に応じて必要なドキュメントだけを参照してください。コンペでのデータ利用・学習・提出に必要な条件は、実行前に `COMPETITION.md` で確認します。

- [AGENTS.md](AGENTS.md) — エージェントが最初に読む操作・安全・検証の規約
- [docs/COMPETITION.md](docs/COMPETITION.md) — コンペごとの評価・データ・利用ルール
- [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md) — Major/Minorの命名・作成・比較規約
- [docs/EXPERIMENT_LOG.md](docs/EXPERIMENT_LOG.md) — 実験結果と判断の追記型台帳（自動追跡基盤の実装前）
- [docs/HANDOVER.md](docs/HANDOVER.md) — 現在の進捗・進行中ジョブ・次の作業の要約

`utils.validation` でCV分割の保存・再利用とOOF整合性検証、`utils.artifacts` で一意のrunディレクトリ・設定・メトリクス保存が可能です。**学習そのものやCV評価値の自動算出は行いません。** HydraサンプルはW&Bの初期化とrunメタデータの保存のみを行い、架空のスコアは記録しません。

## 環境構築

環境構築には uv と Docker の2つの方法があります。ローカルで手軽に開発したい場合は uv、Kaggle公式イメージを基盤として実行したい場合は Docker を使用してください。

### uv による環境構築

```sh
# セットアップ
make uv-setup

# スクリプトを実行する場合
uv run python -m experiments.exp000_sample.run exp=001
```

### Docker による環境構築

```sh
# imageのbuild
make build

# Pythonスクリプトの実行・対話シェル
make bash

# CPUで起動する場合はCPU=1やCPU=True などをつける
```

ローカルJupyterLabは使用しません。`notebooks/` はKaggleで実行・提出するNotebookを保存するためのディレクトリです。
DockerはJupyterサーバーを起動せず、`make bash` でシェルを開いてPythonコードを実行します。

## スクリプトの実行方法

```sh
# python -m experiments.{major_version_name}.run exp={minor_version_name}

python -m experiments.exp000_sample.run
python -m experiments.exp000_sample.run exp=001
```

※ `python -m` を使用することで、カレントディレクトリがPythonパスに追加され、`utils` モジュールを正しくインポートできます。

## CV・OOF・成果物の共通基盤

`utils.validation` はscikit-learnなどの分割インデックスを受け取り、以下を行います。

- `make_cv_plan`：CV分割を検証（train/validation重複、fold間の重複、行ID重複）。`groups`や`times`を与えた場合はGroup/Timeリークを追加検出します。
- `save_cv_plan` / `load_cv_plan`：分割と元データの**行ID・順序**をJSONに保存して再利用します。CVの上書きや異なるデータへの誤適用を防止します。
- `build_oof_frame` / `save_oof_csv`：fold別の予測を元の行順に並べ、形状不一致・NaN/Inf・欠損を検出してCSVに保存します（1次元/多クラス2次元）。
- `cv_fingerprint`：CV分割全体のハッシュ値を取得できます。

`utils.artifacts.experiment_run` は `output/experiments/<major>/<minor>/<run_id>/` に一意の成果物ディレクトリを作ります。終了/失敗状態、Git commit、CV ID、データ版を `run.json` に、解決済み設定を `config.yaml` に保存し、**実際に`save_metrics()`を呼んだ場合のみ** `metrics.json` を生成します。設定内の典型的な秘密情報のキーは伏字化しますが、任意の値に埋め込まれた機密情報を完全に検出するものではありません。

最小のCPUデモ（合成データ、ネットワークなし、実データ不要）：

```bash
uv run python -m tools.demo_cv
```

出力例：

```text
output/
├── cv/demo_v01.json
└── experiments/exp000_demo_cv/000/<run_id>/
    ├── config.yaml
    ├── run.json
    ├── metrics.json
    └── oof.csv
```

CV・データ版の選定や評価関数、実際の学習処理は**コンペ固有**です。共通ユーティリティはリークの完全な防止やモデルの性能を保証しません。時系列分割で未評価行がある場合は `make_cv_plan(..., require_complete=False)` と `build_oof_frame(..., allow_partial=True)` を指定し、その評価対象行だけに対応するOOFを扱います。

`run.json` は一次情報ですが、W&Bへのメトリクス自動転送と `docs/EXPERIMENT_LOG.md` への自動追記は現時点で行われません。詳細は [実験運用規約](docs/EXPERIMENTS.md) を参照してください。

## Kaggle API ツール

`uv sync --group dev` で依存関係をインストールしてください。

```bash
uv run python tools/check_submission.py <competition> --timeout 3600
uv run python tools/upload_model.py --title my-models --user-name YOUR_KAGGLE_USERNAME --dir ./output/experiments --pattern '**/best_model.pt' --new
```

`uv.lock` はGit管理します。依存更新後に `uv lock` を実行しコミットしてください。
Kaggle公式Dockerイメージとuv環境は現時点で完全に同一ではありません。Dockerの依存関係と実行確認は別途対応が必要です。

## CI・Kaggle提出CSVの事前検証

GitHub Actions（`.github/workflows/ci.yml`）はPRと`main`へのpushで、固定済み依存環境（`uv.lock`）を使ってRuff・pytest・合成CVデモ・Hydraサンプルを実行します。**実データ、Kaggle API認証、提出、GPUはCIでは使用しません。** 初回はGitHubのActions画面で結果を確認してください。

提出前に`sample_submission.csv`を元にローカルCSVを検査できます。実際の提出は行いません。

~~~bash
# 列名、列順、行数、ID順序、欠損、targetの数値・有限性を検証
uv run python -m tools.validate_submission output/submission.csv \
  --sample input/sample_submission.csv --numeric target

# ID列がPassengerIdなど独自名なら明示
uv run python -m tools.validate_submission output/submission.csv \
  --sample input/sample_submission.csv --id-column PassengerId --numeric Survived

# ID列のないコンペの場合のみ（並びの正しさは機械的に判定できません）
uv run python -m tools.validate_submission output/submission.csv \
  --sample input/sample_submission.csv --no-id --numeric target
~~~

- ID列は`id`（大文字小文字を無視して完全一致）だけ自動認識します。それ以外は`--id-column`、IDがなければ`--no-id`を指定してください。
- IDの並び順は標準で厳密に検証します。コンペがIDによる対応付けを許可することを確認した場合だけ、`--allow-reordered`を指定できます。
- `--numeric`を指定した予測列について、文字列や`NaN`・`Inf`を拒否します。複数列なら繰り返し指定します。カテゴリ文字列予測は`--numeric`を付けずに検証してください。
- 形式検証だけでは、クラス値の範囲、確率総和、評価方式、提出回数制限、外部データ利用規約、推論の正しさは保証できません。**公式Rules/Evaluationの確認と本番提出の明示的な承認は別途必要**です。
- CV設計のレビュー・fold/OOF整合性検証には、必要時に[validate-cv Agent Skill](.agents/skills/validate-cv/SKILL.md)を参照してください。詳細な手順を`AGENTS.md`に常時読み込ませる必要はありません。

