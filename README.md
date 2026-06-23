# 🧩 Hermes Plugins

A collection of plugins for the [Hermes Agent](https://github.com/NousResearch/hermes) — native
tools, commands, and hooks that run in-process inside Hermes. This repo currently ships one
plugin, with more on the way.

## 📦 Plugins

| Plugin | What it adds | Tier |
| --- | --- | --- |
| [hermes-spider-tools](./plugins/hermes-spider-tools) | 🕷 [Spider Cloud](https://spider.cloud) web scraping, crawling, search, and remote browser automation as native Hermes tools | Core REST + Browser |

> More plugins will be added here over time. Each lives in its own directory under `plugins/`
> and is self-contained (its own `plugin.yaml`, `__init__.py`, and `README.md`).

## 🚀 Quick start

Requires the [Hermes Agent](https://github.com/NousResearch/hermes).

```bash
# 1. install (clones into ~/.hermes/plugins, copies config.yaml, prompts for the API key)
hermes plugins install spider-rs/hermes-plugins/plugins/hermes-spider-tools

# 2. browser tier only — add the SDK to Hermes' environment
~/.hermes/hermes-agent/venv/bin/pip install spider-browser

# 3. enable, then launch
hermes plugins enable hermes-spider-tools
hermes
```

Get a Spider Cloud key at <https://spider.cloud/api-keys> — step 1 prompts for it. Inside Hermes,
run `/plugins` to confirm it loaded, then `/spider status`.

No GitHub remote yet? Install from a local clone instead — `cp -r plugins/hermes-spider-tools
~/.hermes/plugins/`, then steps 2–3. Other routes (project-local, PyPI) are in
[Other ways to install](#-other-ways-to-install--distribute).

## 🛠️ Plugin use cases

### 🕸️ Web scraping & crawling — [hermes-spider-tools](./plugins/hermes-spider-tools)

Gives the agent first-class access to [Spider Cloud](https://spider.cloud). Two tool tiers:

- **Core** — stateless REST tools: `spider_scrape`, `spider_crawl`, `spider_search`,
  `spider_links`, `spider_screenshot`, `spider_unblocker`, `spider_transform`, and
  `spider_get_credits`. Pure standard library — no dependencies.
- **Browser** — stateful remote-browser automation backed by Spider's pre-warmed fleet:
  `spider_browser_open`/`navigate`/`click`/`fill`/`screenshot`/`content`/`evaluate`/`wait_for`/`close`.
  Needs `pip install spider-browser`.

Manage them with the `/spider` and `/spider-browser` commands. See the
[plugin README](./plugins/hermes-spider-tools/README.md) for the full tool reference.

## 📦 Other ways to install & distribute

The [Quick start](#-quick-start) covers the common case. Other routes:

- **Project-local:** drop a plugin in a repo's `./.hermes/plugins/` and enable project plugins
  with `HERMES_ENABLE_PROJECT_PLUGINS=1` (this runs the plugin's Python — only for trusted code).
- **Update a GitHub install:** `hermes plugins update hermes-spider-tools`.
- **PyPI:** package a plugin with a `hermes_agent.plugins` entry point, `pip install` it into
  Hermes' environment, then `hermes plugins enable`. This is the only route that auto-installs a
  plugin's Python dependencies; it skips the install-time key prompt and `*.example` copy (those
  are Git-install only).

Discovery order, later overriding earlier: **bundled → user (`~/.hermes/plugins/`) → project
(`./.hermes/plugins/`) → pip entry points.** Discovery never auto-enables — always `hermes plugins
enable <name>`.

## 🧑‍💻 Local development

This repo uses [`uv`](https://docs.astral.sh/uv/) for the dev environment (lint + the import
smoke test). The plugins themselves run inside Hermes' own interpreter.

```bash
uv sync                         # create the dev venv
uv run ruff check plugins       # lint
uv run python tests/smoke.py    # import + schema/handler smoke test (no network)
```

When iterating on a plugin, install it into `~/.hermes/plugins/` (or symlink it) and restart
Hermes to pick up code changes:

```bash
ln -sfn "$PWD/plugins/hermes-spider-tools" ~/.hermes/plugins/hermes-spider-tools
~/.hermes/hermes-agent/venv/bin/pip install spider-browser   # browser tier only
hermes plugins enable hermes-spider-tools
```

## 🗂️ Repository structure

```
hermes-plugins/
├── .envrc                          # direnv: loads .env into the shell
├── .env.example                    # template for required secrets
├── .gitignore                      # ignores .env, config.yaml, caches
├── pyproject.toml / uv.lock        # uv dev environment (lint + smoke test)
├── LICENSE
├── README.md
├── tests/
│   └── smoke.py                    # imports the plugin, validates schemas/handlers
└── plugins/
    └── hermes-spider-tools/        # Spider Cloud tools (core + browser tiers)
        ├── plugin.yaml             # manifest (name, provides_tools, requires_env)
        ├── config.yaml.example     # primary config template (copied to config.yaml)
        ├── __init__.py             # register(ctx): wires tools, commands, hooks
        ├── config.py               # config.yaml loader + env fallback
        ├── client.py               # stdlib HTTP client + result capping
        ├── schemas.py              # core tool JSON schemas
        ├── tools.py                # core tool handlers
        ├── browser_schemas.py      # browser tool JSON schemas
        ├── browser.py              # browser runtime (loop thread) + handlers
        ├── settings.py             # config-baselined enable/disable state
        ├── commands.py             # /spider and /spider-browser
        ├── constants.py            # shared tool-name constants
        ├── LICENSE
        └── README.md
```

## 📄 License

MIT
