#!/usr/bin/env python3
"""Add descriptions, icons, and project statuses for linked blog relations."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

import requests
import yaml


API = "https://api.notion.com/v1"
NOTION_VERSION = "2026-03-11"

BOARD_DS = "5e22ec26-1aaf-82f0-bd37-0748e90aa957"
PROJECTS_DS = "71370145-e585-4372-805b-7c9b15f57f25"

ROOT = Path(__file__).resolve().parents[1]
POSTS_ROOT = ROOT / "posts"

REQUEST_DELAY = 0.15

BOARD_TITLE_PROP = "Name"
BOARD_DESC_PROP = "설명"
PROJECT_TITLE_PROP = "제목"
PROJECT_DESC_PROP = "설명"
PROJECT_STATUS_PROP = "상태"

STATUS_MAP = {
    "before-start": "예정",
    "on-going": "진행 중",
    "completed": "완료",
    "failed": "보류·취소",
}

BOARD_UPDATES: dict[str, dict[str, str]] = {
    "학업": {"icon": "🎓", "description": "학부 수업, 학기별 과제, 전공 개념 정리"},
    "자격·어학": {"icon": "📜", "description": "자격증, 어학 시험, 시험 준비 기록"},
    "취업·커리어": {"icon": "💼", "description": "진로 준비, 커리어 자료, 프로젝트 아이디어 스크랩"},
    "42 Seoul": {"icon": "💻", "description": "42 Seoul에서 진행한 프로젝트들에 대한 노트 모음"},
    "Block Chain": {"icon": "⛓️", "description": "블록체인 관련 개념과 실습 노트"},
    "Blog": {"icon": "✍️", "description": "블로그 운영과 글쓰기 관련 노트"},
    "IT 인프라": {
        "icon": "🛠️",
        "description": "AirFlow, Hadoop, Helm, k8s, Terraform, Vault 등 인프라와 DevOps 정리 노트",
    },
    "데이터 분석": {
        "icon": "📊",
        "description": "Machine Learning, Deep Learning, 선형대수, Kaggle, 강화 학습 관련 노트",
    },
    "ROS": {"icon": "🤖", "description": "ROS 관련 노트"},
    "Rust": {"icon": "⚙️", "description": "Rust 관련 노트"},
    "금융": {"icon": "💰", "description": "금융 관련 노트"},
    "독서": {"icon": "📚", "description": "독서 관련 기록과 노트"},
}

# Notion project title -> source index.qmd path and icon.
PROJECT_SOURCES: dict[str, tuple[str, str]] = {
    "학부 4학년 1학기": ("01_projects/bs_4_1/index.qmd", "🎓"),
    "정보처리기사 2026-2 실기": ("01_projects/정보처리기사/index.qmd", "💻"),
    "ADP 35회 실기": ("03_archives/completed_project/adp_실기/index.qmd", "📊"),
    "ADP 34회 필기": ("03_archives/completed_project/adp_필기/index.qmd", "📊"),
    "AWS SAA 준비": ("03_archives/completed_project/aws_saa/index.qmd", "☁️"),
    "학부 2학년 2학기": ("03_archives/completed_project/bs_2_2/index.qmd", "🎓"),
    "학부 3학년 1학기": ("03_archives/completed_project/bs_3_1/index.qmd", "🎓"),
    "학부 3학년 2학기": ("03_archives/completed_project/bs_3_2/index.qmd", "🎓"),
    "오픽(OPIc)": ("03_archives/completed_project/opic/index.qmd", "💬"),
    "Toeic 준비": ("03_archives/completed_project/토익/index.qmd", "💬"),
    "토익 스피킹 준비": ("03_archives/completed_project/toeic_speaking/index.qmd", "💬"),
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

    def patch_page(self, page_id: str, body: dict[str, Any]) -> None:
        self.request("PATCH", f"/pages/{page_id}", body)


def split_frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta = yaml.safe_load(parts[1]) or {}
    return (meta if isinstance(meta, dict) else {}), parts[2]


def project_info(path: str) -> dict[str, str]:
    meta, body = split_frontmatter(POSTS_ROOT / path)
    status = str(meta.get("status") or "").strip().strip('"').strip("'")
    description = str(meta.get("description") or details_sentence(body) or "").strip()
    return {
        "source_title": str(meta.get("title") or "").strip(),
        "description": description,
        "status": STATUS_MAP.get(status, ""),
        "raw_status": status,
    }


def details_sentence(body: str) -> str:
    lines = body.splitlines()
    in_details = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            in_details = stripped == "## Details"
            continue
        if in_details and stripped and not stripped.startswith("```"):
            return stripped
    return ""


def title_of(page: dict[str, Any]) -> str:
    for prop in page.get("properties", {}).values():
        if prop.get("type") == "title":
            return "".join(item.get("plain_text", "") for item in prop.get("title", []))
    return ""


def rich_text(content: str) -> list[dict[str, Any]]:
    return [{"type": "text", "text": {"content": content[:1900]}}] if content else []


def board_body(name: str, update: dict[str, str]) -> dict[str, Any]:
    body: dict[str, Any] = {
        "icon": {"type": "emoji", "emoji": update["icon"]},
        "properties": {BOARD_DESC_PROP: {"rich_text": rich_text(update["description"])}},
    }
    return body


def project_body(name: str, source_path: str, icon: str) -> dict[str, Any]:
    info = project_info(source_path)
    props: dict[str, Any] = {
        PROJECT_DESC_PROP: {"rich_text": rich_text(info["description"])},
    }
    if info["status"]:
        props[PROJECT_STATUS_PROP] = {"select": {"name": info["status"]}}
    return {
        "icon": {"type": "emoji", "emoji": icon},
        "properties": props,
        "_debug": info,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    notion = Notion(load_token())
    boards_by_title = {title_of(page): page for page in notion.query_data_source(BOARD_DS)}
    projects_by_title = {title_of(page): page for page in notion.query_data_source(PROJECTS_DS)}

    board_plan = []
    for name, update in BOARD_UPDATES.items():
        page = boards_by_title.get(name)
        if page:
            board_plan.append((name, page["id"], board_body(name, update)))

    project_plan = []
    for name, (source_path, icon) in PROJECT_SOURCES.items():
        page = projects_by_title.get(name)
        if page:
            body = project_body(name, source_path, icon)
            debug = body.pop("_debug")
            project_plan.append((name, page["id"], source_path, debug, body))

    print(f"board_updates={len(board_plan)}")
    for name, page_id, body in board_plan:
        desc = body["properties"][BOARD_DESC_PROP]["rich_text"][0]["text"]["content"]
        print(f"board: {name} {page_id} icon={body['icon']['emoji']} desc={desc}")

    print(f"project_updates={len(project_plan)}")
    for name, page_id, source_path, debug, body in project_plan:
        status = body["properties"].get(PROJECT_STATUS_PROP, {}).get("select", {}).get("name", "-")
        desc = body["properties"][PROJECT_DESC_PROP]["rich_text"][0]["text"]["content"]
        print(f"project: {name} {page_id} icon={body['icon']['emoji']} status={status} source_status={debug['raw_status']} desc={desc}")

    if not args.apply:
        return 0

    for name, page_id, body in board_plan:
        notion.patch_page(page_id, body)
        print(f"updated board: {name}")
        time.sleep(REQUEST_DELAY)

    for name, page_id, _source_path, _debug, body in project_plan:
        notion.patch_page(page_id, body)
        print(f"updated project: {name}")
        time.sleep(REQUEST_DELAY)

    print(f"done board_updates={len(board_plan)} project_updates={len(project_plan)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
