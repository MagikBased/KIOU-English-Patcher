#!/usr/bin/env python3
"""Export Texture2D atlases and optional Sprite crops from Unity bundles."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path
from typing import Any

import UnityPy
from PIL import Image, ImageDraw, ImageFont


SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def safe_name(value: str, fallback: str = "unnamed", limit: int = 80) -> str:
    value = SAFE_NAME_RE.sub("_", value.strip()).strip("._-")
    if not value:
        value = fallback
    return value[:limit]


def object_name(data: Any) -> str:
    return getattr(data, "name", None) or getattr(data, "m_Name", None) or ""


def texture_format_name(data: Any) -> str:
    value = getattr(data, "m_TextureFormat", "")
    name = getattr(value, "name", "")
    return name or str(value)


def image_size(image: Image.Image | None) -> tuple[int, int]:
    if image is None:
        return 0, 0
    return image.size


def export_image(image: Image.Image, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(out_path)


def make_output_name(bundle_path: Path, type_name: str, path_id: int, name: str) -> str:
    bundle_stem = safe_name(bundle_path.stem, "bundle", 120)
    asset_name = safe_name(name)
    return f"{bundle_stem}__{type_name}__{path_id}__{asset_name}.png"


def export_bundle(
    bundle_path: Path,
    out_dir: Path,
    include_textures: bool,
    include_sprites: bool,
    min_width: int,
    min_height: int,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    records: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    env = UnityPy.load(str(bundle_path))
    for obj in env.objects:
        type_name = obj.type.name
        if type_name == "Texture2D" and include_textures:
            try:
                data = obj.read()
                image = data.image
            except Exception as exc:
                errors.append(
                    {
                        "bundle_file": bundle_path.name,
                        "path_id": str(obj.path_id),
                        "type": type_name,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
                continue

            width, height = image_size(image)
            if width < min_width or height < min_height:
                continue

            name = object_name(data)
            out_path = out_dir / "Texture2D" / make_output_name(bundle_path, type_name, obj.path_id, name)
            export_image(image, out_path)
            records.append(
                {
                    "bundle_file": bundle_path.name,
                    "path_id": obj.path_id,
                    "type": type_name,
                    "name": name,
                    "width": width,
                    "height": height,
                    "texture_format": texture_format_name(data),
                    "png_path": str(out_path),
                }
            )

        elif type_name == "Sprite" and include_sprites:
            try:
                data = obj.read()
                image = data.image
            except Exception as exc:
                errors.append(
                    {
                        "bundle_file": bundle_path.name,
                        "path_id": str(obj.path_id),
                        "type": type_name,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
                continue

            width, height = image_size(image)
            if width < min_width or height < min_height:
                continue

            name = object_name(data)
            out_path = out_dir / "Sprite" / make_output_name(bundle_path, type_name, obj.path_id, name)
            export_image(image, out_path)
            records.append(
                {
                    "bundle_file": bundle_path.name,
                    "path_id": obj.path_id,
                    "type": type_name,
                    "name": name,
                    "width": width,
                    "height": height,
                    "texture_format": "",
                    "png_path": str(out_path),
                }
            )

    return records, errors


def write_manifest(records: list[dict[str, Any]], errors: list[dict[str, str]], out_dir: Path) -> None:
    manifest_json = out_dir / "manifest.json"
    manifest_json.write_text(
        json.dumps({"images": records, "errors": errors}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    manifest_csv = out_dir / "manifest.csv"
    fieldnames = ["bundle_file", "path_id", "type", "name", "width", "height", "texture_format", "png_path"]
    with manifest_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)

    errors_json = out_dir / "errors.json"
    errors_json.write_text(json.dumps(errors, ensure_ascii=False, indent=2), encoding="utf-8")


def contact_label(record: dict[str, Any], image_path: Path) -> str:
    name = record.get("name") or image_path.stem
    size = f"{record.get('width')}x{record.get('height')}"
    return f"{record.get('type')} {record.get('path_id')} {size}\n{name}"


def make_contact_sheet(records: list[dict[str, Any]], out_dir: Path, kind: str, thumb_size: int = 192) -> None:
    subset = [record for record in records if record["type"] == kind]
    if not subset:
        return

    label_height = 40
    padding = 12
    cell_w = thumb_size + padding * 2
    cell_h = thumb_size + label_height + padding * 2
    columns = 4
    rows = math.ceil(len(subset) / columns)
    sheet = Image.new("RGBA", (columns * cell_w, rows * cell_h), (245, 245, 245, 255))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()

    for index, record in enumerate(subset):
        src = Path(record["png_path"])
        try:
            image = Image.open(src).convert("RGBA")
        except Exception:
            continue
        image.thumbnail((thumb_size, thumb_size), Image.Resampling.LANCZOS)
        col = index % columns
        row = index // columns
        x = col * cell_w + padding
        y = row * cell_h + padding
        tile = Image.new("RGBA", (thumb_size, thumb_size), (230, 230, 230, 255))
        tile.alpha_composite(image, ((thumb_size - image.width) // 2, (thumb_size - image.height) // 2))
        sheet.alpha_composite(tile, (x, y))
        draw.multiline_text((x, y + thumb_size + 4), contact_label(record, src), fill=(20, 20, 20, 255), font=font)

    sheet.convert("RGB").save(out_dir / f"contact_sheet_{kind}.jpg", quality=92)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundles-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--glob", default="*")
    parser.add_argument("--textures", action="store_true", help="Export Texture2D images.")
    parser.add_argument("--sprites", action="store_true", help="Export Sprite crops.")
    parser.add_argument("--min-width", default=1, type=int)
    parser.add_argument("--min-height", default=1, type=int)
    parser.add_argument("--contact-sheets", action="store_true")
    args = parser.parse_args()

    include_textures = args.textures or not args.sprites
    include_sprites = args.sprites

    args.out_dir.mkdir(parents=True, exist_ok=True)
    bundle_paths = sorted(path for path in args.bundles_dir.rglob(args.glob) if path.is_file())

    records: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for index, bundle_path in enumerate(bundle_paths, start=1):
        print(f"[{index}/{len(bundle_paths)}] {bundle_path.name}")
        try:
            bundle_records, bundle_errors = export_bundle(
                bundle_path=bundle_path,
                out_dir=args.out_dir,
                include_textures=include_textures,
                include_sprites=include_sprites,
                min_width=args.min_width,
                min_height=args.min_height,
            )
        except Exception as exc:
            errors.append({"bundle_file": bundle_path.name, "error": f"{type(exc).__name__}: {exc}"})
            continue
        records.extend(bundle_records)
        errors.extend(bundle_errors)

    write_manifest(records, errors, args.out_dir)
    if args.contact_sheets:
        make_contact_sheet(records, args.out_dir, "Texture2D")
        make_contact_sheet(records, args.out_dir, "Sprite")

    print(f"Exported {len(records)} images to {args.out_dir}")
    if errors:
        print(f"Encountered {len(errors)} errors; see {args.out_dir / 'errors.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
