import pymonetdb
from pymonetdb import Error as PyMonetdbErr
import configparser
import os

config = configparser.ConfigParser()
dir_ = os.path.dirname(__file__)
configuration = os.path.join(dir_, 'mdb.ini')
config.read(configuration)
db_name = config['db']['db_name']
user = config['db']['user']
password = config['db']['password']
port = config['db']['port']


def create_head_tbl(db_name=db_name):
    tbl_name = config['mdb']['rev_head_tbl_name']
    conn = pymonetdb.connect(db_name, port=port, username=user, password=password)
    sql = "create table if not exists {}(head string)".format(tbl_name)
    try:
        conn.execute(sql)
        conn.commit()
        return True
    except PyMonetdbErr as e:
        conn.rollback()  
        raise(e)
    finally:
        conn.close()
    return False

def get_head():
    head = None
    conn = pymonetdb.connect(db_name, port=port, username=user, password=password)
    try:
        sql = "select head from mdb_rev_head limit 1"
        curr = conn.cursor()
        curr.execute(sql)
        head, = curr.fetchone() or (None,)
    finally:
        conn.close()
    return head

def create_revisions_table(db_name=db_name):
    tbl_name = config['mdb']['rev_history_tbl_name']
    conn = pymonetdb.connect(db_name, port=port, username=user, password=password)
    sql = """
    create table if not exists {}(id string, description string, ts timestamp);
    alter table {} add constraint mdb_rev_pk primary key (id);
    """.format(tbl_name, tbl_name)
    try:
        conn.execute(sql)
        conn.commit()
        return True
    except PyMonetdbErr as e:
        conn.rollback()
        raise(e)    
    finally:
        conn.close()
    return False

def get_revisions():
    tbl_name = config['mdb']['rev_history_tbl_name']
    conn = pymonetdb.connect(db_name, port=port, username=user, password=password)
    sql = "select id, description, ts from {} order by ts".format(tbl_name)
    cur = conn.cursor()
    try:
        cur.execute(sql)
        return cur.fetchall()
    finally:
        conn.close()

def add_revision(id_, description, ts):
    tbl_name = config['mdb']['rev_history_tbl_name']
    conn = pymonetdb.connect(db_name, port=port, username=user, password=password)
    sql = "insert into {} values ({}, {}, {})".format(tbl_name, id_, description, ts)
    try:
        conn.execute(sql)
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise(e)
    finally:
        conn.close()
    return False

def migrate():
    pass