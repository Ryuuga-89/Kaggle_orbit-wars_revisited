# Orbit Wars 再挑戦

終了済みの Kaggle コンペ [Orbit Wars](https://www.kaggle.com/competitions/orbit-wars) を再挑戦するためのリポジトリです。現在は初期段階で、環境を理解しながらプロジェクトの進行方針を確定していきます。公式リーダーボードの順位更新は目的にしていません。ルール・評価・未確認事項は [docs/COMPETITION.md](docs/COMPETITION.md)、現在の作業状態は [docs/HANDOVER.md](docs/HANDOVER.md) を正本にします。

ローカル比較は `orbit/protocols/` の対戦プロトコルで行います。提出物は `agent(obs)` を持つエージェントです。学習コードはまだありません。

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
├── agents
├── experiments
├── notebooks
├── orbit
├── output
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

`orbit.match` が試合を実行し、`utils.artifacts` が run ディレクトリへ設定と実測メトリクスを保存します。勝率は実行した試合から計算します。公式スキルレーティングは取得しません。学習は未実装です。

## 環境構築

環境構築には uv と Docker の2つの方法があります。ローカルで手軽に開発したい場合は uv、Kaggle公式イメージを基盤として実行したい場合は Docker を使用してください。

### uv による環境構築

```sh
# セットアップ
make uv-setup

# 評価を実行する場合（学習しない）
uv run python -m experiments.exp001_random_eval.run exp=000
uv run python -m experiments.exp002_nearest_eval.run exp=000
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
uv run python -m experiments.exp001_random_eval.run exp=000
uv run python -m experiments.exp002_nearest_eval.run exp=000
```

`python -m` によりカレントディレクトリが Python パスに入り、`orbit` と `utils` をインポートできます。

## ローカル評価と成果物

`eval_v01` は seed 42 の 1 試合です。候補がランダムまたは最近傍ヒューリスティックで、対戦相手はシード付きランダムです。1 試合の勝敗は安定した強さの推定ではありません。

シミュレータは PyPI の `kaggle-environments` 1.33.2 wheel には含まれません。`pyproject.toml` の git revision `aeb49aea5f50eb02f287f3e4db4415dc61429791` を使います。プロトコルとインストール済みコミットが違うと実行は失敗します。

`utils.artifacts.experiment_run` は `output/experiments/<major>/<minor>/<run_id>/` を作ります。`run.json` に終了状態、Git commit、評価プロトコル、環境コミットを書き、`config.yaml` に解決済み設定を書きます。`metrics.json` は `save_metrics()` を呼んだときだけ生成します。試合単位の結果は `games.json` です。設定内の典型的な秘密情報キーは伏字にします。

`run.json` は一次情報です。W&B への自動転送と `docs/EXPERIMENT_LOG.md` への自動追記は行いません。詳細は [実験運用規約](docs/EXPERIMENTS.md) を参照してください。

`uv.lock` は Git 管理します。依存更新後に `uv lock` を実行し、コミットするときはロックファイルも含めます。Kaggle 公式 Docker イメージと uv 環境は同一ではありません。

## CI

GitHub Actions（`.github/workflows/ci.yml`）は PR と `main` への push で、`uv.lock` を使って Ruff、pytest、`exp001_random_eval` の 1 試合を実行します。Kaggle API 認証、提出、GPU は CI では使いません。Kaggle への提出は行いません。

