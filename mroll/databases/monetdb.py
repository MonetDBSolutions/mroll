"""
MonetDB
"""
import pymonetdb
import configparser
import os, sys
from typing import Tuple, List
from mroll.migration import Revision, MigrationContext, MigrationCtxConfig
from mroll.exceptions import RevisionOperationError

class MonetMigrCtx(MigrationContext):
    """
    Monetdb specific implementation of Migration Context
    """
    def __init__(self, config: MigrationCtxConfig):
        assert config.db_name
        assert config.username
        assert config.password
        assert config.tbl_name
        assert config.hostname
        assert config.port
        self.config = config

    def create_revisions_tbl(self) -> None:
        config = self.config
        return create_revisions_table(
            config.db_name,
            tbl_name=config.tbl_name,
            hostname=config.hostname,
            port=config.port,
            username=config.username,
            password=config.password)

    @property
    def head(self) -> Revision:
        config = self.config
        head = get_head(
            config.db_name,
            tbl_name=config.tbl_name,
            hostname=config.hostname,
            port=config.port,
            username=config.username,
            password=config.password)
        if head is not None:
            id_, description, ts = head
            return Revision(id_, description, ts)
        return head

    @property
    def revisions(self) -> List[Revision]:
        config = self.config
        revisions = get_revisions(
            config.db_name,
            tbl_name=config.tbl_name,
            hostname=config.hostname,
            port=config.port,
            username=config.username,
            password=config.password)
        return [Revision(id_, description, ts) for id_, description, ts in revisions]

    def add_revisions(self, revisions: List[Revision]) -> None:
        config = self.config
        return add_revisions(
            revisions,
            config.db_name,
            tbl_name=config.tbl_name,
            hostname=config.hostname,
            port=config.port,
            username=config.username,
            password=config.password)

    def remove_revisions(self, revisions: List[Revision]) -> None:
        config = self.config
        return remove_revisions(
            revisions,
            config.db_name,
            tbl_name=config.tbl_name,
            hostname=config.hostname,
            port=config.port,
            username=config.username,
            password=config.password)

    def __repr__(self):
        return "<MonetMigrCtx head={} revisions={}>".format(self.head, self.revisions)


REVISION_RECORD = Tuple[str, str, str]

def get_head(
    db_name, tbl_name:str='mroll_revisions',
    hostname:str='127.0.0.1', port:int=50000,
    username:str='monetbd', password:str='monetdb') -> REVISION_RECORD:
    """
    Returns last revision
    """
    conn = pymonetdb.connect(db_name, hostname=hostname, port=port, username=username, password=password)
    sql = """select id, description, ts from sys."{}" as r where r.ts=(select max(ts) from sys."{}")""".format(tbl_name, tbl_name)
    curr = conn.cursor()
    curr.execute(sql)
    rev = curr.fetchone()
    conn.close() 
    return rev

def create_revisions_table(
    db_name, tbl_name:str='mroll_revisions', 
    hostname:str='127.0.0.1', port:int=50000, 
    username:str='monetbd', password:str='monetdb') -> None:
    """
    Creates revisons table with columns (id string, description string, ts timestamp)
    """
    conn = pymonetdb.connect(db_name, hostname=hostname, port=port, username=username, password=password)
    sql = """
    create table sys."{}"(id string, description string, ts timestamp);
    alter table sys."{}" add constraint mroll_rev_pk primary key (id);
    """.format(tbl_name, tbl_name)
    try:
        conn.execute(sql)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise(e)    
    finally:
        conn.close()

def get_revisions(
    db_name, tbl_name:str='mroll_revisions',
    hostname:str='127.0.0.1', port:int=50000, 
    username:str='monetbd', password:str='monetdb') -> List[REVISION_RECORD]:
    """
    Returns all applied revisions.
    """
    conn = pymonetdb.connect(db_name, hostname=hostname, port=port, username=username, password=password)
    sql = """select id, description, ts from sys."{}" order by ts""".format(tbl_name)
    cur = conn.cursor()
    cur.execute(sql)
    res = cur.fetchall()
    conn.close()
    return res
        

def add_revisions(revisions: List[Revision], 
    db_name, tbl_name:str='mroll_revisions', 
    hostname:str='127.0.0.1', port:int=50000,
    username:str='monetbd', password:str='monetdb') -> None:
    """
    Executes upgrade_sql and adds new revision records.
    """
    conn = pymonetdb.connect(db_name, hostname=hostname, port=port, username=username, password=password)
    cur = conn.cursor()
    sql = """
    insert into sys."{}" values (%s, %s, %s)
    """.format(tbl_name)
    try:
        for rev in revisions:
            for stmt in rev.upgrade_stmts:
                conn.execute(stmt)
            cur.execute(sql, (rev.id, rev.description, rev.ts))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise RevisionOperationError(rev, stmt, repr(e))
    finally:
        conn.close()

def remove_revisions(revisions: List[Revision],
    db_name, tbl_name:str='mroll_revisions', 
    hostname:str='127.0.0.1', port:int=50000,
    username:str='monetbd', password:str='monetdb') -> None:
    """
    Removes list of revisions in one transaction.
    """
    conn = pymonetdb.connect(db_name, hostname=hostname, port=port, username=username, password=password)
    cur = conn.cursor()
    sql = """delete from sys."{}" where id=%s""".format(tbl_name)
    try:
        for rev in revisions:
            for stmt in rev.downgrade_stmts:
                conn.execute(stmt)
            cur.execute(sql, (rev.id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise RevisionOperationError(rev, stmt, repr(e))
    finally:
        conn.close()
