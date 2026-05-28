from decimal import Decimal, InvalidOperation
from datetime import datetime
import os
import requests

from .base import ImportedDeal


class MarktguruProvider:
    source_name = "Marktguru"
    base_url = "https://api.marktguru.de/api/v1/offers/search"

    def __init__(self, zip_code=None):
        self.api_key = os.environ.get("MARKTGURU_API_KEY")
        self.client_key = os.environ.get("MARKTGURU_CLIENT_KEY")

        self.zip_code = (
            zip_code
            or os.environ.get("MARKTGURU_ZIP_CODE")
            or "89231"
        )

    def fetch_deals(self, search_terms=None, limit=50):
        if not self.api_key or not self.client_key:
            raise ValueError("MARKTGURU_API_KEY und MARKTGURU_CLIENT_KEY fehlen in .env")

        search_terms = search_terms if search_terms is not None else [""]

        imported_deals = []
        seen_external_ids = set()

        for term in search_terms:
            offset = 0

            while True:
                response = requests.get(
                    self.base_url,
                    params={
                        "as": "web",
                        "limit": limit,
                        "offset": offset,
                        "q": term,
                        "zipCode": self.zip_code,
                    },
                    headers={
                        "x-apikey": self.api_key,
                        "x-clientkey": self.client_key,
                        "User-Agent": "Mozilla/5.0",
                    },
                    timeout=50,
                )

                response.raise_for_status()
                data = response.json()

                results = data.get("results", [])
                total_results = data.get("totalResults", 0)

                if not results:
                    break

                for item in results:
                    deal = self._parse_item(item)

                    if not deal:
                        continue

                    if deal.external_id in seen_external_ids:
                        continue

                    seen_external_ids.add(deal.external_id)
                    imported_deals.append(deal)

                offset += limit

                if offset >= total_results:
                    break

        return imported_deals

    def _parse_decimal(self, value):
        if value is None:
            return None

        try:
            return Decimal(str(value).replace(",", "."))
        except (InvalidOperation, ValueError):
            return None

    def _parse_date(self, value):
        if not value:
            return None

        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError:
            return None

    def _parse_item(self, item):
        external_id = str(item.get("id") or item.get("_id") or "")
        if not external_id:
            return None

        brand = item.get("brand") or {}
        product = item.get("product") or {}

        brand_name = brand.get("name") if isinstance(brand, dict) else ""
        product_name = product.get("name") if isinstance(product, dict) else ""

        title = " ".join(
            part for part in [brand_name, product_name]
            if part
        ).strip()

        if not title:
            title = (
                item.get("title")
                or item.get("name")
                or item.get("description")
                or "Unbekanntes Angebot"
            )

        if title.isdigit():
            return None

        description = item.get("description") or ""

        advertisers = item.get("advertisers") or []
        store_name = "Unbekannter Markt"

        if advertisers and isinstance(advertisers, list):
            store_name = advertisers[0].get("name") or store_name

        deal_price = self._parse_decimal(
            item.get("price")
            or item.get("newPrice")
            or item.get("currentPrice")
            or item.get("discountPrice")
        )

        original_price = self._parse_decimal(
            item.get("oldPrice")
            or item.get("originalPrice")
            or item.get("regularPrice")
        )

        discount_text = ""
        if original_price and deal_price:
            savings = original_price - deal_price
            if savings > 0:
                discount_text = f"{savings:.2f} € sparen"
        elif deal_price:
            discount_text = "Angebot"

        valid_from = None
        valid_until = None

        validity_dates = item.get("validityDates") or []
        if validity_dates:
            validity = validity_dates[0]
            valid_from = self._parse_date(validity.get("from"))
            valid_until = self._parse_date(validity.get("to"))

        product_url = item.get("externalUrl") or item.get("url") or ""

        image_url = f"https://mg2de.b-cdn.net/api/v1/offers/{external_id}/images/default/0/large.webp"

        return ImportedDeal(
            external_id=f"marktguru-{external_id}",
            store_name=store_name,
            title=title,
            description=description,
            original_price=original_price,
            deal_price=deal_price,
            discount_text=discount_text,
            product_url=product_url,
            image_url=image_url,
            valid_from=valid_from,
            valid_until=valid_until,
        )