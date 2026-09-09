#!/usr/bin/env python3
"""manifest.json に従ってデータを取得する（自動取得分）／手動取得の指示を表示する。

Requires:
  requests>=2.31  （manual=false かつ URL が具体的なファイルを指す場合のみ。
                    本開発環境では未検証。pipelines/requirements-etl.txt 参照）

本開発環境（PyPI・外部サイトへ到達不可）では実行できない。ローカル環境で

    python3 pipelines/00_download.py --list            # 一覧・要手動取得分を表示
    python3 pipelines/00_download.py --source-id gsi_dem5a_txt --bbox <west,south,east,north> --zoom 15
    python3 pipelines/00_download.py --all --dry-run    # 実行内容の確認のみ

のように使う。

対象データの一覧は `pipelines/manifest.json`。各エントリの `manual: true` は
「サイト上の操作（検索・年度選択・利用規約同意等）が必要なため本スクリプトでは
自動取得しない」ことを意味する。`manual: false` は URL テンプレートを機械的に
埋めて `requests` で取得できることを意味する（現状は地理院標高タイルのみ）。

このスクリプト自身は import 時点では外部サイトへアクセスしない
（禁止事項: 外部サイトへのアクセス試行）。実際の HTTP 取得は
`--source-id` 等で明示的に実行を指示したときのみ、ローカル環境で行われる。
"""

from __future__ import annotations

import argparse
import json
import os
import sys

try:
    import requests  # type: ignore
except ImportError:  # pragma: no cover - この環境では未インストール
    requests = None

from lib import tiles

DEFAULT_MANIFEST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "manifest.json")


def load_manifest(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def is_tile_template(url: str) -> bool:
    return url is not None and "{z}" in url and "{x}" in url and "{y}" in url


def print_manual_instructions(source: dict) -> None:
    print(f"[MANUAL] {source['source_id']}: {source['name']}")
    print(f"  url: {source.get('url')}")
    print(f"  dest_dir: {source.get('dest_dir')}")
    print(f"  expected_filename: {source.get('expected_filename')}")
    print(f"  login_required: {source.get('login_required')}")
    print(f"  license: {source.get('license')}")
    print(f"  notes: {source.get('notes')}")
    print("  -> ブラウザで上記 URL を開き、案内に従って手動でダウンロードし、")
    print(f"     dest_dir 配下（{source.get('dest_dir')}）に配置してください。")
    print()


def list_sources(manifest: dict) -> None:
    for source in manifest["sources"]:
        kind = "MANUAL" if source.get("manual") else "AUTO"
        print(f"{kind:6s} {source['source_id']:35s} {source['name']}")


def download_tile(url_template: str, zoom: int, x: int, y: int, dest_dir: str, ext: str) -> str:
    """1枚のタイルを取得して dest_dir に保存し、保存先パスを返す（要 requests）。"""
    if requests is None:
        raise RuntimeError(
            "requests がインストールされていません。"
            " pip install -r pipelines/requirements-etl.txt を実行してください。"
        )
    url = tiles.tile_url(url_template, zoom, x, y)
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, f"{zoom}_{x}_{y}.{ext}")
    with open(dest_path, "wb") as f:
        f.write(resp.content)
    return dest_path


def download_tiles_for_bbox(
    source: dict, west: float, south: float, east: float, north: float, zoom: int
) -> list[str]:
    """bbox（経度緯度）を覆うタイルを全て取得する。"""
    x0, y0 = tiles.lonlat_to_tile_xy(west, north, zoom)
    x1, y1 = tiles.lonlat_to_tile_xy(east, south, zoom)
    x_lo, x_hi = min(x0, x1), max(x0, x1)
    y_lo, y_hi = min(y0, y1), max(y0, y1)
    url_template = source["url"]
    ext = url_template.rsplit(".", 1)[-1]
    dest_dir = source["dest_dir"]
    paths = []
    for x in range(x_lo, x_hi + 1):
        for y in range(y_lo, y_hi + 1):
            paths.append(download_tile(url_template, zoom, x, y, dest_dir, ext))
    return paths


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--list", action="store_true", help="manifest の一覧を表示して終了")
    parser.add_argument("--source-id", help="取得対象の source_id（未指定なら manual 分の指示を全件表示）")
    parser.add_argument("--bbox", help="west,south,east,north（タイル系ソースの取得範囲、経度緯度）")
    parser.add_argument("--zoom", type=int, default=15, help="タイル系ソースのズームレベル（既定 15）")
    parser.add_argument("--dry-run", action="store_true", help="実際には取得せず、計画のみ表示")
    args = parser.parse_args(argv)

    manifest = load_manifest(args.manifest)

    if args.list:
        list_sources(manifest)
        return 0

    sources = manifest["sources"]
    if args.source_id:
        sources = [s for s in sources if s["source_id"] == args.source_id]
        if not sources:
            print(f"source_id '{args.source_id}' は manifest に見つかりません。", file=sys.stderr)
            return 1

    for source in sources:
        if source.get("manual"):
            print_manual_instructions(source)
            continue

        url = source.get("url")
        if not is_tile_template(url):
            print(f"[SKIP] {source['source_id']}: manual=false だが URL テンプレートではありません。手動で確認してください: {url}")
            continue

        if not args.bbox:
            print(
                f"[SKIP] {source['source_id']} はタイル取得ソースです。"
                " --bbox west,south,east,north --zoom Z を指定して実行してください。"
            )
            continue

        west, south, east, north = (float(v) for v in args.bbox.split(","))
        if args.dry_run:
            x0, y0 = tiles.lonlat_to_tile_xy(west, north, args.zoom)
            x1, y1 = tiles.lonlat_to_tile_xy(east, south, args.zoom)
            n_tiles = (abs(x1 - x0) + 1) * (abs(y1 - y0) + 1)
            print(f"[DRY-RUN] {source['source_id']}: zoom={args.zoom} で約 {n_tiles} タイルを {source['dest_dir']} に取得予定")
            continue

        paths = download_tiles_for_bbox(source, west, south, east, north, args.zoom)
        print(f"[OK] {source['source_id']}: {len(paths)} タイルを取得しました -> {source['dest_dir']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
