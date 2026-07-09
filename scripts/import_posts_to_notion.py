#!/usr/bin/env python3
"""Import Quarto blog posts into the Notion "모든 게시글" data source.

The Notion database is intentionally kept clean: only title, date, and
categories are written automatically. Operational state such as source path,
content hash, and failure logs stays in a local manifest file.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import yaml


API = "https://api.notion.com/v1"
NOTION_VERSION = "2026-03-11"
ALL_POSTS_DS = "b362ec26-1aaf-836d-9f00-878aa4052db1"
BOARD_DS = "5e22ec26-1aaf-82f0-bd37-0748e90aa957"
PROJECTS_DS = "71370145-e585-4372-805b-7c9b15f57f25"
SITE_URL = "https://cryscham123.github.io"

ROOT = Path(__file__).resolve().parents[1]
POSTS_ROOT = ROOT / "posts"
SITE_ROOT = ROOT / "_site"
DEFAULT_MANIFEST = ROOT / "notion_import_manifest.json"

TITLE_PROP = "제목"
DATE_PROP = "날짜"
CATEGORY_PROP = "카테고리"

MAX_TEXT = 1900
MAX_RICH_TEXT = 90
MAX_CHILDREN = 100
REQUEST_DELAY = 0.35

LANGUAGES = {
    "abap",
    "agda",
    "arduino",
    "assembly",
    "bash",
    "basic",
    "c",
    "c#",
    "c++",
    "clojure",
    "coffeescript",
    "css",
    "dart",
    "diff",
    "docker",
    "elixir",
    "elm",
    "erlang",
    "f#",
    "flow",
    "fortran",
    "gherkin",
    "glsl",
    "go",
    "graphql",
    "groovy",
    "haskell",
    "html",
    "java",
    "javascript",
    "json",
    "julia",
    "kotlin",
    "latex",
    "less",
    "lisp",
    "livescript",
    "lua",
    "makefile",
    "markdown",
    "markup",
    "matlab",
    "mermaid",
    "nix",
    "objective-c",
    "ocaml",
    "pascal",
    "perl",
    "php",
    "plain text",
    "powershell",
    "prolog",
    "protobuf",
    "python",
    "r",
    "reason",
    "ruby",
    "rust",
    "sass",
    "scala",
    "scheme",
    "scss",
    "shell",
    "sql",
    "swift",
    "typescript",
    "vb.net",
    "verilog",
    "vhdl",
    "visual basic",
    "webassembly",
    "xml",
    "yaml",
}


def load_token() -> str:
    token = os.environ.get("NOTION_API_TOKEN", "").strip()
    if token:
        return token
    path = Path.home() / ".config/notion/api_key"
    if path.exists():
        return path.read_text().strip()
    raise SystemExit("No NOTION_API_TOKEN or ~/.config/notion/api_key found")


class Notion:
    def __init__(self, token: str):
        self.token = token

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {
            "Authorization": "Bearer " + self.token,
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }
        req = urllib.request.Request(API + path, data=data, method=method, headers=headers)
        for attempt in range(6):
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    if resp.status == 204:
                        return {}
                    return json.load(resp)
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", "replace")
                if exc.code == 429 and attempt < 5:
                    retry = float(exc.headers.get("Retry-After", "1"))
                    time.sleep(retry + 0.2)
                    continue
                if 500 <= exc.code < 600 and attempt < 5:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                raise RuntimeError(f"Notion API {exc.code} {method} {path}: {detail[:1000]}") from exc
        raise RuntimeError(f"Notion request failed after retries: {method} {path}")

    def ensure_date_property(self) -> None:
        meta = self.request("GET", f"/data_sources/{ALL_POSTS_DS}")
        if DATE_PROP in meta.get("properties", {}):
            return
        self.request("PATCH", f"/data_sources/{ALL_POSTS_DS}", {"properties": {DATE_PROP: {"date": {}}}})

    def create_page(
        self,
        title: str,
        date: str | None,
        categories: list[str],
        extra_properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        properties: dict[str, Any] = {
            TITLE_PROP: {"title": [{"text": {"content": truncate(title, 1900)}}]},
        }
        if extra_properties:
            properties.update(extra_properties)
        if date:
            properties[DATE_PROP] = {"date": {"start": date}}
        if categories:
            properties[CATEGORY_PROP] = {
                "multi_select": [{"name": truncate(cat, 100)} for cat in categories[:100]]
            }
        body = {"parent": {"type": "data_source_id", "data_source_id": ALL_POSTS_DS}, "properties": properties}
        return self.request("POST", "/pages", body)

    def append_children(self, block_id: str, children: list[dict[str, Any]]) -> None:
        for i in range(0, len(children), MAX_CHILDREN):
            chunk = children[i : i + MAX_CHILDREN]
            self.request("PATCH", f"/blocks/{block_id}/children", {"children": chunk})
            time.sleep(REQUEST_DELAY)

    def get_page(self, page_id: str) -> dict[str, Any]:
        return self.request("GET", f"/pages/{page_id}")

    def trash_page(self, page_id: str) -> None:
        self.request("PATCH", f"/pages/{page_id}", {"in_trash": True})

    def recreate_page(self, old_page_id: str, post: dict[str, Any]) -> dict[str, Any]:
        old_page = self.get_page(old_page_id)
        extra_properties = relation_properties(old_page)
        new_page = self.create_page(post["title"], post["date"], post["categories"], extra_properties)
        try:
            self.append_children(new_page["id"], post["blocks"])
        except Exception:
            self.trash_page(new_page["id"])
            raise
        self.trash_page(old_page_id)
        return new_page


def relation_properties(page: dict[str, Any]) -> dict[str, Any]:
    props: dict[str, Any] = {}
    for name in ("게시판", "프로젝트"):
        prop = page.get("properties", {}).get(name, {})
        if prop.get("type") != "relation":
            continue
        relation = [{"id": item["id"]} for item in prop.get("relation", []) if item.get("id")]
        if relation:
            props[name] = {"relation": relation}
    return props


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def chunks(text: str, limit: int = MAX_TEXT) -> list[str]:
    if not text:
        return []
    out = []
    while text:
        out.append(text[:limit])
        text = text[limit:]
    return out


def plain_rt(text: str) -> list[dict[str, Any]]:
    return [{"type": "text", "text": {"content": part}} for part in chunks(text)]


def append_text_rich(
    out: list[dict[str, Any]],
    text: str,
    *,
    bold: bool = False,
    code: bool = False,
    link_url: str | None = None,
) -> None:
    if not text:
        return
    for part in chunks(text):
        item: dict[str, Any] = {"type": "text", "text": {"content": part}}
        if link_url:
            item["text"]["link"] = {"url": link_url}
        annotations: dict[str, Any] = {}
        if bold:
            annotations["bold"] = True
        if code:
            annotations["code"] = True
        if annotations:
            item["annotations"] = annotations
        out.append(item)


def append_equation_rich(out: list[dict[str, Any]], expr: str) -> None:
    expr = expr.strip()
    if not expr:
        return
    if "\n" in expr or len(expr) > 900:
        append_text_rich(out, expr, code=True)
        return
    out.append({"type": "equation", "equation": {"expression": expr}})


def find_unescaped(text: str, needle: str, start: int) -> int:
    idx = start
    while True:
        idx = text.find(needle, idx)
        if idx == -1:
            return -1
        backslashes = 0
        j = idx - 1
        while j >= 0 and text[j] == "\\":
            backslashes += 1
            j -= 1
        if backslashes % 2 == 0:
            return idx
        idx += len(needle)


def first_unescaped(text: str, needles: set[str], start: int) -> int:
    idx = start
    while idx < len(text):
        if text[idx] not in needles:
            idx += 1
            continue
        backslashes = 0
        j = idx - 1
        while j >= 0 and text[j] == "\\":
            backslashes += 1
            j -= 1
        if backslashes % 2 == 0:
            return idx
        idx += 1
    return -1


def find_link_url_end(text: str, start: int) -> int:
    depth = 0
    idx = start
    while idx < len(text):
        char = text[idx]
        backslashes = 0
        j = idx - 1
        while j >= 0 and text[j] == "\\":
            backslashes += 1
            j -= 1
        escaped = backslashes % 2 == 1
        if not escaped:
            if char == "(":
                depth += 1
            elif char == ")":
                if depth == 0:
                    return idx
                depth -= 1
        idx += 1
    return -1


def append_bold_rich(out: list[dict[str, Any]], rich: list[dict[str, Any]]) -> None:
    for item in rich:
        cloned = copy.deepcopy(item)
        annotations = cloned.setdefault("annotations", {})
        annotations["bold"] = True
        out.append(cloned)


def append_link_rich(
    out: list[dict[str, Any]],
    label: str,
    link_url: str,
    post: Path | None = None,
    manifest_items: dict[str, Any] | None = None,
) -> None:
    rich = inline_rt(label, post, manifest_items)
    if not rich:
        append_text_rich(out, label, link_url=link_url)
        return
    for item in rich:
        cloned = copy.deepcopy(item)
        if cloned.get("type") == "text":
            cloned.setdefault("text", {})["link"] = {"url": link_url}
        out.append(cloned)


def manifest_page_url_for_path(
    target: Path,
    manifest_items: dict[str, Any] | None,
) -> str | None:
    if not manifest_items:
        return None

    candidates = [target]
    if target.suffix.lower() == ".html":
        candidates.extend([target.with_suffix(".md"), target.with_suffix(".qmd")])
    elif not target.suffix:
        candidates.extend([target / "index.md", target / "index.qmd"])

    for candidate in candidates:
        try:
            rel = candidate.resolve().relative_to(POSTS_ROOT.resolve()).as_posix()
        except ValueError:
            continue
        item = manifest_items.get(rel)
        if item and item.get("url"):
            return item["url"]
    return None


def public_local_url(target: Path, query: str = "", fragment: str = "") -> str | None:
    try:
        rel = target.relative_to(ROOT).as_posix()
    except ValueError:
        return None
    if target.suffix.lower() in {".md", ".qmd"}:
        rel = str(Path(rel).with_suffix(".html")).replace("\\", "/")
    encoded_path = "/".join(urllib.parse.quote(part) for part in ("/" + rel).split("/"))
    url = urllib.parse.urljoin(SITE_URL, encoded_path)
    if query:
        url += "?" + query
    if fragment:
        url += "#" + urllib.parse.quote(fragment, safe="/:?=&%")
    return url


def public_site_output_url(target: Path, query: str = "", fragment: str = "") -> str | None:
    try:
        rel = target.relative_to(SITE_ROOT).as_posix()
    except ValueError:
        return None
    encoded_path = "/".join(urllib.parse.quote(part) for part in ("/" + rel).split("/"))
    url = urllib.parse.urljoin(SITE_URL, encoded_path)
    if query:
        url += "?" + query
    if fragment:
        url += "#" + urllib.parse.quote(fragment, safe="/:?=&%")
    return url if len(url) <= 1900 else None


def rendered_qmd_pdf(path: Path) -> Path | None:
    if path.suffix.lower() != ".qmd":
        return None
    try:
        rel = path.relative_to(POSTS_ROOT)
    except ValueError:
        return None
    candidate = (SITE_ROOT / "posts" / rel).with_suffix(".pdf")
    return candidate if candidate.exists() else None


def public_post_url(post: Path, fragment: str = "") -> str | None:
    url = public_local_url(post, fragment=fragment)
    return url


def normalize_link_url(
    raw: str,
    post: Path | None = None,
    manifest_items: dict[str, Any] | None = None,
) -> str | None:
    href = raw.strip()
    if not href:
        return None
    if href.startswith("<") and href.endswith(">"):
        href = href[1:-1].strip()
    if re.search(r"\s", href):
        href = href.split(None, 1)[0]

    lowered = href.lower()
    if lowered.startswith(("javascript:", "data:")):
        return None
    if lowered.startswith(("http://", "https://", "mailto:", "tel:")):
        return href if len(href) <= 1900 else None

    split = urllib.parse.urlsplit(href)
    if split.scheme:
        return href if len(href) <= 1900 else None

    if split.path == "" and split.fragment and post:
        url = public_post_url(post, split.fragment)
        return url if url and len(url) <= 1900 else None

    if not post:
        return None

    if split.path.startswith("/"):
        target = ROOT / urllib.parse.unquote(split.path.lstrip("/"))
    else:
        target = post.parent / urllib.parse.unquote(split.path)

    if not split.query and not split.fragment:
        page_url = manifest_page_url_for_path(target, manifest_items)
        if page_url:
            return page_url if len(page_url) <= 1900 else None

    url = public_local_url(target, split.query, split.fragment)
    return url if url and len(url) <= 1900 else None


def inline_rt(
    text: str,
    post: Path | None = None,
    manifest_items: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Convert common Markdown inline spans to Notion rich text."""
    out: list[dict[str, Any]] = []
    buf: list[str] = []
    i = 0

    def flush() -> None:
        nonlocal buf
        if buf:
            append_text_rich(out, "".join(buf))
            buf = []

    while i < len(text):
        char = text[i]

        if char == "`":
            run_end = i
            while run_end < len(text) and text[run_end] == "`":
                run_end += 1
            marker = text[i:run_end]
            close = text.find(marker, run_end)
            if close != -1:
                flush()
                append_text_rich(out, text[run_end:close], code=True)
                i = close + len(marker)
                continue

        if text.startswith("**", i) and (i == 0 or text[i - 1] != "\\"):
            close = find_unescaped(text, "**", i + 2)
            if close != -1 and close > i + 2:
                flush()
                append_bold_rich(out, inline_rt(text[i + 2 : close], post, manifest_items))
                i = close + 2
                continue

        if char == "$" and (i == 0 or text[i - 1] != "\\"):
            if text.startswith("$$", i):
                close = find_unescaped(text, "$$", i + 2)
                if close != -1:
                    flush()
                    append_equation_rich(out, text[i + 2 : close])
                    i = close + 2
                    continue
            else:
                close = find_unescaped(text, "$", i + 1)
                if close != -1 and not text.startswith("$", close + 1):
                    expr = text[i + 1 : close].strip()
                    if expr:
                        flush()
                        append_equation_rich(out, expr)
                        i = close + 1
                        continue

        if char == "[" and (i == 0 or text[i - 1] not in {"\\", "!"}):
            close_label = find_unescaped(text, "]", i + 1)
            if close_label != -1 and close_label + 1 < len(text) and text[close_label + 1] == "(":
                close_url = find_link_url_end(text, close_label + 2)
                if close_url != -1:
                    label = text[i + 1 : close_label]
                    raw_url = text[close_label + 2 : close_url]
                    link_url = normalize_link_url(raw_url, post, manifest_items)
                    if link_url:
                        flush()
                        append_link_rich(out, label, link_url, post, manifest_items)
                        i = close_url + 1
                        continue

        buf.append(char)
        i += 1

    flush()
    return out


