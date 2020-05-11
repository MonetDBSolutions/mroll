import pymonetdb
from pymonetdb import Error as PyMonetdbErr
import configparser
import os

config = configparser.ConfigParser()
dir_ = os.path.dirname(__file__)
configuration = os.path.join(dir_, 'mroll.ini')
config.read(configuration)
db_name = config['db']['db_name']
user = config['db']['user']
password = config['db']['password']
port = config['db']['port']
tbl_name = config['mroll']['rev_history_tbl_name']


def get_head(db_name=db_name, tbl_name=tbl_name):
    rev = None
    conn = pymonetdb.connect(db_name, port=port, username=user, password=password)
    try:
        sql = """select id, description, ts from sys."{}" as r where r.ts=(select max(ts) from sys."{}")""".format(tbl_name, tbl_name)
        curr = conn.cursor()
        curr.execute(sql)
        rev = curr.fetchone()
    finally:
        conn.close()
    return rev

def create_revisions_table(db_name=db_name, tbl_name=tbl_name):
    conn = pymonetdb.connect(db_name, port=port, username=user, password=password)
    sql = """
    create table if not exists sys."{}"(id string, description string, ts timestamp);
    alter table sys."{}" add constraint mroll_rev_pk primary key (id);
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

def get_revisions(db_name=db_name, tbl_name=tbl_name):
    conn = pymonetdb.connect(db_name, port=port, username=user, password=password)
    sql = """select id, description, ts from sys."{}" order by ts""".format(tbl_name)
    cur = conn.cursor()
    try:
        cur.execute(sql)
        return cur.fetchall()
    finally:
        conn.close()

def add_revision(id_, description, ts, upgrade_sql, db_name=db_name, tbl_name=tbl_name):
    """
    Applies the upgrade sql and adds it to meta data in one transaction
    """
    conn = pymonetdb.connect(db_name, port=port, username=user, password=password)
    cur = conn.cursor()
    sql = """
    insert into sys."{}" values (%s, %s, %s)
    """.format(tbl_name)
    try:
        conn.execute(upgrade_sql)
        cur.execute(sql, (id_, description, ts))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise(e)
    finally:
        conn.close()
    return False

def remove_revision(id_, downgrade_sql, db_name=db_name, tbl_name=tbl_name):
    conn = pymonetdb.connect(db_name, port=port, username=user, password=password)
    cur = conn.cursor()
    sql = """delete from sys."{}" where id=%s""".format(tbl_name)
    try:
        conn.execute(downgrade_sql)
        cur.execute(sql, (id_,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise(e)
    finally:
        conn.close()
    return False
