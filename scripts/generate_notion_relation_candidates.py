#!/usr/bin/env python3
"""Generate reviewable Area/Project relation candidates for imported posts.

This script is read-only against Notion. It only writes a local JSON file so the
mapping can be reviewed before creating or linking relation pages.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from import_posts_to_notion import (  # noqa: E402
    API,
    BOARD_DS,
    DEFAULT_MANIFEST,
    NOTION_VERSION,
    POSTS_ROOT,
    PROJECTS_DS,
    load_manifest,
    load_token,
    split_frontmatter,
    title_from_body,
)

DEFAULT_OUTPUT = POSTS_ROOT.parent / "notion_relation_candidates.json"


class NotionReadOnly:
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

    def title_property(self, data_source_id: str) -> str:
        meta = self.request("GET", f"/data_sources/{data_source_id}")
        for name, prop in meta.get("properties", {}).items():
            if prop.get("type") == "title":
                return name
        raise RuntimeError(f"No title property found for data source {data_source_id}")

    def page_titles(self, data_source_id: str) -> dict[str, dict[str, Any]]:
        title_prop = self.title_property(data_source_id)
        out: dict[str, dict[str, Any]] = {}
        cursor: str | None = None
        while True:
            body: dict[str, Any] = {"page_size": 100}
            if cursor:
                body["start_cursor"] = cursor
            result = self.request("POST", f"/data_sources/{data_source_id}/query", body)
            for page in result.get("results", []):
                title = title_text(page.get("properties", {}).get(title_prop, {}))
                if title:
                    out[normalize_key(title)] = {"name": title, "page_id": page["id"], "url": page.get("url")}
            if not result.get("has_more"):
                break
            cursor = result.get("next_cursor")
        return out


def title_text(prop: dict[str, Any]) -> str:
    pieces = []
    for item in prop.get("title", []):
        pieces.append(item.get("plain_text") or item.get("text", {}).get("content", ""))
    return "".join(pieces).strip()


def normalize_key(text: str) -> str:
    return re.sub(r"[\s_\-]+", "", text).casefold()


def humanize_slug(slug: str) -> str:
    text = slug.replace("_", " ").replace("-", " ").strip()
    aliases = {
        "air flow": "AirFlow",
        "k8s": "k8s",
        "aws saa": "AWS SAA",
        "sqld": "SQLD",
        "adp 실기": "ADP 실기",
        "adp 필기": "ADP 필기",
        "bs 4 1": "학부 4학년 1학기",
        "bs 3 2": "학부 3학년 2학기",
        "bs 3 1": "학부 3학년 1학기",
        "bs 2 2": "학부 2학년 2학기",
    }
    return aliases.get(text.casefold(), text)


def index_title(collection_dir: Path, fallback_slug: str) -> str:
    for name in ("index.qmd", "index.md"):
        path = collection_dir / name
        if not path.exists():
            continue
        raw = path.read_text(encoding="utf-8", errors="replace")
        meta, body = split_frontmatter(raw)
        title = str(meta.get("title") or title_from_body(body, fallback_slug)).strip().strip('"').strip("'")
        if title:
            return title
    return humanize_slug(fallback_slug)


def candidate_ref(name: str | None, existing: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    if not name:
        return None
    match = existing.get(normalize_key(name))
    return {
        "name": name,
        "existing_page_id": match.get("page_id") if match else None,
        "existing_url": match.get("url") if match else None,
        "needs_create": match is None,
    }


def relation_guess(rel: str) -> dict[str, Any]:
    parts = Path(rel).parts
    source_kind = "unknown"
    project_name: str | None = None
    area_name: str | None = None
    reason: list[str] = []

    def subarea_after_notes(notes_index: int) -> str | None:
        if len(parts) > notes_index + 2:
            return humanize_slug(parts[notes_index + 1])
        return None

    if len(parts) >= 3 and parts[0] == "01_projects":
        source_kind = "active_project"
        project_name = index_title(POSTS_ROOT / parts[0] / parts[1], parts[1])
        area_name = subarea_after_notes(2)
        reason.append("01_projects/<project>/notes maps to 프로젝트")
        if area_name:
            reason.append("first folder below notes maps to area candidate")
    elif len(parts) >= 4 and parts[0] == "03_archives" and parts[1] == "completed_project":
        source_kind = "completed_project"
        project_name = index_title(POSTS_ROOT / parts[0] / parts[1] / parts[2], parts[2])
        area_name = subarea_after_notes(3)
        reason.append("03_archives/completed_project/<project>/notes maps to 프로젝트")
        if area_name:
            reason.append("first folder below notes maps to area candidate")
    elif len(parts) >= 3 and parts[0] == "02_categories":
        source_kind = "category"
        area_name = index_title(POSTS_ROOT / parts[0] / parts[1], parts[1])
        reason.append("02_categories/<area>/notes maps to 게시판/area")
    elif len(parts) >= 4 and parts[0] == "03_archives" and parts[1] == "stored_categories":
        source_kind = "stored_category"
        area_name = index_title(POSTS_ROOT / parts[0] / parts[1] / parts[2], parts[2])
        reason.append("03_archives/stored_categories/<area>/notes maps to 게시판/area")

    return {
        "source_kind": source_kind,
        "project_name": project_name,
        "area_name": area_name,
        "reason": reason,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--no-notion", action="store_true", help="do not query existing Notion relation pages")
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    items = manifest.get("items", {})

    existing_projects: dict[str, dict[str, Any]] = {}
    existing_areas: dict[str, dict[str, Any]] = {}
    if not args.no_notion:
        notion = NotionReadOnly(load_token())
        existing_projects = notion.page_titles(PROJECTS_DS)
        existing_areas = notion.page_titles(BOARD_DS)

    output_items: list[dict[str, Any]] = []
    project_names: set[str] = set()
    area_names: set[str] = set()
    for rel, item in sorted(items.items()):
        if item.get("status") != "completed":
            continue
        guess = relation_guess(rel)
        if guess["project_name"]:
            project_names.add(guess["project_name"])
        if guess["area_name"]:
            area_names.add(guess["area_name"])
        output_items.append(
            {
                "source_path": rel,
                "post_title": item.get("title"),
                "post_page_id": item.get("page_id"),
                "post_url": item.get("url"),
                "source_kind": guess["source_kind"],
                "project": candidate_ref(guess["project_name"], existing_projects),
                "area": candidate_ref(guess["area_name"], existing_areas),
                "reason": guess["reason"],
            }
        )

    projects_to_create = [
        name for name in sorted(project_names) if normalize_key(name) not in existing_projects
    ]
    areas_to_create = [name for name in sorted(area_names) if normalize_key(name) not in existing_areas]
    payload = {
        "schema": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "notion_targets": {
            "post_project_property": "프로젝트",
            "project_data_source_id": PROJECTS_DS,
            "post_area_property": "게시판",
            "area_data_source_id": BOARD_DS,
        },
        "summary": {
            "posts": len(output_items),
            "unique_project_candidates": len(project_names),
            "unique_area_candidates": len(area_names),
            "existing_project_matches": len(project_names) - len(projects_to_create),
            "existing_area_matches": len(area_names) - len(areas_to_create),
            "projects_to_create": len(projects_to_create),
            "areas_to_create": len(areas_to_create),
        },
        "create_candidates": {
            "projects": projects_to_create,
            "areas": areas_to_create,
        },
        "items": output_items,
    }
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(f"wrote {args.output}")
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
