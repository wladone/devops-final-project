#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update a Helm values file with a new image repository and tag.")
    parser.add_argument("--values-file", required=True, help="Path to the Helm values YAML file.")
    parser.add_argument("--image-repository", required=True, help="Container repository to write into image.repository.")
    parser.add_argument("--image-tag", required=True, help="Container tag to write into image.tag.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    values_path = Path(args.values_file)

    if not values_path.exists():
        raise FileNotFoundError(f"Values file not found: {values_path}")

    with values_path.open("r", encoding="utf-8") as handle:
        values = yaml.safe_load(handle) or {}

    image = values.setdefault("image", {})
    image["repository"] = args.image_repository
    image["tag"] = args.image_tag

    with values_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(values, handle, sort_keys=False)

    print(f"Updated {values_path} to {args.image_repository}:{args.image_tag}")


if __name__ == "__main__":
    main()
