#!/usr/bin/env python3
"""Create/link Notion project and board relations for imported blog posts."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import time
from pathlib import Path
from typing import Any

import requests


API = "https://api.notion.com/v1"
NOTION_VERSION = "2026-03-11"

ALL_POSTS_DS = "b362ec26-1aaf-836d-9f00-878aa4052db1"
BOARD_DS = "5e22ec26-1aaf-82f0-bd37-0748e90aa957"
PROJECTS_DS = "71370145-e585-4372-805b-7c9b15f57f25"

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "notion_import_manifest.json"

REQUEST_DELAY = 0.15


BOARD_TITLE_PROP = "Name"
BOARD_DESC_PROP = "설명"
PROJECT_TITLE_PROP = "제목"
PROJECT_AREA_PROP = "Area"
POST_BOARD_PROP = "게시판"
POST_PROJECT_PROP = "프로젝트"


BOARDS: dict[str, dict[str, str]] = {
    "IT 인프라": {"description": "AirFlow, Hadoop, Helm, k8s, Terraform, vault"},
    "데이터 분석": {"description": "Machine Learning, Deep Learning, 선형대수, Kaggle, 강화 학습"},
    "42 Seoul": {"description": ""},
    "Block Chain": {"description": ""},
    "Blog": {"description": ""},
    "ROS": {"description": ""},
    "Rust": {"description": ""},
    "금융": {"description": ""},
    "독서": {"description": ""},
}


# Source root under posts/ -> final board name.
AREA_ROOTS: dict[str, str] = {
    "02_categories/42_seoul": "42 Seoul",
    "02_categories/block_chain": "Block Chain",
    "02_categories/deep_learning": "데이터 분석",
    "02_categories/강화_학습": "데이터 분석",
    "02_categories/진로준비": "취업·커리어",
    "03_archives/stored_categories/air_flow": "IT 인프라",
    "03_archives/stored_categories/blog": "Blog",
    "03_archives/stored_categories/hadoop": "IT 인프라",
    "03_archives/stored_categories/helm": "IT 인프라",
    "03_archives/stored_categories/k8s": "IT 인프라",
    "03_archives/stored_categories/kaggle": "데이터 분석",
    "03_archives/stored_categories/machine_learning": "데이터 분석",
    "03_archives/stored_categories/ros": "ROS",
    "03_archives/stored_categories/rust": "Rust",
    "03_archives/stored_categories/terraform": "IT 인프라",
    "03_archives/stored_categories/vault": "IT 인프라",
    "03_archives/stored_categories/금융": "금융",
    "03_archives/stored_categories/독서": "독서",
    "03_archives/stored_categories/선형대수": "데이터 분석",
}


# Source root under posts/ -> (project title to link, board/area title).
# project title may be None when the source project should not become a Notion project.
PROJECT_ROOTS: dict[str, tuple[str | None, str]] = {
    "01_projects/bs_4_1": ("학부 4학년 1학기", "학업"),
    "01_projects/정보처리기사": ("정보처리기사 2026-2 실기", "자격·어학"),
    "03_archives/completed_project/adp_실기": ("ADP 35회 실기", "자격·어학"),
    "03_archives/completed_project/adp_필기": ("ADP 34회 필기", "자격·어학"),
    "03_archives/completed_project/aws_saa": ("AWS SAA 준비", "자격·어학"),
    "03_archives/completed_project/bs_2_2": ("학부 2학년 2학기", "학업"),
    "03_archives/completed_project/bs_3_1": ("학부 3학년 1학기", "학업"),
    "03_archives/completed_project/bs_3_2": ("학부 3학년 2학기", "학업"),
    "03_archives/completed_project/opic": ("오픽(OPIc)", "자격·어학"),
    "03_archives/completed_project/sqld": (None, "자격·어학"),
    "03_archives/completed_project/toeic_speaking": ("토익 스피킹 준비", "자격·어학"),
    "03_archives/completed_project/토익": ("Toeic 준비", "자격·어학"),
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
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            }
        )

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        for attempt in range(6):
            resp = self.session.request(method, API + path, json=body, timeout=60)
            if resp.status_code == 429 and attempt < 5:
                time.sleep(float(resp.headers.get("Retry-After", "1")) + 0.2)
                continue
            if 500 <= resp.status_code < 600 and attempt < 5:
                time.sleep(1.5 * (attempt + 1))
                continue
            if resp.status_code >= 400:
                raise RuntimeError(f"Notion API {resp.status_code} {method} {path}: {resp.text[:1000]}")
            return resp.json() if resp.content else {}
        raise RuntimeError(f"Notion request failed after retries: {method} {path}")

    def query_data_source(self, data_source_id: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            body: dict[str, Any] = {"page_size": 100}
            if cursor:
                body["start_cursor"] = cursor
            data = self.request("POST", f"/data_sources/{data_source_id}/query", body)
            rows.extend(data.get("results", []))
            if not data.get("has_more"):
                return rows
            cursor = data.get("next_cursor")

    def create_board(self, title: str, description: str = "") -> dict[str, Any]:
        props: dict[str, Any] = {
            BOARD_TITLE_PROP: {"title": [{"text": {"content": title}}]},
        }
        if description:
            props[BOARD_DESC_PROP] = {"rich_text": [{"text": {"content": description}}]}
        return self.request("POST", "/pages", {"parent": {"type": "data_source_id", "data_source_id": BOARD_DS}, "properties": props})

    def create_project(self, title: str, board_id: str | None = None) -> dict[str, Any]:
        props: dict[str, Any] = {
            PROJECT_TITLE_PROP: {"title": [{"text": {"content": title}}]},
        }
        if board_id:
            props[PROJECT_AREA_PROP] = {"relation": [{"id": board_id}]}
        return self.request(
            "POST",
            "/pages",
            {"parent": {"type": "data_source_id", "data_source_id": PROJECTS_DS}, "properties": props},
        )

    def patch_post_relations(self, page_id: str, board_id: str | None, project_id: str | None) -> None:
        props: dict[str, Any] = {}
        if board_id:
            props[POST_BOARD_PROP] = {"relation": [{"id": board_id}]}
        if project_id:
            props[POST_PROJECT_PROP] = {"relation": [{"id": project_id}]}
        if props:
            self.request("PATCH", f"/pages/{page_id}", {"properties": props})


def title_of(page: dict[str, Any]) -> str:
    for prop in page.get("properties", {}).values():
        if prop.get("type") == "title":
            return "".join(item.get("plain_text", "") for item in prop.get("title", []))
    return ""


def find_root(rel: str, roots: dict[str, Any]) -> str | None:
    for root in sorted(roots, key=len, reverse=True):
        if rel == root or rel.startswith(root + "/"):
            return root
    return None


def desired_relations(rel: str) -> tuple[str | None, str | None]:
    project_root = find_root(rel, PROJECT_ROOTS)
    if project_root:
        project_title, board_title = PROJECT_ROOTS[project_root]
        return board_title, project_title
    area_root = find_root(rel, AREA_ROOTS)
    if area_root:
        return AREA_ROOTS[area_root], None
    return None, None


def build_plan(
    board_ids: dict[str, str],
    project_ids: dict[str, str],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    items = manifest.get("items", {})
    linked: list[dict[str, str | None]] = []
    skipped: list[str] = []
    needed_boards: set[str] = set()
    needed_projects: set[str] = set()
    for rel, item in sorted(items.items()):
        if item.get("status") != "completed":
            continue
        board_title, project_title = desired_relations(rel)
        if not board_title and not project_title:
            skipped.append(rel)
            continue
        if board_title and board_title not in board_ids:
            needed_boards.add(board_title)
        if project_title and project_title not in project_ids:
            needed_projects.add(project_title)
        linked.append({"rel": rel, "board": board_title, "project": project_title, "page_id": item.get("page_id")})
    return {
        "linked": linked,
        "skipped": skipped,
        "needed_boards": sorted(needed_boards),
        "needed_projects": sorted(needed_projects),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    manifest = json.loads(MANIFEST.read_text())
    notion = Notion(load_token())
    boards = notion.query_data_source(BOARD_DS)
    projects = notion.query_data_source(PROJECTS_DS)
    board_ids = {title_of(page): page["id"] for page in boards if title_of(page)}
    project_ids = {title_of(page): page["id"] for page in projects if title_of(page)}

    plan = build_plan(board_ids, project_ids, manifest)

    print(f"will_link_posts={len(plan['linked'])}")
    print(f"skipped_posts={len(plan['skipped'])}")
    print("will_create_boards=" + json.dumps(plan["needed_boards"], ensure_ascii=False))
    print("will_create_projects=" + json.dumps(plan["needed_projects"], ensure_ascii=False))

    by_board: dict[str, int] = {}
    by_project: dict[str, int] = {}
    for row in plan["linked"]:
        if row["board"]:
            by_board[row["board"]] = by_board.get(row["board"], 0) + 1
        if row["project"]:
            by_project[row["project"]] = by_project.get(row["project"], 0) + 1
    print("posts_by_board=" + json.dumps(dict(sorted(by_board.items())), ensure_ascii=False))
    print("posts_by_project=" + json.dumps(dict(sorted(by_project.items())), ensure_ascii=False))

    if not args.apply:
        if plan["skipped"]:
            print("skipped_sample=" + json.dumps(plan["skipped"][:20], ensure_ascii=False))
        return 0

    for board_title in plan["needed_boards"]:
        page = notion.create_board(board_title, BOARDS.get(board_title, {}).get("description", ""))
        board_ids[board_title] = page["id"]
        print(f"created board: {board_title} {page['id']}")
        time.sleep(REQUEST_DELAY)

    for project_title in plan["needed_projects"]:
        board_title = next((board for project, board in PROJECT_ROOTS.values() if project == project_title), None)
        page = notion.create_project(project_title, board_ids.get(board_title or ""))
        project_ids[project_title] = page["id"]
        print(f"created project: {project_title} {page['id']}")
        time.sleep(REQUEST_DELAY)

    linked_count = 0
    for row in plan["linked"]:
        page_id = row["page_id"]
        if not page_id:
            continue
        notion.patch_post_relations(
            str(page_id),
            board_ids.get(str(row["board"])) if row["board"] else None,
            project_ids.get(str(row["project"])) if row["project"] else None,
        )
        linked_count += 1
        if linked_count % 25 == 0:
            print(f"linked posts: {linked_count}")
        time.sleep(REQUEST_DELAY)

    manifest["relations"] = {
        "linked_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "strategy": "project roots plus status-area roots; 진로 준비 -> 취업·커리어; SQLD project omitted",
        "linked_posts": linked_count,
        "skipped_posts": len(plan["skipped"]),
        "boards": by_board,
        "projects": by_project,
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(f"done linked={linked_count} skipped={len(plan['skipped'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
