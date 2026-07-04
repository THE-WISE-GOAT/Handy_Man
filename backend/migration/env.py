from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from src.core.model import Base
from src.configuration.config import settings
from geoalchemy2 import alembic_helpers
import src.core.model
from src.database.database import Base


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config
database_url = f"postgresql://{settings.DATABASE_USERNAME}:{settings.DATABASE_PASSWORD}@{settings.DATABASE_HOSTNAME}:{settings.DATABASE_PORT}/{settings.DATABASE_NAME}"

config.set_main_option("sqlalchemy.url", database_url)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def custom_include_object(object, name, type_, reflected, compare_to):
    """Filter to completely ignore internal PostGIS/Tiger geocoder tables."""
    
    # Comprehensive list matching all the system tables showing up in your script
    ignored_tables = [
        "spatial_ref_sys", "geometry_columns", "geography_columns", 
        "raster_columns", "raster_overviews", "addrfeat", "edges", 
        "faces", "place", "state", "county", "tract", "zcta5", 
        "tabblock", "tabblock20", "bg", "addr", "zip_state", "zip_state_loc",
        "zip_lookup", "zip_lookup_all", "zip_lookup_base", "pagc_rules", 
        "pagc_gaz", "pagc_lex", "layer", "topology", "loader_platform", 
        "loader_variables", "loader_lookuptables", "geocode_settings", 
        "geocode_settings_default", "direction_lookup", "street_type_lookup",
        "place_lookup", "county_lookup", "state_lookup", "countysub_lookup",
        "secondary_unit_lookup", "cousub", "featnames"
    ]
    
    # 1. First run the built-in GeoAlchemy spatial filter if applicable
    if not alembic_helpers.include_object(object, name, type_, reflected, compare_to):
        return False
        
    # 2. Skip internal PostGIS/Tiger system tables
    if type_ == "table" and name in ignored_tables:
        return False
        
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_object=custom_include_object,  # Use custom hybrid filter
        process_revision_directives=alembic_helpers.writer,
        render_item=alembic_helpers.render_item,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_object=custom_include_object,  # Use custom hybrid filter
            process_revision_directives=alembic_helpers.writer,
            render_item=alembic_helpers.render_item,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
