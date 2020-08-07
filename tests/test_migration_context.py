import os
import shutil
from unittest import TestCase
from click.testing import CliRunner
from mroll.migration import Revision, WorkDirectory, gen_rev_id
from mroll.commands import setup, revision
from mroll.config import MROLL_CONFIG_DIR
from mroll.databases import create_migration_ctx
import pymonetdb
from datetime import datetime

class TestMonetMigrationContext(TestCase):
    setup_res = None
    init_res = None
    work_dir = os.path.join('/tmp', 'migrations')
    db_name = os.environ.get('TEST_DB_NAME', 'mroll_test_db')

    def setUp(self):
        self.setup_res = self.run_setup_cmd()
        self.set_config_db_name(self.db_name)
        conn = pymonetdb.connect(self.db_name)
        conn.execute('create schema if not exists test;')
        conn.commit()
        
    def tearDown(self):
        if os.path.exists(self.work_dir):
            shutil.rmtree(self.work_dir)
        if os.path.exists(MROLL_CONFIG_DIR):
            shutil.rmtree(MROLL_CONFIG_DIR)
        self.drop_all()

    def drop_all(self):
        conn = pymonetdb.connect(self.db_name)
        try:
            conn.execute("drop table if exists sys.mroll_revisions;")
            conn.execute("drop schema test cascade")
            conn.commit()
        except Exception as e:
            print(e)
        finally:
            conn.close()

    def run_setup_cmd(self):
        runner = CliRunner() 
        return runner.invoke(setup, ['-p', str(self.work_dir)])

    def set_config_db_name(self, db_name):
        wd = WorkDirectory(path=self.work_dir)
        wd._set_config('db', 'db_name', db_name)

    def test_create_migr_ctx(self):
        wd = WorkDirectory(path=self.work_dir)
        ctx = create_migration_ctx(wd.get_migration_ctx_config())
        self.assertIsNotNone(ctx)

    def test_migr_ctx_head(self):
        wd = WorkDirectory(path=self.work_dir)
        ctx = create_migration_ctx(wd.get_migration_ctx_config())
        ctx.create_revisions_tbl()
        self.assertIsNone(ctx.head)
        conn = pymonetdb.connect(self.db_name)
        sql = """insert into sys.mroll_revisions values ('{}', '{}', '{}')""".format(gen_rev_id(), "bla bla", datetime.now())
        conn.execute(sql)
        conn.commit()
        self.assertIsNotNone(ctx.head)

    def test_ctx_revisions(self):
        wd = WorkDirectory(path=self.work_dir)
        ctx = create_migration_ctx(wd.get_migration_ctx_config())
        ctx.create_revisions_tbl()
        self.assertTrue(len(ctx.revisions) == 0)
        conn = pymonetdb.connect(self.db_name)
        sql = """insert into sys.mroll_revisions values ('{}', '{}', '{}'), ('{}', '{}', '{}');""".format(gen_rev_id(), "revision 1", datetime.now(), gen_rev_id(), "revision 2", datetime.now())
        conn.execute(sql)
        conn.commit()
        self.assertTrue(len(ctx.revisions) == 2)

    def test_ctx_add_revisions(self):
        wd = WorkDirectory(path=self.work_dir)
        ctx = create_migration_ctx(wd.get_migration_ctx_config())
        ctx.create_revisions_tbl()
        self.assertTrue(len(ctx.revisions) == 0)
        revisions = [
            Revision(
                gen_rev_id(), "adding table foo", datetime.now(),
                upgrade_sql="create table test.foo (a string);",
                downgrade_sql="drop table test.foo;"
                ),
            Revision(
                gen_rev_id(), "adding table bar", datetime.now(),
                upgrade_sql="create table test.bar (a string);",
                downgrade_sql="drop table test.bar;"
                )
            ]
        ctx.add_revisions(revisions)
        self.assertTrue(len(ctx.revisions) == 2)

    def test_ctx_remove_revisions(self):
        wd = WorkDirectory(path=self.work_dir)
        ctx = create_migration_ctx(wd.get_migration_ctx_config())
        ctx.create_revisions_tbl()
        self.assertTrue(len(ctx.revisions) == 0)
        id_1 = gen_rev_id()
        id_2 = gen_rev_id()
        d_1 = datetime.now()
        d_2 = datetime.now()
        conn = pymonetdb.connect(self.db_name)
        sql = """insert into sys.mroll_revisions values ('{}', '{}', '{}'), ('{}', '{}', '{}');""".format(id_1, "revision 1", d_1, id_2, "revision 2", d_2)
        conn.execute(sql)
        conn.commit()
        self.assertTrue(len(ctx.revisions) == 2)
        revisions = [Revision(id_1, "revision 1", d_1),Revision(id_2, "revision 2", d_2)]
        ctx.remove_revisions(revisions)
        self.assertTrue(len(ctx.revisions) == 0)
