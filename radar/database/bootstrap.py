from sqlalchemy import select
from sqlalchemy.orm import Session

from radar.database.models import Category, Source, Store

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


def seed_demo_source(session: Session, interval_minutes: int) -> None:
    name = "Demostración — DATOS SIMULADOS"
    if session.scalar(select(Source).where(Source.name == name)) is not None:
        return
    store = session.scalar(select(Store).where(Store.name == "Tienda simulada (sin ventas)"))
    if store is None:
        store = Store(name="Tienda simulada (sin ventas)")
        session.add(store)
        session.flush()
    session.add(
        Source(
            store_id=store.id,
            name=name,
            connector="demo",
            enabled=True,
            interval_minutes=interval_minutes,
        )
    )
    session.commit()
