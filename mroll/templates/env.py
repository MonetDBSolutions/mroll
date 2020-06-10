"""
MonetDB specific implementation. To use with another SQL compliant database re-implement API
bellow.
"""
import pymonetdb
import configparser
import os, sys
from typing import Tuple, List
from mroll.migration import Revision
from mroll.exceptions import RevisionOperationError

config = configparser.ConfigParser()
dir_ = os.path.dirname(__file__)
configuration = os.path.join(dir_, 'mroll.ini')
config.read(configuration)

db_name = config['db']['db_name']
username = config['db']['username']
password = config['db']['password']
hostname = config['host']['hostname']
port = config['host']['port']
tbl_name = config['mroll']['rev_history_tbl_name']

REVISION_RECORD = Tuple[str, str, str]

def get_head(db_name:str=db_name, hostname:str=hostname, port:int=port, username:str=username, password:str=password, tbl_name:str=tbl_name) -> REVISION_RECORD:
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

def create_revisions_table(db_name:str=db_name, hostname:str=hostname, port:int=port, username:str=username, password:str=password, tbl_name:str=tbl_name) -> None:
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

def get_revisions(db_name:str=db_name, hostname:str=hostname, port:int=port, username:str=username, password:str=password, tbl_name:str=tbl_name) -> List[REVISION_RECORD]:
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
    db_name:str=db_name, hostname:str=hostname, port:int=port, 
    username:str=username, password:str=password, tbl_name:str=tbl_name) -> None:
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
    db_name:str=db_name, hostname:str=hostname, port:int=port, 
    username:str=username, password:str=password, tbl_name:str=tbl_name) -> None:
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
