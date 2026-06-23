# hermes-spider-tools

Native [Hermes Agent](https://hermes-agent.nousresearch.com/) tools that expose
[Spider Cloud](https://spider.cloud?utm_source=github&utm_medium=readme&utm_campaign=hermes-spider-tools) scraping, crawling, search, screenshot, and
browser-automation capabilities.

It ships **two tool tiers**:

- **Core tier** — stateless tools that call the Spider Cloud REST API directly. Pure standard
  library, no runtime dependencies.
- **Browser tier** — stateful remote-browser automation backed by the
  [`spider-browser`](https://pypi.org/project/spider-browser/) Python package (WebSocket to
  Spider's pre-warmed browser fleet).

## Core tools

| Tool | Endpoint | Description |
| --- | --- | --- |
| `spider_scrape` | `POST /scrape` | Scrape a single URL; faster/cheaper than crawling. |
| `spider_crawl` | `POST /crawl` | Crawl a site following links up to a `limit`/`depth`. |
| `spider_search` | `POST /search` | Web search, optionally fetching each result's content. |
| `spider_links` | `POST /links` | Collect links without returning page content. |
| `spider_screenshot` | `POST /screenshot` | Capture a page screenshot (base64 PNG in the payload). |
| `spider_unblocker` | `POST /unblocker` | Fetch anti-bot-protected pages via the stealth unblocker. |
| `spider_transform` | `POST /transform` | Convert raw HTML to markdown/text (no web request). |
| `spider_get_credits` | `GET /data/credits` | Check remaining credit balance (free). |

Core tools cap processing to the first **10 results** by default (configurable via `max_results`
in `config.yaml`) and tell the model when more were available (`processed first 10 of 31
results`).

## Browser tools

Stateful: `spider_browser_open` returns a `session_id` that the other tools take, and
`spider_browser_close` releases it. **Open sessions bill until closed** — they auto-close after
5 minutes of inactivity and on session end / process exit, and at most 5 may be open at once.

| Tool | Description |
| --- | --- |
| `spider_browser_open` | Open a remote browser session; returns a `session_id`. |
| `spider_browser_navigate` | Navigate the session to a URL and wait for load. |
| `spider_browser_click` | Click an element by CSS selector. |
| `spider_browser_fill` | Fill a form field by CSS selector. |
| `spider_browser_screenshot` | Capture a screenshot (base64 PNG in the payload). |
| `spider_browser_content` | Get the page HTML or visible text. |
| `spider_browser_evaluate` | Execute JavaScript in the page and return the result. |
| `spider_browser_wait_for` | Wait for a selector, navigation, or network idle. |
| `spider_browser_close` | Close the session and stop billing. |

## Install

```bash
# 1. install (clones into ~/.hermes/plugins, copies config.yaml, prompts for the API key)
hermes plugins install spider-rs/hermes-plugins/plugins/hermes-spider-tools

# 2. browser tier only — add the SDK to Hermes' environment
~/.hermes/hermes-agent/venv/bin/pip install spider-browser

# 3. enable, then launch
hermes plugins enable hermes-spider-tools
hermes
```

Get a key at <https://spider.cloud/api-keys?utm_source=github&utm_medium=readme&utm_campaign=hermes-spider-tools> — step 1 prompts for it (or set `SPIDER_API_KEY` /
`config.yaml`, see [Configuration](#configuration)). Confirm with `/plugins`, then
`/spider status`.

From a local clone instead of GitHub — `cp -r plugins/hermes-spider-tools ~/.hermes/plugins/`,
copy `config.yaml.example` → `config.yaml`, then run steps 2–3. Project-local and PyPI installs
are in the [repo README](../../README.md#-other-ways-to-install--distribute).

## Configuration

Configuration is read in this order for **every** setting:
**`config.yaml` (primary) → environment variable (fallback) → built-in default.**

### Primary: `config.yaml`

A fully annotated template lives at [`config.yaml.example`](./config.yaml.example). Copy it to
`config.yaml` in this folder (`hermes plugins install` does this automatically) and edit:

```bash
cp config.yaml.example config.yaml
```

`config.yaml` is gitignored — only the `.example` is tracked, so local endpoints and secrets
never get committed. Keys:

| Key | Env fallback | Default | Notes |
| --- | --- | --- | --- |
| `api_key` | — | — | The key, stored directly (file is gitignored). |
| `api_key_env` | — | `SPIDER_API_KEY` | Names an env var to read the key from (keeps the secret out of any file). |
| `api_url` | `SPIDER_API_URL` | `https://api.spider.cloud` | Core REST base URL. |
| `browser_server_url` | `SPIDER_BROWSER_URL` | SDK default | Browser fleet WebSocket. |
| `max_results` | — | `10` | Cap on results returned to the model. |
| `disabled_tools` | — | none | Baseline; `/spider enable\|disable` overrides it live. |

For the key, set **either** `api_key` (literal) **or** `api_key_env` (an env var name). The
template ships with `api_key_env: SPIDER_API_KEY`, so the secret can stay in the environment.

### Secondary: environment variables

Any setting omitted from `config.yaml` falls back to its env var above. Provide the key via the
environment in any of these ways:

- `hermes plugins install <git-url>` masked-prompts for `SPIDER_API_KEY` (`secret: true` in
  `plugin.yaml`) and saves it to `~/.hermes/.env`.
- Add `SPIDER_API_KEY=sk-...` to `~/.hermes/.env` yourself (Hermes loads it at startup).
- Export it inline: `SPIDER_API_KEY=sk-... hermes`.

Get a key at <https://spider.cloud/api-keys?utm_source=github&utm_medium=readme&utm_campaign=hermes-spider-tools>.

## Commands

```
/spider status            show API key status and which tools are enabled
/spider enable [tool]     enable a tool (or all core tools if omitted)
/spider disable [tool]    disable a tool (or all core tools if omitted)
/spider tools             list every tool and whether it is enabled
/spider help              show help

/spider-browser status    show API key status and open browser sessions
/spider-browser close     close all open browser sessions
/spider-browser help      show browser help
```

Toggling is **live** — Hermes re-checks each tool's availability, so no restart is needed.
State persists to `hermes-spider-tools-settings.json` in your Hermes directory (`$HERMES_DIR`,
default `~/.hermes`).

## Debugging

```bash
HERMES_PLUGINS_DEBUG=1 hermes plugins list
hermes logs --level WARNING | grep -i plugin
```

Because `register(ctx)` runs at startup, restart Hermes after changing plugin **code**
(tool toggling via `/spider` is the exception — it takes effect immediately).

**Browser tier:**

- `{"error": "...install spider-browser"}` — the SDK isn't in Hermes' environment:
  `~/.hermes/hermes-agent/venv/bin/pip install spider-browser`.
- `spider_browser_open` returning a CDP timeout (e.g. `Target.setDiscoverTargets`) is the remote
  fleet handshake, not a plugin bug — it reproduces with the bare `spider-browser` SDK. Retry, or
  check fleet availability / your plan for your region.

See per-endpoint parameter details at <https://spider.cloud/docs/api?utm_source=github&utm_medium=readme&utm_campaign=hermes-spider-tools>.

## License

MIT
