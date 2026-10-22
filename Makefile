CPU_FLAG :=
ifneq ($(CPU),)
    CPU_FLAG := -f compose.cpu.yaml
endif

default: build

build:
	docker compose $(CPU_FLAG) build

bash:
	docker compose $(CPU_FLAG) run --rm kaggle bash

down:
	docker compose $(CPU_FLAG) down

# === uv環境用コマンド ===
uv-setup:
	uv sync --group dev
