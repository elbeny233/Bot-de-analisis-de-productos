import argparse
import getpass
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import select
from sqlalchemy.engine import make_url

from radar.core.config import Settings
from radar.core.security import hash_password
from radar.database.bootstrap import seed_categories
from radar.database.models import AdminUser
from radar.database.session import build_engine, session_factory


def main():
    parser = argparse.ArgumentParser(description="Administración local de Radar Ofertas VIP")
    parser.add_argument("command", choices=["init-db", "create-admin", "backup"])
    parser.add_argument("--username", default="admin")
    args = parser.parse_args()
    settings = Settings()
    if args.command == "init-db":
        command.upgrade(Config("alembic.ini"), "head")
    if args.command == "backup":
        database = make_url(settings.database_url).database
        if database == ":memory:" or not Path(database).is_file():
            parser.error("No existe una base de datos persistente para respaldar")
        destination = Path("backups")
        destination.mkdir(exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        output = destination / f"radar-{timestamp}.db"
        with sqlite3.connect(f"{Path(database).resolve().as_uri()}?mode=ro", uri=True) as src:
            with sqlite3.connect(output) as dst:
                src.backup(dst)
        print(f"Respaldo creado: {output}")
        return
    engine = build_engine(settings.database_url)
    try:
        with session_factory(engine)() as session:
            if args.command == "init-db":
                seed_categories(session)
                print("Base de datos migrada y categorías inicializadas")
            else:
                if not args.username.strip() or len(args.username) > 100:
                    parser.error("Nombre administrativo inválido")
                if session.scalar(select(AdminUser).where(AdminUser.username == args.username)):
                    parser.error("Ese administrador ya existe")
                password = getpass.getpass("Contraseña (mínimo 12 caracteres): ")
                confirmation = getpass.getpass("Confirma la contraseña: ")
                if password != confirmation:
                    parser.error("Las contraseñas no coinciden")
                try:
                    encoded = hash_password(password)
                except ValueError as error:
                    parser.error(str(error))
                session.add(AdminUser(username=args.username, password_hash=encoded))
                session.commit()
                print("Administrador creado; el inicio de sesión web llegará en la Fase 6")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