def rich_text_blocks(
    kind: str,
    text: str,
    post: Path | None = None,
    manifest_items: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    rich = inline_rt(text, post, manifest_items)
    if not rich:
        return []
    blocks = []
    for i in range(0, len(rich), MAX_RICH_TEXT):
        blocks.append({"object": "block", "type": kind, kind: {"rich_text": rich[i : i + MAX_RICH_TEXT]}})
    return blocks


def paragraph(
    text: str,
    post: Path | None = None,
    manifest_items: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return rich_text_blocks("paragraph", text, post, manifest_items)


def simple_block(
    kind: str,
    text: str,
    post: Path | None = None,
    manifest_items: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if not text:
        return []
    return rich_text_blocks(kind, text, post, manifest_items)


def code_block(text: str, language: str = "plain text") -> dict[str, Any]:
    lang = language.lower().strip() or "plain text"
    lang = {
        "py": "python",
        "sh": "shell",
        "zsh": "shell",
        "console": "shell",
        "yml": "yaml",
        "js": "javascript",
        "ts": "typescript",
        "md": "markdown",
        "quarto": "markdown",
    }.get(lang, lang)
    if lang not in LANGUAGES:
        lang = "plain text"
    return {"object": "block", "type": "code", "code": {"rich_text": plain_rt(text), "language": lang}}


def heading(
    level: int,
    text: str,
    post: Path | None = None,
    manifest_items: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    kind = {1: "heading_1", 2: "heading_2"}.get(level, "heading_3")
    return rich_text_blocks(kind, text, post, manifest_items)


def divider() -> dict[str, Any]:
    return {"object": "block", "type": "divider", "divider": {}}


def image_block(
    url: str,
    caption: str = "",
    post: Path | None = None,
    manifest_items: dict[str, Any] | None = None,
) -> dict[str, Any]:
    block = {"object": "block", "type": "image", "image": {"type": "external", "external": {"url": url}}}
    if caption:
        block["image"]["caption"] = inline_rt(caption[:1900], post, manifest_items)
    return block


def pdf_block(
    url: str,
    caption: str = "",
    post: Path | None = None,
    manifest_items: dict[str, Any] | None = None,
) -> dict[str, Any]:
    block = {"object": "block", "type": "pdf", "pdf": {"type": "external", "external": {"url": url}}}
    if caption:
        block["pdf"]["caption"] = inline_rt(caption[:1900], post, manifest_items)
    return block


def equation_block(expr: str) -> dict[str, Any]:
    if len(expr) > 900:
        return code_block(expr, "latex")
    return {"object": "block", "type": "equation", "equation": {"expression": expr}}


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    try:
        meta = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        meta = {}
    return meta if isinstance(meta, dict) else {}, parts[2].lstrip("\n")


def load_inherited_metadata(path: Path) -> dict[str, Any]:
    current: dict[str, Any] = {}
    rel_parent = path.parent.relative_to(POSTS_ROOT)
    dirs = [POSTS_ROOT]
    acc = POSTS_ROOT
    for part in rel_parent.parts:
        acc = acc / part
        dirs.append(acc)
    for directory in dirs:
        meta_file = directory / "_metadata.yml"
        if not meta_file.exists():
            continue
        try:
            data = yaml.safe_load(meta_file.read_text()) or {}
        except yaml.YAMLError:
            data = {}
        if isinstance(data, dict):
            current.update(data)
    return current


def normalize_date(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (dt.date, dt.datetime)):
        return value.date().isoformat() if isinstance(value, dt.datetime) else value.isoformat()
    text = str(value).strip().strip('"').strip("'")
    if text == "last-modified":
        return None
    match = re.match(r"^(\d{4}-\d{2}-\d{2})", text)
    return match.group(1) if match else None


def normalize_categories(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, list):
        items = value
    else:
        items = [str(value)]
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        for part in str(item).split(","):
            text = part.strip().strip('"').strip("'")
            if not text or text in seen:
                continue
            seen.add(text)
            out.append(text)
    return out


def title_from_body(body: str, fallback: str) -> str:
    match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return fallback.replace("_", " ").replace("-", " ").strip() or "Untitled"


def post_files() -> list[Path]:
    return sorted(
        p
        for p in POSTS_ROOT.rglob("*")
        if p.is_file()
        and p.suffix.lower() in {".md", ".qmd"}
        and p.name != "_metadata.yml"
        and "/notes/" in p.as_posix()
    )


def has_rendering_spans(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")
    return bool(
        re.search(r"`[^`\n]+`", text)
        or re.search(r"(?<!\$)\$[^$\n]+\$(?!\$)", text)
        or re.search(r"\$\$[^$\n].*\$\$", text)
        or re.search(r"!\[[^\]\n]*\]\([^)]+\)\s*\{[^}\n]*\.post-thumbnail[^}\n]*\}", text)
        or re.search(r"(?<!!)(?<!\\)\[[^\]\n]+\]\([^)]+\)", text)
        or has_formatting_spans(path)
    )


def has_formatting_spans(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")
    return bool(
        re.search(r"(?<!\*)\*\*[^*\n][\s\S]*?\*\*(?!\*)", text)
        or re.search(r"(?is)<iframe\b[^>]*\bsrc\s*=\s*['\"][^'\"]+\.pdf(?:[#?][^'\"]*)?['\"]", text)
        or re.search(
            r"(?im)^\s*(?:[-*+]\s+)?\[[^\]\n]+\]\((?!https?://|mailto:|tel:)[^)]+\.pdf(?:[#?][^)]*)?\)\s*$",
            text,
        )
    )


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def public_file_url(
    post: Path,
    ref: str,
    *,
    allowed_suffixes: set[str] | None = None,
    allow_external: bool = True,
) -> tuple[str | None, str | None, bool]:
    raw = ref.strip()
    if not raw:
        return None, "empty file ref", False
    if raw.startswith("<") and raw.endswith(">"):
        raw = raw[1:-1].strip()
    if raw.startswith(("http://", "https://")):
        path = urllib.parse.urlsplit(raw).path
        if allowed_suffixes and Path(path).suffix.lower() not in allowed_suffixes:
            return None, f"unsupported external file type: {raw}", False
        if not allow_external:
            return None, f"external file not embedded: {raw}", False
        return raw, None, False
    clean = raw.split("#", 1)[0].split("?", 1)[0]
    if clean.startswith("/"):
        local = ROOT / clean.lstrip("/")
        url_path = clean
    else:
        local = post.parent / urllib.parse.unquote(clean)
        try:
            url_path = "/" + str(local.relative_to(ROOT))
        except ValueError:
            url_path = "/" + str((post.parent / clean).relative_to(ROOT))
    if allowed_suffixes and local.suffix.lower() not in allowed_suffixes:
        return None, f"unsupported local file type: {raw}", True
    if not local.exists():
        return None, f"missing local file: {raw}", True
    encoded = "/".join(urllib.parse.quote(part) for part in url_path.split("/"))
    return urllib.parse.urljoin(SITE_URL, encoded), None, True


def public_image_url(post: Path, ref: str) -> tuple[str | None, str | None]:
    url, err, _ = public_file_url(
        post,
        ref,
        allowed_suffixes={".apng", ".avif", ".gif", ".jpg", ".jpeg", ".png", ".svg", ".webp"},
    )
    if err:
        return None, err.replace("file", "image")
    return url, None


def public_pdf_url(post: Path, ref: str, *, allow_external: bool = True) -> tuple[str | None, str | None, bool]:
    return public_file_url(post, ref, allowed_suffixes={".pdf"}, allow_external=allow_external)


def parse_fence_language(info: str) -> str:
    info = info.strip()
    if not info:
        return "plain text"
    braced = re.match(r"^\{([A-Za-z0-9_+-]+)\}", info)
    if braced:
        return braced.group(1)
    return info.split()[0]


def image_from_line(
    line: str,
    post: Path,
    manifest_items: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, str | None, bool]:
    match = re.fullmatch(r"\s*!\[([^\]]*)\]\(([^)]+)\)\s*(?:\{([^}]*)\})?\s*", line)
    if not match:
        return None, None, False
    caption, ref, attrs = match.groups()
    if attrs and ".post-thumbnail" in attrs:
        return None, None, True
    url, err = public_image_url(post, ref)
    if err:
        return None, err, False
    return image_block(url or ref, caption, post, manifest_items), None, False


def iframe_pdf_from_line(
    line: str,
    post: Path,
    manifest_items: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    match = re.fullmatch(
        r"\s*<iframe\b[^>]*\bsrc\s*=\s*(['\"])(.*?)\1[^>]*>\s*</iframe>\s*",
        line,
        re.IGNORECASE,
    )
    if not match:
        return None, None
    src = match.group(2).strip()
    if Path(urllib.parse.urlsplit(src).path).suffix.lower() != ".pdf":
        return None, f"iframe not imported: {src}"
    url, err, _ = public_pdf_url(post, src, allow_external=True)
    if err:
        return None, err
    caption = Path(urllib.parse.unquote(urllib.parse.urlsplit(src).path)).name
    return pdf_block(url or src, caption, post, manifest_items), None


def standalone_pdf_link_from_line(
    line: str,
    post: Path,
    manifest_items: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    match = re.fullmatch(r"\s*(?:[-*+]\s+)?\[([^\]]+)\]\(([^)]+)\)\s*", line)
    if not match:
        return None, None
    label, ref = match.groups()
    if re.match(r"(?i)^(https?://|mailto:|tel:)", ref.strip()):
        return None, None
    if Path(urllib.parse.urlsplit(ref.strip()).path).suffix.lower() != ".pdf":
        return None, None
    url, err, _ = public_pdf_url(post, ref, allow_external=False)
    if err:
        return None, err
    return pdf_block(url or ref, label.strip(), post, manifest_items), None


def convert_body(
    body: str,
    post: Path,
    manifest_items: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    blocks: list[dict[str, Any]] = []
    warnings: list[str] = []
    paragraph_lines: list[str] = []
    lines = body.splitlines()
    i = 0

    def flush_paragraph() -> None:
        nonlocal paragraph_lines
        text = " ".join(line.strip() for line in paragraph_lines).strip()
        if text:
            blocks.extend(paragraph(text, post, manifest_items))
        paragraph_lines = []

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            flush_paragraph()
            i += 1
            continue

        if stripped.startswith("```"):
            flush_paragraph()
            language = parse_fence_language(stripped[3:])
            buf: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1
            blocks.append(code_block("\n".join(buf), language))
            continue

        if stripped == "$$":
            flush_paragraph()
            buf = []
            i += 1
            while i < len(lines) and lines[i].strip() != "$$":
                buf.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1
            blocks.append(equation_block("\n".join(buf).strip()))
            continue

        if stripped.startswith("$$") and stripped.endswith("$$") and len(stripped) > 4:
            flush_paragraph()
            blocks.append(equation_block(stripped[2:-2].strip()))
            i += 1
            continue

        if stripped.startswith(":::"):
            flush_paragraph()
            title = re.search(r'title\s*=\s*"([^"]+)"', stripped)
            if title:
                blocks.extend(simple_block("quote", title.group(1), post, manifest_items))
            i += 1
            continue

        pdf, warning = iframe_pdf_from_line(line, post, manifest_items)
        if pdf is not None:
            flush_paragraph()
            blocks.append(pdf)
            i += 1
            continue
        if warning:
            flush_paragraph()
            warnings.append(warning)
            blocks.extend(paragraph(f"[Iframe not imported: {warning}]", post, manifest_items))
            i += 1
            continue

        pdf, warning = standalone_pdf_link_from_line(line, post, manifest_items)
        if pdf is not None:
            flush_paragraph()
            blocks.append(pdf)
            i += 1
            continue
        if warning:
            flush_paragraph()
            warnings.append(warning)
            blocks.extend(paragraph(f"[PDF not imported: {warning}]", post, manifest_items))
            i += 1
            continue

        image, warning, skipped = image_from_line(line, post, manifest_items)
        if skipped:
            flush_paragraph()
            i += 1
            continue
        if image is not None:
            flush_paragraph()
            blocks.append(image)
            i += 1
            continue
        if warning:
            flush_paragraph()
            warnings.append(warning)
            blocks.extend(paragraph(f"[Image not imported: {warning}]", post, manifest_items))
            i += 1
            continue

        if re.match(r"^\s*\|.*\|\s*$", line):
            flush_paragraph()
            buf = []
            while i < len(lines) and re.match(r"^\s*\|.*\|\s*$", lines[i]):
                buf.append(lines[i])
                i += 1
            blocks.append(code_block("\n".join(buf), "markdown"))
            continue

        h = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if h:
            flush_paragraph()
            blocks.extend(heading(min(len(h.group(1)), 3), h.group(2), post, manifest_items))
            i += 1
            continue

        if re.match(r"^[-*_]{3,}$", stripped):
            flush_paragraph()
            blocks.append(divider())
            i += 1
            continue

        bullet = re.match(r"^\s*[-*+]\s+(.+)$", line)
        if bullet:
            flush_paragraph()
            blocks.extend(simple_block("bulleted_list_item", bullet.group(1).strip(), post, manifest_items))
            i += 1
            continue

        number = re.match(r"^\s*\d+[.)]\s+(.+)$", line)
        if number:
            flush_paragraph()
            blocks.extend(simple_block("numbered_list_item", number.group(1).strip(), post, manifest_items))
            i += 1
            continue

        quote = re.match(r"^\s*>\s?(.+)$", line)
        if quote:
            flush_paragraph()
            blocks.extend(simple_block("quote", quote.group(1).strip(), post, manifest_items))
            i += 1
            continue

        paragraph_lines.append(line)
        i += 1

    flush_paragraph()
    return blocks, warnings


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "schema": 1,
            "data_source_id": ALL_POSTS_DS,
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "items": {},
        }
    return json.loads(path.read_text())


def save_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")


def build_post(path: Path, manifest_items: dict[str, Any] | None = None) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    file_meta, body = split_frontmatter(raw)
    meta = load_inherited_metadata(path)
    meta.update(file_meta)
    title = str(meta.get("title") or title_from_body(body, path.stem)).strip().strip('"').strip("'")
    date = normalize_date(meta.get("date"))
    categories = normalize_categories(meta.get("categories"))
    rel = path.relative_to(POSTS_ROOT).as_posix()
    blocks, warnings = convert_body(body, path, manifest_items)
    return {
        "path": path,
        "rel": rel,
        "title": title,
        "date": date,
        "categories": categories,
        "hash": content_hash(raw),
        "blocks": blocks,
        "warnings": warnings,
        "bytes": len(raw.encode("utf-8")),
    }


def build_qmd_pdf_post(path: Path, manifest_items: dict[str, Any] | None = None) -> dict[str, Any]:
    post = build_post(path, manifest_items)
    pdf = rendered_qmd_pdf(path)
    if not pdf:
        return post
    url = public_site_output_url(pdf)
    if not url:
        post["warnings"] = [f"rendered PDF URL not available: {pdf}"]
        return post
    post["blocks"] = [pdf_block(url, pdf.name, path, manifest_items)]
    post["warnings"] = []
    post["rendered_pdf"] = pdf.relative_to(ROOT).as_posix()
    return post


def select_posts(args: argparse.Namespace) -> list[Path]:
    files = post_files()
    if args.only:
        wanted = set(args.only)
        files = [p for p in files if p.relative_to(POSTS_ROOT).as_posix() in wanted]
    if args.start_after:
        files = [p for p in files if p.relative_to(POSTS_ROOT).as_posix() > args.start_after]
    if args.limit:
        files = files[: args.limit]
    return files


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write to Notion")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--start-after", default="")
    parser.add_argument("--only", action="append", default=[])
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--recreate-completed", action="store_true")
    parser.add_argument("--rendering-affected", action="store_true")
    parser.add_argument("--formatting-affected", action="store_true")
    parser.add_argument("--qmd-rendered-pdf", action="store_true")
    parser.add_argument("--qmd-pdf-only", action="store_true")
    args = parser.parse_args()

    selected = select_posts(args)
    manifest = load_manifest(args.manifest)
    items = manifest.setdefault("items", {})
    if args.retry_failed:
        failed_paths = {key for key, value in items.items() if value.get("status") == "failed"}
        selected = [p for p in selected if p.relative_to(POSTS_ROOT).as_posix() in failed_paths]
    if args.rendering_affected:
        selected = [p for p in selected if has_rendering_spans(p)]
    if args.formatting_affected:
        selected = [p for p in selected if has_formatting_spans(p)]
    if args.qmd_rendered_pdf:
        selected = [p for p in selected if rendered_qmd_pdf(p)]

    if not args.apply:
        print(f"dry_run posts={len(selected)}")
        for path in selected[:20]:
            post = build_qmd_pdf_post(path, items) if args.qmd_pdf_only else build_post(path, items)
            print(
                f"{post['rel']} | {post['title']} | date={post['date'] or '-'} "
                f"| categories={post['categories']} | blocks={len(post['blocks'])} | warnings={len(post['warnings'])}"
            )
        if len(selected) > 20:
            print(f"... {len(selected) - 20} more")
        return 0

    notion = Notion(load_token())
    notion.ensure_date_property()

    ok = skipped = failed = 0
    for path in selected:
        post = build_qmd_pdf_post(path, items) if args.qmd_pdf_only else build_post(path, items)
        rel = post["rel"]
        current = items.get(rel)
        if current and current.get("status") == "completed" and args.recreate_completed:
            try:
                page = notion.recreate_page(current["page_id"], post)
                items[rel] = {
                    "status": "completed",
                    "page_id": page["id"],
                    "url": page.get("url"),
                    "title": post["title"],
                    "date": post["date"],
                    "categories": post["categories"],
                    "hash": post["hash"],
                    "bytes": post["bytes"],
                    "blocks": len(post["blocks"]),
                    "warnings": post["warnings"],
                    "rendered_pdf": post.get("rendered_pdf"),
                    "replaced_page_id": current.get("page_id"),
                    "recreated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                }
                save_manifest(args.manifest, manifest)
                ok += 1
                print(f"recreated: {rel} -> {page.get('url')}")
                time.sleep(REQUEST_DELAY)
            except Exception as exc:
                failed += 1
                current["refresh_error"] = str(exc)
                current["refresh_failed_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
                save_manifest(args.manifest, manifest)
                print(f"failed recreate: {rel}: {exc}", file=sys.stderr)
            continue
        if current and current.get("status") == "completed":
            if current.get("hash") == post["hash"]:
                skipped += 1
                print(f"skip unchanged: {rel}")
                continue
        if current and current.get("status") == "completed" and current.get("hash") != post["hash"]:
            skipped += 1
            print(f"skip changed existing page: {rel}")
            continue
        try:
            page = notion.create_page(post["title"], post["date"], post["categories"])
            page_id = page["id"]
            notion.append_children(page_id, post["blocks"])
            items[rel] = {
                "status": "completed",
                "page_id": page_id,
                "url": page.get("url"),
                "title": post["title"],
                "date": post["date"],
                "categories": post["categories"],
                "hash": post["hash"],
                "bytes": post["bytes"],
                "blocks": len(post["blocks"]),
                "warnings": post["warnings"],
                "rendered_pdf": post.get("rendered_pdf"),
                "imported_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            }
            save_manifest(args.manifest, manifest)
            ok += 1
            print(f"imported: {rel} -> {page.get('url')}")
            time.sleep(REQUEST_DELAY)
        except Exception as exc:
            failed += 1
            items[rel] = {
                "status": "failed",
                "title": post["title"],
                "date": post["date"],
                "categories": post["categories"],
                "hash": post["hash"],
                "error": str(exc),
                "failed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            }
            save_manifest(args.manifest, manifest)
            print(f"failed: {rel}: {exc}", file=sys.stderr)

    print(f"done imported={ok} skipped={skipped} failed={failed} manifest={args.manifest}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
