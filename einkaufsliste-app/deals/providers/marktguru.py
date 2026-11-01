from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal, InvalidOperation
from datetime import datetime
import logging
import os
import requests

from .base import ImportedDeal

logger = logging.getLogger(__name__)

# Händler dieser Branchen verkaufen keine Lebensmittel (Fressnapf, Baumarkt …)
NON_FOOD_INDUSTRIES = ("tier", "zoo", "bau", "möbel", "elektro", "mode", "sport", "garten",
                       "spielwaren", "auto", "apotheke", "optik", "schuh", "textil")


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

    def fetch_deals(self, search_terms=None, limit=50, on_progress=None, max_workers=3):
        """Sucht Angebote für alle Suchbegriffe.

        Mehrere Begriffe laufen parallel (max_workers), on_progress(done, total) wird nach
        jedem fertigen Begriff aufgerufen – dafür gibt es in der App die Ladeanzeige.
        """
        if not self.api_key or not self.client_key:
            raise ValueError("MARKTGURU_API_KEY und MARKTGURU_CLIENT_KEY fehlen in .env")

        terms = list(search_terms) if search_terms is not None else [""]
        total = len(terms)
        done = 0
        imported_deals = []
        seen_external_ids = set()

        if on_progress:
            on_progress(0, total)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self._fetch_term, term, limit) for term in terms]
            for future in as_completed(futures):
                for deal in future.result():
                    if deal.external_id in seen_external_ids:
                        continue
                    seen_external_ids.add(deal.external_id)
                    imported_deals.append(deal)
                done += 1
                if on_progress:
                    on_progress(done, total)

        return imported_deals

    def _fetch_term(self, term, limit):
        deals = []
        offset = 0

        while True:
            try:
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
                    timeout=30,
                )

                if response.status_code == 429:
                    logger.warning("Marktguru [%s]: Rate limit (429) – übersprungen", term)
                    break

                if not response.ok:
                    logger.warning("Marktguru [%s]: HTTP %s – übersprungen", term, response.status_code)
                    break

                data = response.json()

            except (requests.RequestException, ValueError) as e:
                logger.warning("Marktguru [%s]: %s – übersprungen", term, e)
                break

            results = data.get("results", [])
            total_results = data.get("totalResults", 0)

            if not results:
                break

            for item in results:
                deal = self._parse_item(item)
                if deal:
                    deals.append(deal)

            offset += limit

            if offset >= total_results:
                break

        return deals

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
        # Marktguru-Platzhalter für Produkte ohne Marke ("thisisnobrand123")
        if (brand_name or "").lower().startswith("thisisnobrand"):
            brand_name = ""

        industries = " ".join(
            (i.get("name") or "").lower() for i in (item.get("industries") or []) if isinstance(i, dict)
        )
        if industries and any(word in industries for word in NON_FOOD_INDUSTRIES):
            return None

        source_categories = "|".join(
            c.get("name") for c in (item.get("categories") or []) if isinstance(c, dict) and c.get("name")
        )[:255]

        from deals.services import is_non_food
        if is_non_food(f"{brand_name} {product_name}", source_categories):
            return None

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

        unit = item.get("unit") or {}
        unit_short = unit.get("shortName", "") if isinstance(unit, dict) else ""
        reference_price = self._parse_decimal(item.get("referencePrice"))
        package_size = self._format_package(item.get("volume"), item.get("quantity"), unit_short)

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
            product_name=product_name or "",
            reference_price=reference_price,
            reference_unit=unit_short if reference_price is not None else "",
            package_size=package_size,
            requires_loyalty=bool(item.get("requiresLoyalityMembership")),
            source_categories=source_categories,
        )

    def _format_package(self, volume, quantity, unit):
        """volume=0.25, unit=kg → "250 g"; quantity>1 → "4 × 250 g"."""
        volume = self._parse_decimal(volume)
        if not volume or not unit:
            return ""
        if unit == "kg" and volume < 1:
            amount, unit = volume * 1000, "g"
        elif unit == "l" and volume < 1:
            amount, unit = volume * 1000, "ml"
        else:
            amount = volume
        amount_text = f"{amount:.2f}".rstrip("0").rstrip(".").replace(".", ",")
        quantity = self._parse_decimal(quantity)
        prefix = f"{int(quantity)} × " if quantity and quantity > 1 and quantity == int(quantity) else ""
        if not prefix and amount == 1:
            # "1 kg" / "1 Stk" sagt nichts, was der Grundpreis nicht schon zeigt
            return ""
        return f"{prefix}{amount_text} {unit}"