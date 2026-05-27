from dataclasses import dataclass
from decimal import Decimal
from datetime import date


@dataclass
class ImportedDeal:
    external_id: str
    store_name: str
    title: str
    description: str = ""
    original_price: Decimal | None = None
    deal_price: Decimal | None = None
    discount_text: str = ""
    product_url: str = ""
    image_url: str = ""
    valid_from: date | None = None
    valid_until: date | None = None