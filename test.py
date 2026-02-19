import argparse
import csv
import hashlib
import os
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "commerce.settings")

import django

django.setup()

from django.core.files.base import ContentFile

from products.models import ProductModel


def parse_price(row):
    raw = (row.get("final_price") or row.get("initial_price") or "").strip().strip('"')
    if not raw or raw.lower() == "null":
        return None
    try:
        return Decimal(raw)
    except InvalidOperation:
        return None


def infer_extension(image_url, content_type):
    content_type = (content_type or "").lower()
    if "jpeg" in content_type or "jpg" in content_type:
        return "jpg"
    if "png" in content_type:
        return "png"
    if "webp" in content_type:
        return "webp"
    if "gif" in content_type:
        return "gif"
    path = urlparse(image_url).path
    ext = Path(path).suffix.lower().replace(".", "")
    return ext if ext in {"jpg", "jpeg", "png", "webp", "gif"} else "jpg"


def download_image(image_url, timeout):
    if not image_url:
        return None, None
    try:
        req = Request(
            image_url,
            headers={
                "User-Agent": "Mozilla/5.0",
            },
        )
        with urlopen(req, timeout=timeout) as response:
            content = response.read()
            content_type = response.headers.get("Content-Type", "")
        if not content:
            return None, None
        ext = infer_extension(image_url, content_type)
        return content, ext
    except Exception:
        return None, None


def product_exists(name):
    return ProductModel.objects.filter(name=name).exists()


def import_products(csv_path, limit, timeout):
    added = 0
    skipped_existing = 0
    skipped_invalid = 0
    image_saved = 0

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if limit and added >= limit:
                break

            name = (row.get("title") or "").strip()
            if not name:
                skipped_invalid += 1
                continue
            name = name[:100]

            price = parse_price(row)
            if price is None:
                skipped_invalid += 1
                continue

            if product_exists(name):
                skipped_existing += 1
                continue

            product = ProductModel.objects.create(name=name, price=price)
            added += 1

            image_url = (row.get("image_url") or "").strip().strip('"')
            content, ext = download_image(image_url, timeout=timeout)
            if content:
                digest = hashlib.md5(image_url.encode("utf-8")).hexdigest()[:12]
                filename = f"product_{product.id}_{digest}.{ext}"
                product.image.save(filename, ContentFile(content), save=True)
                image_saved += 1

    return {
        "added": added,
        "skipped_existing": skipped_existing,
        "skipped_invalid": skipped_invalid,
        "image_saved": image_saved,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Import products from CSV into ProductModel with optional image download.",
    )
    parser.add_argument(
        "--csv",
        default=r"F:\commerce\amazon-products.csv",
        help="Path to CSV file.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max number of NEW products to import (0 = all).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=20,
        help="Image download timeout in seconds.",
    )
    args = parser.parse_args()

    stats = import_products(args.csv, args.limit, args.timeout)

    print("Done")
    print(f"Added: {stats['added']}")
    print(f"Skipped existing: {stats['skipped_existing']}")
    print(f"Skipped invalid rows: {stats['skipped_invalid']}")
    print(f"Images saved: {stats['image_saved']}")


if __name__ == "__main__":
    main()
