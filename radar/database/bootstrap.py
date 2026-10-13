from sqlalchemy import select
from sqlalchemy.orm import Session

from radar.database.models import Category

DEFAULT_CATEGORIES = [
    ("alimentos", "Alimentos y abarrotes"),
    ("linea-blanca", "Línea blanca"),
    ("electronica", "Electrónica"),
    ("videojuegos", "Videojuegos"),
    ("computadoras", "Computadoras"),
    ("hogar", "Hogar y muebles"),
    ("herramientas", "Herramientas"),
    ("ropa", "Ropa y calzado"),
    ("belleza", "Belleza y cuidado personal"),
    ("extraordinarias", "Ofertas extraordinarias"),
    ("avisos", "Avisos generales"),
]


def seed_categories(session: Session) -> None:
    existing = set(session.scalars(select(Category.slug)))
    for slug, name in DEFAULT_CATEGORIES:
        if slug not in existing:
            session.add(Category(slug=slug, name=name))
    session.commit()
