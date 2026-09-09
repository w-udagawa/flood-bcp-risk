#!/usr/bin/env python3
"""Shapefile の .dbf（属性テーブル）を標準ライブラリのみで検査する。

用途（docs/tasks/TASK-006_M1検証ツールキット.md）：
  - V-02: 東京都浸水予想区域図の浸水深階級属性の確認
  - V-05: 国土数値情報 A51 の対象自治体（属性からの確認）
  - A31 の属性確認全般

dBase III/IV 形式（.dbf）のヘッダ・フィールド記述子・レコードをバイナリで
パースする。GIS ライブラリ（geopandas / pyshp 等）は使わない。

対応フィールド型：
  C (Character), N (Numeric), F (Float), L (Logical), D (Date)
  M (Memo) 等その他の型は「型のみ」表示し、値は生のバイト長情報のみ扱う
  （本ツールの用途ではメモフィールドの中身までは不要なため）。

文字コード：既定 cp932（Shift_JIS 系）。デコードに失敗した場合は utf-8 で
再試行し、それでも失敗したフィールドは replace で読み替える。

zip をそのまま指定した場合は、中に含まれる .dbf を探して読む
（複数ある場合は --member で選択、省略時は最初に見つかったもの）。

ネットワークは一切使用しない。
"""

from __future__ import annotations

import argparse
import io
import json
import struct
import sys
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from typing import BinaryIO, Optional

FIELD_DESCRIPTOR_SIZE = 32
HEADER_TERMINATOR = 0x0D


@dataclass
class FieldDef:
    name: str
    type_code: str
    length: int
    decimal_count: int


@dataclass
class FieldStats:
    field: FieldDef
    non_null_count: int = 0
    total_count: int = 0
    top_values: list = field(default_factory=list)  # [(value, count), ...]
    unique_count: int = 0

    @property
    def non_null_rate(self) -> float:
        if self.total_count == 0:
            return 0.0
        return self.non_null_count / self.total_count

    def to_json(self) -> dict:
        return {
            "name": self.field.name,
            "type": self.field.type_code,
            "length": self.field.length,
            "decimal_count": self.field.decimal_count,
            "total_count": self.total_count,
            "non_null_count": self.non_null_count,
            "non_null_rate": round(self.non_null_rate, 4),
            "unique_count": self.unique_count,
            "top_values": [
                {"value": v, "count": c} for v, c in self.top_values
            ],
        }


class DbfParseError(RuntimeError):
    pass


def _read_dbf_header(fh: BinaryIO) -> tuple[int, int, int, int]:
    """32 バイトのヘッダを読み、(version, record_count, header_len, record_len) を返す。"""
    raw = fh.read(32)
    if len(raw) != 32:
        raise DbfParseError("ファイルが短すぎて dBase ヘッダ（32バイト）を読めません")
    version = raw[0]
    record_count = struct.unpack_from("<I", raw, 4)[0]
    header_len = struct.unpack_from("<H", raw, 8)[0]
    record_len = struct.unpack_from("<H", raw, 10)[0]
    return version, record_count, header_len, record_len


def _read_field_defs(fh: BinaryIO, header_len: int) -> list[FieldDef]:
    fields: list[FieldDef] = []
    # フィールド記述子は 32 バイトオフセット 32 から始まり、0x0D で終端する。
    while True:
        pos = fh.tell()
        if pos >= header_len - 1:
            break
        first_byte = fh.read(1)
        if not first_byte:
            break
        if first_byte[0] == HEADER_TERMINATOR:
            break
        rest = fh.read(FIELD_DESCRIPTOR_SIZE - 1)
        if len(rest) != FIELD_DESCRIPTOR_SIZE - 1:
            raise DbfParseError("フィールド記述子の読み込みに失敗しました")
        raw = first_byte + rest
        name_raw = raw[0:11].split(b"\x00", 1)[0]
        type_code = chr(raw[11])
        length = raw[16]
        decimal_count = raw[17]
        fields.append(
            FieldDef(
                name=name_raw.decode("ascii", errors="replace"),
                type_code=type_code,
                length=length,
                decimal_count=decimal_count,
            )
        )
    return fields


def _decode(raw: bytes, encoding: str) -> str:
    try:
        return raw.decode(encoding)
    except (UnicodeDecodeError, LookupError):
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode(encoding, errors="replace")


def _is_null_value(type_code: str, text: str) -> bool:
    """トリム後の値が「非 null」とみなせるかどうかを判定する。"""
    if type_code == "L":
        return text in ("", "?")
    return text == ""


