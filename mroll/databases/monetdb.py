"""
MonetDB
"""
import pymonetdb
import configparser
import os, sys
from typing import Tuple, List
from mroll.migration import Revision
from mroll.exceptions import RevisionOperationError


# TODO evrrything goes through migration context where module eg mdb/monetdb is specific databas
# module. inIt through config file aka mroll ini.



class MigrationContext:
    """
    Implements migrations context interface
    """
    def __init__(self, head=None, revisions=[]):
        # TODO init the rev tbl here
        self.head = head
        self.revisions = revisions

    def create_revisions_tbl(self):
        # self.plugin.create_revison table
        pass

    @property
    def head(self):
        return self.head

    @property
    def revisions(self):
        return self.revisions

    def add_revisions(self, revisions: List[Revision]):
        pass

    def remove_revisions(self, revisions: List[Revision]):
        pass

    def __repr__(self):
        return "<MigrationContext head={} revisions={}>".format(self.head, self.revisions)

    @classmethod
    def from_conf(cls, env):
        # TODO pass the mroll.ini
        pass

REVISION_RECORD = Tuple[str, str, str]

def get_head(
    db_name, tbl_name:str='mroll_revisions',
    hostname:str='127.0.0.1', port:int=50000,
    username:str='monetbd', password:str='monetdb') -> REVISION_RECORD:
    """
    Returns last revision
    """
    rev = None
    conn = pymonetdb.connect(db_name, hostname=hostname, port=port, username=username, password=password)
    try:
        sql = """select id, description, ts from sys."{}" as r where r.ts=(select max(ts) from sys."{}")""".format(tbl_name, tbl_name)
        curr = conn.cursor()
        curr.execute(sql)
        rev = curr.fetchone()
    finally:
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
    try:
        cur.execute(sql)
        return cur.fetchall()
    finally:
        conn.close()

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
