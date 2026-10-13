from decimal import Decimal

from radar.collectors.base import CollectedProduct


class DemoCollector:
    """Datos sintéticos, sin consultas a tiendas ni URLs de compra."""

    is_simulated = True

    def collect(self) -> list[CollectedProduct]:
        return [
            CollectedProduct(
                source_product_id="demo-arroz",
                variant_key="1kg",
                name="[SIMULADO] Arroz de demostración 1 kg",
                presentation="1 kg",
                category_slug="alimentos",
                price=Decimal("29.90"),
                available=True,
                shipping_cost=Decimal("0"),
                conditions="SIMULACIÓN: no es una oferta ni un producto a la venta",
            ),
            CollectedProduct(
                source_product_id="demo-audifonos",
                variant_key="modelo-demo",
                name="[SIMULADO] Audífonos de demostración",
                brand="Marca simulada",
                model="DEMO-01",
                category_slug="electronica",
                price=Decimal("499.00"),
                available=None,
                conditions="SIMULACIÓN: disponibilidad y envío desconocidos",
            ),
            CollectedProduct(
                source_product_id="demo-arroz",
                variant_key="500g",
                name="[SIMULADO] Arroz de demostración 500 g",
                presentation="500 g",
                category_slug="alimentos",
                price=Decimal("16.90"),
                available=False,
                conditions="SIMULACIÓN: producto no disponible",
            ),
        ]
