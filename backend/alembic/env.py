# WHAT THIS FILE IS
# Configuration for Alembic, the tool that manages database changes ("migrations").
# WHY it exists: when we change the tables in models.py, Alembic compares our models
# to the real database and writes the exact steps to update it. This file tells
# Alembic (a) what our models are and (b) which database to connect to.
# You normally don't edit this per-change — you just run `alembic` commands.

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

# Importing app.models runs that file, which registers all 14 tables onto
# SQLModel.metadata below. We don't call anything from it directly — importing is
# the point. (The "noqa" note tells the linter this "unused" import is intentional.)
import app.models  # noqa: F401 — imported for the side effect of registering every table
from app.config import get_settings
from app.db import normalize_url

config = context.config

# Set up log messages (uses the [logger_*] sections in alembic.ini).
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# target_metadata = the full picture of the tables our code expects. Alembic compares
# THIS against the real database to figure out what changed.
target_metadata = SQLModel.metadata


def include_object(obj, name, type_, reflected, compare_to):
    # Tell Alembic to ignore tables it doesn't manage. Specifically, the old Prisma
    # tool left a bookkeeping table ("_prisma_migrations") in the same database.
    # Without this, Alembic would think we want to delete it. Return False = "skip".
    #
    # With include_schemas turned on (see run_migrations_online), some of our tables live
    # in a schema (silver/gold/bronze). SQLModel.metadata keys those as "schema.table",
    # but the `name` Alembic passes here is the UNQUALIFIED table name. So we rebuild the
    # qualified key from obj.schema before checking — otherwise our own schema tables would
    # look "unmanaged" and Alembic would propose dropping them.
    if type_ == "table" and reflected:
        schema = getattr(obj, "schema", None)
        key = f"{schema}.{name}" if schema else name
        if key not in target_metadata.tables:
            return False
    return True


def include_name(name, type_, parent_names):
    # Runs only because include_schemas=True (below) makes Alembic reflect EVERY schema in
    # the database — including Supabase-managed ones (auth, storage, ...) we don't own.
    # Restrict reflection to the schemas our own models declare, so autogenerate never sees
    # (and never proposes dropping) Supabase's tables. We derive the allowed set from the
    # models themselves (each table's .schema; None = the default "public" schema), so adding
    # a model in a new schema is covered automatically — there's no hand-kept list to update.
    if type_ == "schema":
        managed_schemas = {table.schema for table in target_metadata.tables.values()}
        return name in managed_schemas
    return True


def _url() -> str:
    # Decide which database address to use.
    # If someone runs `alembic -x dburl=...`, use that (we use it to build the very
    # first migration against an empty database). Otherwise use DIRECT_URL if set
    # (a direct connection, best for schema changes), falling back to DATABASE_URL.
    override = context.get_x_argument(as_dictionary=True).get("dburl")
    if override:
        # Normalize the pasted address too — the same driver/pgbouncer fixes the settings
        # path gets below. WHY: a raw dashboard URL says "postgresql://", which SQLAlchemy
        # routes to the psycopg2 driver we don't install; without this the one-off command
        # crashes with "No module named psycopg2" (the T98 bug, hit during the T96
        # production migration).
        return normalize_url(override)
    settings = get_settings()
    return normalize_url(settings.direct_url or settings.database_url)


def run_migrations_offline() -> None:
    # "Offline" mode: don't connect to a database, just print the SQL it WOULD run.
    # Handy for reviewing changes before applying them.
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # "Online" mode (the normal one): actually connect to the database and apply the
    # migrations. NullPool = open one connection, use it, close it (no reuse needed
    # for a one-off command).
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = _url()
    connectable = engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,  # apply the "ignore Prisma's table" rule above
            # include_schemas=True: also look at non-default schemas (silver/gold/bronze from
            # T39/ADR-0009), or autogenerate wouldn't see those tables and would mis-generate.
            # include_name then narrows reflection back to just the schemas we own.
            include_schemas=True,
            include_name=include_name,
        )
        with context.begin_transaction():
            context.run_migrations()


# Pick the mode based on how alembic was invoked, then run.
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
