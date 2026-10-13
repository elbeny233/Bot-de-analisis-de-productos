import hashlib
import json
import re
import unicodedata
from decimal import Decimal

CATEGORY_KEYWORDS = {
    "alimentos": ("arroz", "frijol", "leche", "aceite", "cereal"),
    "linea-blanca": ("refrigerador", "lavadora", "secadora"),
    "electronica": ("audifonos", "televisor", "bocina", "smartphone"),
    "videojuegos": ("videojuego", "playstation", "xbox", "nintendo"),
    "computadoras": ("laptop", "computadora", "memoria ram", "ssd"),
    "hogar": ("sofa", "colchon", "mesa", "silla"),
    "herramientas": ("taladro", "martillo", "destornillador"),
    "ropa": ("camisa", "pantalon", "zapatos", "tenis"),
    "belleza": ("shampoo", "crema facial", "perfume"),
}


def normalize_text(value: str | None) -> str:
    return " ".join(unicodedata.normalize("NFKC", value or "").casefold().split())


def normalize_presentation(value: str | None) -> str:
    value = normalize_text(value)
    return re.sub(r"(\d)\s*(kg|g|ml|l|gb|tb)\b", r"\1 \2", value)


def product_identity(item) -> tuple[str, Decimal]:
    """Identidad conservadora: no combina modelos, presentaciones ni vendedores."""
    parts = [
        normalize_presentation(item.variant_key),
        normalize_text(item.brand),
        normalize_text(item.model),
        normalize_presentation(item.presentation),
        normalize_text(item.seller),
    ]
    digest = hashlib.sha256(json.dumps(parts, ensure_ascii=False).encode()).hexdigest()
    # El hash completo conserva identidad aun si el texto visible supera 300 caracteres.
    key = f"{parts[0][:230]}~{digest}"
    confidence = Decimal("0.50")
    if parts[3]:
        confidence += Decimal("0.20")
    if parts[2]:
        confidence += Decimal("0.20")
    if parts[1]:
        confidence += Decimal("0.10")
    return key, confidence


def compatible_legacy(product, item) -> bool:
    return (
        normalize_text(product.brand) == normalize_text(item.brand)
        and normalize_text(product.model) == normalize_text(item.model)
        and normalize_presentation(product.presentation)
        == normalize_presentation(item.presentation)
        and normalize_text(product.seller) == normalize_text(item.seller)
    )


def classify_category(name: str, suggested: str | None, known: set[str]) -> str | None:
    if suggested in known:
        return suggested
    canonical = unicodedata.normalize("NFKD", normalize_text(name))
    canonical = "".join(char for char in canonical if not unicodedata.combining(char))
    matches = {
        slug
        for slug, words in CATEGORY_KEYWORDS.items()
        if slug in known
        and any(re.search(r"\b" + re.escape(word) + r"\b", canonical) for word in words)
    }
    return matches.pop() if len(matches) == 1 else None
