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

Requires the [Hermes Agent](https://github.com/NousResearch/hermes). Hermes discovers personal
plugins under `~/.hermes/plugins/`, and discovery alone is not enough — plugins must be enabled.

```bash
# install a plugin for everyday use
cp -r plugins/hermes-spider-tools ~/.hermes/plugins/
hermes plugins enable hermes-spider-tools
hermes

# inside Hermes
/plugins
```

> Prefer a one-command install from GitHub, or packaging for PyPI? See
> [Installing & distributing](#-installing--distributing).

Each plugin's **primary** configuration is its own gitignored `config.yaml` (copied from the
tracked `config.yaml.example` in the plugin folder); environment variables are the **fallback**.
See the [plugin README](./plugins/hermes-spider-tools/README.md#configuration) for the full key
reference. The quickest start is still to pass the key inline via the env fallback:

```bash
SPIDER_API_KEY=sk-... hermes
```

To avoid typing it each time, keep it in a gitignored `.env` and let
[direnv](https://direnv.net) load it automatically when you enter the directory:

```bash
brew install direnv
echo 'eval "$(direnv hook zsh)"' >> ~/.zshrc   # then open a new terminal

echo 'SPIDER_API_KEY=sk-...' > .env             # gitignored
printf 'dotenv\n' > .envrc                       # already present in this repo
direnv allow
```

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

## 📥 Installing & distributing

Hermes discovers plugins from four sources; later ones override earlier on a name clash:
**bundled** (ships with Hermes) → **user** (`~/.hermes/plugins/`) → **project**
(`./.hermes/plugins/`, opt-in via `HERMES_ENABLE_PROJECT_PLUGINS=1`) → **pip** (packages exposing
the `hermes_agent.plugins` entry point). Discovery never auto-enables — always `hermes plugins
enable <name>` afterward.

There are three ways to get a plugin onto a machine:

- **Local (dev / this repo):** copy or symlink the plugin into `~/.hermes/plugins/` (see
  [Local development](#-local-development)). Best while iterating.

- **From GitHub (recommended for sharing).** `hermes plugins install` takes a **Git** source — a
  full URL or `owner/repo` shorthand, with an optional **subdirectory** for monorepos like this
  one. It clones, copies each `*.example` → real file, prompts for `requires_env` secrets, and
  offers to enable:

  ```bash
  hermes plugins install <owner>/hermes-plugins/plugins/hermes-spider-tools
  hermes plugins update hermes-spider-tools   # pull latest later
  ```

  (`hermes plugins install` does **not** fetch from PyPI — Git only.)

- **From PyPI (packaged).** Restructure a plugin as a pip package that declares the entry point,
  publish it, then install it into Hermes' environment yourself:

  ```toml
  # pyproject.toml
  [project.entry-points."hermes_agent.plugins"]
  hermes-spider-tools = "hermes_spider_tools"
  ```

  ```bash
  ~/.hermes/hermes-agent/venv/bin/pip install hermes-spider-tools
  hermes plugins enable hermes-spider-tools
  ```

  Trade-off: the pip route is the only one that auto-installs a plugin's third-party Python
  dependencies (via the package's `dependencies`); the local and GitHub routes do **not**, so a
  tier like the Spider browser tier still needs `pip install spider-browser` separately. The pip
  route also skips the `requires_env` prompt and `*.example` copy (those run only on Git install).

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
