from . import monetdb

__all__ = (
    'create_migration_ctx'
)

def create_migration_ctx(config, database='monetdb'):
    """
    Factory method to create specific database context
    """
    if database == 'monetdb':
        from .monetdb import MigrationContext
        return MigrationContext.from_conf(config)
        