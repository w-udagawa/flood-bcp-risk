#!/usr/bin/env python3
"""地理院標高タイル（dem5a / dem5b / dem1a）の URL 列挙・存在確認ツール。

用途（docs/tasks/TASK-006_M1検証ツールキット.md）：
  - V-03: 対象区（目黒区・世田谷区）の DEM5A/DEM1A 整備状況、標高タイルの最大ズーム

タイル座標の計算は `pipelines/lib/tiles.py`（`pipelines/00_download.py` /
`pipelines/30_terrain.py` と共通）を import して再利用し、重複実装しない。

既定の bbox（目黒区・世田谷区を含む概略範囲）はこのスクリプト内に定数として
置いている。**出典は「概算」であり、行政界データから正確に切り出したもの
ではない**（地理院地図等で目視確認した緯度経度のおおよその範囲）。厳密な
範囲が必要な場合は `--bbox west,south,east,north` で上書きすること。

URL テンプレートは `docs/02_要件定義書.md`・`docs/04_データカタログ.md` に
記載の `https://cyberjapandata.gsi.go.jp/xyz/dem5a/{z}/{x}/{y}.txt` の
パターンを `dem5a`/`dem5b`/`dem1a` に対して展開したもの（タスクカード
TASK-006 本文にも同じパターンが明記されている）。

ネットワークアクセスは `--fetch` を指定したときのみ行う。既定（`--fetch` な
し）では URL 列挙のみを行い、通信は一切発生しない。到達できない環境では
`--fetch` 使用時にその旨を表示して終了する（例外で落ちない）。
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

# pipelines/lib/tiles.py を再利用するため、リポジトリルートを sys.path に追加する。
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from pipelines.lib import tiles  # noqa: E402  (sys.path 設定後の import)

# 目黒区・世田谷区を含む概略 bbox（west, south, east, north）。
# 出典：概算（地理院地図で両区の外形を目視確認したおおよその範囲。
# 行政界ポリゴンからの厳密な算出ではない）。
DEFAULT_BBOX = (139.58, 35.58, 139.72, 35.66)

DEFAULT_ZOOM = 15

DEFAULT_LAYERS = ["dem5a", "dem5b", "dem1a"]

URL_TEMPLATE = "https://cyberjapandata.gsi.go.jp/xyz/{layer}/{z}/{x}/{y}.txt"

FETCH_TIMEOUT_SEC = 5.0


def enumerate_tiles(bbox: tuple[float, float, float, float], zoom: int) -> list[tuple[int, int]]:
    """bbox 内に含まれるタイル座標 (x, y) の一覧を重複なく返す（左上→右下順）。"""
    west, south, east, north = bbox
    x0, y0 = tiles.lonlat_to_tile_xy(west, north, zoom)
    x1, y1 = tiles.lonlat_to_tile_xy(east, south, zoom)
    x_min, x_max = sorted((x0, x1))
    y_min, y_max = sorted((y0, y1))
    result = []
    for y in range(y_min, y_max + 1):
        for x in range(x_min, x_max + 1):
            result.append((x, y))
    return result


def build_urls(
    bbox: tuple[float, float, float, float],
    zoom: int,
    layers: list[str],
    url_template: str = URL_TEMPLATE,
) -> dict:
    tile_xy = enumerate_tiles(bbox, zoom)
    layer_results = {}
    for layer in layers:
        # {layer} 部分だけ先に埋め、z/x/y の埋め込みは tiles.tile_url に任せる
        # （タイル座標計算のロジックを重複実装しないため）。
        layer_template = url_template.replace("{layer}", layer)
        urls = [
            tiles.tile_url(layer_template, zoom, x, y) for (x, y) in tile_xy
        ]
        layer_results[layer] = urls
    return {
        "bbox": list(bbox),
        "bbox_note": "概算（目黒区・世田谷区を含む概略範囲、行政界からの厳密算出ではない）",
        "zoom": zoom,
        "tile_count": len(tile_xy),
        "layers": layer_results,
    }


def probe_url(url: str, timeout: float = FETCH_TIMEOUT_SEC) -> dict:
    """HEAD（失敗時 GET）でタイルの存在を確認する。ネットワーク不通は例外にせず記録する。"""
    req = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {"url": url, "status": resp.status, "reachable": True, "error": None}
    except urllib.error.HTTPError as exc:
        # HEAD が 405 等で拒否される場合は GET で再試行する。
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return {"url": url, "status": resp.status, "reachable": True, "error": None}
        except urllib.error.HTTPError as exc2:
            return {
                "url": url,
                "status": exc2.code,
                "reachable": exc2.code < 400,
                "error": f"HTTPError: {exc2.code}",
            }
        except (urllib.error.URLError, OSError, TimeoutError) as exc2:
            return {"url": url, "status": None, "reachable": False, "error": str(exc2)}
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        return {"url": url, "status": None, "reachable": False, "error": str(exc)}


def fetch_report(url_data: dict, max_per_layer: Optional[int]) -> dict:
    """--fetch 指定時、各レイヤの先頭 max_per_layer 件（既定: 全件）を実際に確認する。

    到達不能な環境（本開発用サンドボックス等）では、最初の 1 件が失敗した時点で
    「到達不能」と判断して残りは試行せず打ち切る（無駄な待ち時間を避ける）。
    """
    report = {}
    network_unreachable = False
    for layer, urls in url_data["layers"].items():
        target_urls = urls if max_per_layer is None else urls[:max_per_layer]
        probes = []
        for url in target_urls:
            if network_unreachable:
                probes.append(
                    {"url": url, "status": None, "reachable": False, "error": "skipped (network unreachable)"}
                )
                continue
            result = probe_url(url)
            probes.append(result)
            if not result["reachable"] and result["error"] and not result["status"]:
                # 最初の 1 件で明確な通信不能（DNS 解決不可・タイムアウト等）が
                # 出た場合はネットワーク自体に到達できないとみなし、以降は打ち切る。
                network_unreachable = True
        reachable_count = sum(1 for p in probes if p["reachable"])
        report[layer] = {
            "probed_count": len(probes),
            "reachable_count": reachable_count,
            "reachable_rate": round(reachable_count / len(probes), 4) if probes else 0.0,
            "probes": probes,
        }
    report["_network_unreachable"] = network_unreachable
    return report


def render_text_report(url_data: dict, fetch_data: Optional[dict]) -> str:
    lines = []
    west, south, east, north = url_data["bbox"]
    lines.append(
        f"bbox（{url_data['bbox_note']}）: west={west} south={south} east={east} north={north}"
    )
    lines.append(f"zoom={url_data['zoom']}  タイル数（1レイヤあたり）={url_data['tile_count']}")
    lines.append("")
    for layer, urls in url_data["layers"].items():
        lines.append(f"=== layer: {layer}（{len(urls)} タイル） ===")
        preview = urls[:5]
        for u in preview:
            lines.append(f"  {u}")
        if len(urls) > len(preview):
            lines.append(f"  ...ほか {len(urls) - len(preview)} 件")
    if fetch_data is not None:
        lines.append("")
        if fetch_data.get("_network_unreachable"):
            lines.append(
                "[到達確認] 外部サイトに到達できませんでした（ネットワーク不通のため、"
                "以降の確認はスキップしました）。ネットワーク制限のない環境で再実行してください。"
            )
        for layer, r in fetch_data.items():
            if layer == "_network_unreachable":
                continue
            lines.append(
                f"[到達確認] {layer}: {r['reachable_count']}/{r['probed_count']} 件が到達可能"
                f"（{r['reachable_rate']:.1%}）"
            )
    return "\n".join(lines)


def parse_bbox(text: str) -> tuple[float, float, float, float]:
    parts = [p.strip() for p in text.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError(
            "--bbox は west,south,east,north の4値をカンマ区切りで指定してください"
        )
    try:
        west, south, east, north = (float(p) for p in parts)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"--bbox の数値変換に失敗しました: {exc}")
    return west, south, east, north


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "緯度経度 bbox とズームから地理院標高タイル（dem5a/dem5b/dem1a）の URL を"
            "列挙する。--fetch 指定時のみ urllib で到達確認する（既定は通信なし）。"
        )
    )
    parser.add_argument(
        "--bbox",
        type=parse_bbox,
        default=DEFAULT_BBOX,
        help=(
            "west,south,east,north（既定: 目黒区・世田谷区を含む概略範囲 "
            f"{','.join(str(v) for v in DEFAULT_BBOX)}、出典は概算）"
        ),
    )
    parser.add_argument("--zoom", type=int, default=DEFAULT_ZOOM, help=f"ズームレベル（既定: {DEFAULT_ZOOM}）")
    parser.add_argument(
        "--layers",
        default=",".join(DEFAULT_LAYERS),
        help=f"カンマ区切りのタイル種別（既定: {','.join(DEFAULT_LAYERS)}）",
    )
    parser.add_argument(
        "--url-template",
        default=URL_TEMPLATE,
        help=f"URL テンプレート（既定: {URL_TEMPLATE}）",
    )
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="urllib で HEAD/GET を実行し実在率を報告する（既定は通信しない）",
    )
    parser.add_argument(
        "--max-per-layer",
        type=int,
        default=10,
        help="--fetch 時にレイヤごとに確認する最大タイル数（既定: 10。過大な通信を避けるため）",
    )
    parser.add_argument("--json-out", default=None, help="結果を JSON で書き出すファイルパス")
    parser.add_argument("--quiet", action="store_true", help="標準出力へのテキストレポートを抑制する")
    return parser


def main(argv: Optional[list] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    layers = [s for s in args.layers.split(",") if s]
    url_data = build_urls(args.bbox, args.zoom, layers, args.url_template)

    fetch_data = None
    if args.fetch:
        fetch_data = fetch_report(url_data, args.max_per_layer)

    if not args.quiet:
        print(render_text_report(url_data, fetch_data))

    if args.json_out:
        payload = dict(url_data)
        if fetch_data is not None:
            payload["fetch"] = fetch_data
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        if not args.quiet:
            print(f"\nJSON を書き出しました: {args.json_out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
