from .monetdb import MonetMigrCtx
from mroll.migration import MigrationContext

__all__ = (
    'create_migration_ctx'
)

def create_migration_ctx(config, database='monetdb') -> MigrationContext:
    """
    Factory method to create specific database engine context.
    Defaults to monetdb.
    """
    if database == 'monetdb':
        return MonetMigrCtx(config)
        