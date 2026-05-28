from decimal import Decimal
import requests

from .base import ImportedDeal


class OpenPricesProvider:
    source_name = "Open Food Facts Open Prices"
    base_url = "https://prices.openfoodfacts.org"

    def fetch_deals(self, search_terms=None, limit=50):
        search_terms = search_terms or ["pasta", "tomaten", "gurke", "milch"]

        imported_deals = []

        for term in search_terms:
            response = requests.get(
                f"{self.base_url}/api/v1/prices",
                params={
                    "search": term,
                    "size": limit,
                },
                timeout=50,
                headers={
                    "User-Agent": "EinkaufslisteProjekt/1.0"
                },
            )

            if response.status_code != 200:
                continue

            data = response.json()
            results = data.get("items") or data.get("results") or []

            for item in results:
                price = item.get("price")
                if price is None:
                    continue

                product_name = (
                    item.get("product_name")
                    or item.get("product_name_de")
                    or item.get("product_code")
                    or term
                )

                location = item.get("location") or {}
                store_name = (
                    location.get("name")
                    if isinstance(location, dict)
                    else "Unbekannter Markt"
                )

                imported_deals.append(
                    ImportedDeal(
                        external_id=f"open-prices-{item.get('id')}",
                        store_name=store_name or "Unbekannter Markt",
                        title=product_name,
                        description="Importiert aus Open Food Facts Open Prices",
                        original_price=None,
                        deal_price=Decimal(str(price)),
                        discount_text="Preis gefunden",
                    )
                )

        return imported_deals