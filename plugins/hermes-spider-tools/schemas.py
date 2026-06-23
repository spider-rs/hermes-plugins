"""Model-facing JSON schemas for the core (REST) Spider tools.

These descriptions are effectively routing logic: they tell the model when to
pick a tool and what each argument means. Keep them narrow and explicit.
"""

from __future__ import annotations

# Shared parameter fragments ------------------------------------------------

_RETURN_FORMAT = {
    "type": "string",
    "description": (
        "Output format: markdown, raw (HTML), text, commonmark, html2text, bytes, or xml. "
        "Defaults to the Spider API default."
    ),
}

_REQUEST_MODE = {
    "type": "string",
    "description": (
        "Request engine: 'http' (fast, no JS), 'chrome' (headless browser), or 'smart' "
        "(http with chrome fallback)."
    ),
}


def _schema(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required,
        },
    }


SCRAPE = _schema(
    "spider_scrape",
    "Scrape a single URL via Spider Cloud and return its content in the requested format. "
    "Faster and cheaper than crawling when you only need one page. Use spider_crawl to follow "
    "links across a site. If SPIDER_API_KEY is missing, report the configuration error instead "
    "of retrying.",
    {
        "url": {"type": "string", "description": "The URL to scrape."},
        "return_format": _RETURN_FORMAT,
        "request": _REQUEST_MODE,
        "readability": {
            "type": "boolean",
            "description": "Apply readability to extract the main article content.",
        },
        "root_selector": {
            "type": "string",
            "description": "CSS selector to limit extraction to a page region.",
        },
        "proxy_enabled": {
            "type": "boolean",
            "description": "Route the request through Spider's premium proxies.",
        },
        "cache": {
            "type": "boolean",
            "description": "Allow Spider to serve a cached response when available.",
        },
        "metadata": {
            "type": "boolean",
            "description": "Include extracted page metadata in the response.",
        },
    },
    ["url"],
)

CRAWL = _schema(
    "spider_crawl",
    "Crawl a website starting from a URL, following links up to a limit/depth, and return "
    "content from every page reached. Always set a sensible 'limit' to control cost; crawling "
    "bills per page fetched. If SPIDER_API_KEY is missing, report the configuration error "
    "instead of retrying.",
    {
        "url": {"type": "string", "description": "The starting URL to crawl."},
        "limit": {
            "type": "number",
            "description": "Maximum number of pages to fetch. Strongly recommended.",
        },
        "depth": {
            "type": "number",
            "description": "Maximum link depth to follow from the starting URL.",
        },
        "return_format": _RETURN_FORMAT,
        "request": _REQUEST_MODE,
        "readability": {
            "type": "boolean",
            "description": "Apply readability to extract main content per page.",
        },
        "proxy_enabled": {
            "type": "boolean",
            "description": "Route requests through Spider's premium proxies.",
        },
        "cache": {
            "type": "boolean",
            "description": "Allow Spider to serve cached responses when available.",
        },
        "budget": {
            "type": "object",
            "additionalProperties": {"type": "number"},
            "description": 'Per-path crawl budget, e.g. {"*": 10, "/blog": 5}.',
        },
    },
    ["url"],
)

SEARCH = _schema(
    "spider_search",
    "Search the web via Spider Cloud and optionally fetch the content of each result page. "
    "Set fetch_page_content only when you actually need page bodies; it costs more. If "
    "SPIDER_API_KEY is missing, report the configuration error instead of retrying.",
    {
        "search": {"type": "string", "description": "The search query."},
        "num": {"type": "number", "description": "Number of search results to return."},
        "fetch_page_content": {
            "type": "boolean",
            "description": "Crawl each result and include its content.",
        },
        "return_format": _RETURN_FORMAT,
        "country": {
            "type": "string",
            "description": "Two-letter country code to localize results, e.g. 'us'.",
        },
        "language": {
            "type": "string",
            "description": "Two-letter language code for results, e.g. 'en'.",
        },
    },
    ["search"],
)

LINKS = _schema(
    "spider_links",
    "Collect links from a page or site without returning page content. Use this for URL "
    "discovery; it is cheaper than a full crawl. If SPIDER_API_KEY is missing, report the "
    "configuration error instead of retrying.",
    {
        "url": {"type": "string", "description": "The URL to collect links from."},
        "limit": {"type": "number", "description": "Maximum number of links to return."},
        "depth": {"type": "number", "description": "Maximum link depth to traverse."},
        "external_domains": {
            "type": "boolean",
            "description": "Include links pointing to external domains.",
        },
        "request": _REQUEST_MODE,
    },
    ["url"],
)

SCREENSHOT = _schema(
    "spider_screenshot",
    "Capture a screenshot of a page. Returns a base64-encoded PNG in the response payload. If "
    "SPIDER_API_KEY is missing, report the configuration error instead of retrying.",
    {
        "url": {"type": "string", "description": "The URL to screenshot."},
        "full_page": {
            "type": "boolean",
            "description": "Capture the full scrollable page instead of the viewport.",
        },
        "request": _REQUEST_MODE,
    },
    ["url"],
)

UNBLOCKER = _schema(
    "spider_unblocker",
    "Fetch content from sites protected by anti-bot systems using Spider's stealth unblocker. "
    "Use only when a normal scrape is blocked; it costs more. If SPIDER_API_KEY is missing, "
    "report the configuration error instead of retrying.",
    {
        "url": {"type": "string", "description": "The URL to fetch through the unblocker."},
        "return_format": _RETURN_FORMAT,
        "proxy_enabled": {
            "type": "boolean",
            "description": "Route through Spider's premium proxies.",
        },
    },
    ["url"],
)

TRANSFORM = _schema(
    "spider_transform",
    "Convert raw HTML you already have into clean markdown or text. Performs no web request, so "
    "it does not consume crawl credits. Use when you already hold HTML and just need it cleaned "
    "up. If SPIDER_API_KEY is missing, report the configuration error instead of retrying.",
    {
        "data": {
            "type": "array",
            "description": "One or more HTML documents to transform.",
            "items": {
                "type": "object",
                "properties": {
                    "html": {"type": "string", "description": "Raw HTML content to transform."},
                    "url": {
                        "type": "string",
                        "description": "Optional source URL used to resolve relative links.",
                    },
                },
                "required": ["html"],
            },
        },
        "return_format": _RETURN_FORMAT,
        "readability": {
            "type": "boolean",
            "description": "Apply readability before converting.",
        },
    },
    ["data"],
)

GET_CREDITS = _schema(
    "spider_get_credits",
    "Check the remaining Spider Cloud credit balance for the configured API key. Free to call; "
    "useful to confirm the key works. If SPIDER_API_KEY is missing, report the configuration "
    "error instead of retrying.",
    {},
    [],
)
