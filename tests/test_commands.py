import os
import shutil
import unittest
from click.testing import CliRunner
import pymonetdb

from mroll import __version__
from mroll.commands import *
from mroll.config import MROLL_CONFIG_DIR

def test_version():
    assert __version__ == '0.1.0'

class TestCommands(unittest.TestCase):
    work_dir = os.path.join('/tmp', 'migrations')
    setup_res = None
    init_res = None
    db_name = os.environ.get('TEST_DB_NAME', 'mroll_test_db')

    def setUp(self):
        self.setup_res = self.run_setup_cmd()
        self.set_config_db_name(self.db_name)
        self.init_res = self.run_init_cmd()
        
    def tearDown(self):
        if os.path.exists(self.work_dir):
            shutil.rmtree(self.work_dir)
        if os.path.exists(MROLL_CONFIG_DIR):
            shutil.rmtree(MROLL_CONFIG_DIR)
        self.drop_tables()

    def drop_tables(self):
        conn = pymonetdb.connect(self.db_name)
        try:
            conn.execute("drop table sys.mroll_revisions;")
            conn.commit()
        except Exception as e:
            print(e)
        finally:
            conn.close()

    def run_setup_cmd(self):
        runner = CliRunner() 
        return runner.invoke(setup, ['-p', str(self.work_dir)])

    def run_init_cmd(self):
        runner = CliRunner() 
        return runner.invoke(init)

    def add_rev_cmd(self, message):
        runner = CliRunner()
        return runner.invoke(revision, ['-m', str(message)])

    def set_config_db_name(self, db_name):
        wd = WorkDirectory(path=self.work_dir)
        wd._set_config('db', 'db_name', db_name)

    def test_setup_command(self):
        res = self.setup_res
        self.assertTrue(res.exit_code == 0)
        self.assertTrue(os.path.exists(MROLL_CONFIG_FILE))

    def test_init_cmd(self):
        res = self.init_res
        self.assertTrue(res.exit_code == 0)
    
    def test_revision_cmd(self):
        res = self.add_rev_cmd('add column b to foo')
        self.assertTrue(res.exit_code==0)

    def test_show_all_revisions(self):
        self.add_rev_cmd('add column a to foo')
        self.add_rev_cmd('add column b to foo')
        self.add_rev_cmd('add column c to foo')
        runner = CliRunner()
        res = runner.invoke(all_revisions)
        self.assertTrue(res.exit_code==0)
        
    def test_upgrade_all_cmd(self):
        migr_ctx = MigrationContext.from_env(get_env())
        self.assertIsNone(migr_ctx.head)
        self.add_rev_cmd('create tbl foo')
        wd = WorkDirectory(self.work_dir)
        self.assertTrue(len(wd.revisions) == 1)
        runner = CliRunner()
        res = runner.invoke(upgrade)
        self.assertTrue(res.exit_code==0)
        migr_ctx = MigrationContext.from_env(get_env())
        self.assertIsNotNone(migr_ctx.head)
        self.assertTrue(len(migr_ctx.revisions) == 1)

    def test_upgrade_num_command(self):
        migr_ctx = MigrationContext.from_env(get_env())
        self.assertIsNone(migr_ctx.head)
        self.add_rev_cmd('create tbl foo')
        self.add_rev_cmd('create tbl bar')
        wd = WorkDirectory(self.work_dir)
        self.assertTrue(len(wd.revisions) == 2)
        runner = CliRunner()
        res = runner.invoke(upgrade, ['-n', 1])
        self.assertTrue(res.exit_code==0)
        migr_ctx = MigrationContext.from_env(get_env())
        self.assertIsNotNone(migr_ctx.head)
        self.assertTrue(len(migr_ctx.revisions) == 1)

    def test_rollback_default_cmd(self):
        migr_ctx = MigrationContext.from_env(get_env())
        self.assertIsNone(migr_ctx.head)
        self.add_rev_cmd('create tbl foo')
        wd = WorkDirectory(self.work_dir)
        self.assertTrue(len(wd.revisions) == 1)
        runner = CliRunner()
        res = runner.invoke(upgrade)
        self.assertTrue(res.exit_code==0)
        migr_ctx = MigrationContext.from_env(get_env())
        self.assertIsNotNone(migr_ctx.head)
        self.assertTrue(len(migr_ctx.revisions) == 1)
        res = runner.invoke(rollback)
        migr_ctx = MigrationContext.from_env(get_env())
        self.assertIsNone(migr_ctx.head)
        self.assertTrue(len(migr_ctx.revisions) == 0)

    def test_rollback_step_cmd(self):
        migr_ctx = MigrationContext.from_env(get_env())
        self.assertIsNone(migr_ctx.head)
        self.add_rev_cmd('create tbl foo')
        self.add_rev_cmd('create tbl bar')
        self.add_rev_cmd('create tbl baz')
        wd = WorkDirectory(self.work_dir)
        self.assertTrue(len(wd.revisions) == 3)
        runner = CliRunner()
        res = runner.invoke(upgrade)
        self.assertTrue(res.exit_code==0)
        migr_ctx = MigrationContext.from_env(get_env())
        self.assertIsNotNone(migr_ctx.head)
        self.assertTrue(len(migr_ctx.revisions) == 3)
        res = runner.invoke(rollback, ['-n', 2])
        migr_ctx = MigrationContext.from_env(get_env())
        self.assertIsNotNone(migr_ctx.head)
        self.assertTrue(len(migr_ctx.revisions) == 1)