def parse_dbf(
    fh: BinaryIO,
    *,
    encoding: str = "cp932",
    top_n: int = 20,
) -> dict:
    version, record_count, header_len, record_len = _read_dbf_header(fh)
    fh.seek(32)
    field_defs = _read_field_defs(fh, header_len)

    # フィールド記述子の後、ヘッダ終端（0x0D）までシークしてからレコード部へ。
    fh.seek(header_len)

    stats = {f.name: FieldStats(field=f) for f in field_defs}
    counters = {f.name: Counter() for f in field_defs}

    actual_records = 0
    while True:
        record = fh.read(record_len)
        if len(record) < record_len:
            break
        delete_flag = record[0:1]
        offset = 1
        actual_records += 1
        is_deleted = delete_flag == b"\x2a"
        for f in field_defs:
            raw = record[offset : offset + f.length]
            offset += f.length
            text = _decode(raw, encoding).strip()
            st = stats[f.name]
            st.total_count += 1
            if is_deleted:
                # 削除済みレコードは集計対象に含めるが値としては数える
                # （dBase は物理削除しないため）。null 判定のみそのまま適用。
                pass
            if not _is_null_value(f.type_code, text):
                st.non_null_count += 1
                counters[f.name][text] += 1

    for f in field_defs:
        st = stats[f.name]
        counter = counters[f.name]
        st.unique_count = len(counter)
        st.top_values = counter.most_common(top_n)

    return {
        "dbase_version": version,
        "encoding": encoding,
        "declared_record_count": record_count,
        "actual_record_count": actual_records,
        "record_length": record_len,
        "header_length": header_len,
        "fields": [stats[f.name].to_json() for f in field_defs],
    }


def _open_dbf_bytes(path: str, member: Optional[str]) -> tuple[bytes, str]:
    """path が .dbf ならそのまま、.zip なら中の .dbf を探して bytes を返す。

    戻り値: (bytes, 実際に読んだファイル名)
    """
    if path.lower().endswith(".zip"):
        with zipfile.ZipFile(path) as zf:
            names = [n for n in zf.namelist() if n.lower().endswith(".dbf")]
            if not names:
                raise DbfParseError(f"zip 内に .dbf が見つかりません: {path}")
            if member:
                candidates = [n for n in names if n == member or n.endswith("/" + member)]
                if not candidates:
                    raise DbfParseError(
                        f"zip 内に指定された member が見つかりません: {member}（候補: {names}）"
                    )
                chosen = candidates[0]
            else:
                if len(names) > 1:
                    sys.stderr.write(
                        f"[警告] zip 内に .dbf が複数あります。最初のものを使用します: {names[0]}"
                        f"（候補: {names}）\n"
                    )
                chosen = names[0]
            return zf.read(chosen), chosen
    with open(path, "rb") as f:
        return f.read(), path


def render_text_report(result: dict, path: str) -> str:
    lines = []
    lines.append(f"ファイル: {path}")
    lines.append(
        f"dBase version: 0x{result['dbase_version']:02X}  "
        f"文字コード: {result['encoding']}"
    )
    lines.append(
        f"レコード数（ヘッダ宣言）: {result['declared_record_count']}  "
        f"レコード数（実読込）: {result['actual_record_count']}"
    )
    lines.append(f"フィールド数: {len(result['fields'])}")
    lines.append("")
    for f in result["fields"]:
        lines.append(
            f"- {f['name']}  type={f['type']}  length={f['length']}  "
            f"decimal={f['decimal_count']}  非null率={f['non_null_rate']:.1%}"
            f"（{f['non_null_count']}/{f['total_count']}）  ユニーク数={f['unique_count']}"
        )
        top = f["top_values"]
        if top:
            preview = ", ".join(f"{v['value']!r}:{v['count']}" for v in top[:10])
            lines.append(f"    上位値: {preview}")
    return "\n".join(lines)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Shapefile の .dbf（属性テーブル）を標準ライブラリのみで検査し、"
            "フィールド一覧・非null率・上位ユニーク値を表示する。"
        )
    )
    parser.add_argument("path", help=".dbf ファイル、または .dbf を含む .zip ファイルのパス")
    parser.add_argument(
        "--encoding",
        default="cp932",
        help="文字コード（既定: cp932）。デコード失敗時は utf-8 で再試行する。",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=20,
        help="各フィールドで表示するユニーク値上位件数（既定: 20）",
    )
    parser.add_argument(
        "--member",
        default=None,
        help="zip 内に複数 .dbf がある場合に選択するファイル名",
    )
    parser.add_argument(
        "--json-out",
        default=None,
        help="集計結果を JSON で書き出すファイルパス（省略時は書き出さない）",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="標準出力へのテキストレポートを抑制する（--json-out と併用想定）",
    )
    return parser


def main(argv: Optional[list] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        raw_bytes, resolved_name = _open_dbf_bytes(args.path, args.member)
    except (DbfParseError, FileNotFoundError, zipfile.BadZipFile) as exc:
        sys.stderr.write(f"エラー: {exc}\n")
        return 1

    try:
        result = parse_dbf(io.BytesIO(raw_bytes), encoding=args.encoding, top_n=args.top_n)
    except DbfParseError as exc:
        sys.stderr.write(f"エラー: .dbf の解析に失敗しました: {exc}\n")
        return 1

    result["source_path"] = args.path
    result["resolved_member"] = resolved_name

    if not args.quiet:
        print(render_text_report(result, resolved_name))

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        if not args.quiet:
            print(f"\nJSON を書き出しました: {args.json_out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
