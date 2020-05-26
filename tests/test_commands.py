import os
import shutil
import unittest
from datetime import datetime
from click.testing import CliRunner
import pymonetdb

from mroll import __version__
from mroll.commands import *
from mroll.migration import Revision, gen_rev_id
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
        conn = pymonetdb.connect(self.db_name)
        conn.execute('create schema test;')
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
            conn.execute("drop table sys.mroll_revisions;")
            conn.execute("drop schema test cascade")
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
        # another try
        res = self.run_init_cmd()
        self.assertNotEqual(res.stdout, '')

    def test_revision_cmd(self):
        res = self.add_rev_cmd('add column b to foo')
        self.assertTrue(res.exit_code==0)

    def test_show_all_revisions(self):
        self.add_rev_cmd('add column a to foo')
        self.add_rev_cmd('add column b to foo')
        self.add_rev_cmd('add column c to foo')
        runner = CliRunner()
        res = runner.invoke(show, ['all'])
        self.assertTrue(res.exit_code==0)

    def test_show_pending_revisions(self):
        wd = WorkDirectory(self.work_dir)
        wd.add_revision(
            Revision(
                gen_rev_id(), "adding table bar", datetime.now(),
                upgrade_sql="create table test.bar (a string);",
                downgrade_sql="drop table test.bar"
            )
        )
        self.assertTrue(len(wd.revisions) == 1)
        runner = CliRunner()
        res = runner.invoke(upgrade)
        self.assertTrue(res.exit_code==0)
        migr_ctx = MigrationContext.from_env(get_env())
        self.assertIsNotNone(migr_ctx.head)
        self.assertTrue(len(migr_ctx.revisions) == 1)
        self.add_rev_cmd('add column a to bar')
        self.add_rev_cmd('add column a to baz')
        self.assertTrue(len(wd.revisions) == 3)
        wd = WorkDirectory(self.work_dir)
        res = runner.invoke(show, ['pending'])
        self.assertTrue(res.exit_code==0)

    def test_show_applied_revisions(self):
        wd = WorkDirectory(self.work_dir)
        wd.add_revision(
            Revision(
                gen_rev_id(), "adding table bar", datetime.now(),
                upgrade_sql="create table test.bar (a string);",
                downgrade_sql="drop table test.bar"
                )
        )
        self.assertTrue(len(wd.revisions) == 1)
        runner = CliRunner()
        res = runner.invoke(upgrade)
        self.assertTrue(res.exit_code==0)
        res = runner.invoke(show, ['applied'])
        self.assertTrue(res.exit_code==0)
        self.assertNotEqual(res.stdout, '')
        
    def test_upgrade_default_cmd(self):
        #  Test upgrade with no options
        migr_ctx = MigrationContext.from_env(get_env())
        wd = WorkDirectory(self.work_dir)
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
        for rev in revisions:
            wd.add_revision(rev)
        self.assertTrue(len(wd.revisions) == 2)
        runner = CliRunner()
        res = runner.invoke(upgrade)
        self.assertTrue(res.exit_code==0)
        migr_ctx = MigrationContext.from_env(get_env())
        self.assertIsNotNone(migr_ctx.head)
        self.assertTrue(len(migr_ctx.revisions) == 2)

    def test_upgrade_num_command(self):
        # Test upgrade cmd with a step 
        migr_ctx = MigrationContext.from_env(get_env())
        wd = WorkDirectory(self.work_dir)
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
        for rev in revisions:
            wd.add_revision(rev)
        self.assertTrue(len(wd.revisions) == 2)
        runner = CliRunner()
        res = runner.invoke(upgrade, ['-n', 1])
        self.assertTrue(res.exit_code==0)
        migr_ctx = MigrationContext.from_env(get_env())
        self.assertIsNotNone(migr_ctx.head)
        self.assertTrue(len(migr_ctx.revisions) == 1)

    def test_upgrade_raise(self):
        migr_ctx = MigrationContext.from_env(get_env())
        self.assertIsNone(migr_ctx.head)
        wd = WorkDirectory(self.work_dir)
        wd.add_revision(Revision(gen_rev_id(), "adding table foo", datetime.now()))
        self.assertTrue(len(wd.revisions) == 1)
        runner = CliRunner()
        res = runner.invoke(upgrade)
        self.assertTrue(res.exit_code==1)

    def test_rollback_default_cmd(self):
        # test rollback no cli options
        migr_ctx = MigrationContext.from_env(get_env())
        self.assertIsNone(migr_ctx.head)
        wd = WorkDirectory(self.work_dir)
        wd.add_revision(
            Revision(
                gen_rev_id(), "adding table foo", datetime.now(),
                upgrade_sql="create table test.foo (a string);",
                downgrade_sql="drop table test.foo;"
                )
        )
        self.assertTrue(len(wd.revisions) == 1)
        runner = CliRunner()
        res = runner.invoke(upgrade)
        self.assertTrue(res.exit_code==0)
        migr_ctx = MigrationContext.from_env(get_env())
        self.assertIsNotNone(migr_ctx.head)
        self.assertTrue(len(migr_ctx.revisions) == 1)
        res = runner.invoke(rollback)
        self.assertTrue(res.exit_code==0)
        migr_ctx = MigrationContext.from_env(get_env())
        self.assertIsNone(migr_ctx.head)
        self.assertTrue(len(migr_ctx.revisions) == 0)

    def test_rollback_step_cmd(self):
        migr_ctx = MigrationContext.from_env(get_env())
        self.assertIsNone(migr_ctx.head)
        wd = WorkDirectory(self.work_dir)
        runner = CliRunner()
        wd.add_revision(
            Revision(
                gen_rev_id(), "adding table foo", datetime.now(),
                upgrade_sql="create table test.foo (a string);",
                downgrade_sql="drop table test.foo"
                )
        )
        res = runner.invoke(upgrade)
        self.assertTrue(res.exit_code==0)
        wd.add_revision(
            Revision(
                gen_rev_id(), "adding table bar", datetime.now(),
                upgrade_sql="create table test.bar (a string);",
                downgrade_sql="drop table test.bar"
                )
        )
        res = runner.invoke(upgrade)
        self.assertTrue(res.exit_code==0)
        migr_ctx = MigrationContext.from_env(get_env())
        self.assertIsNotNone(migr_ctx.head)
        self.assertTrue(len(migr_ctx.revisions) == 2)
        res = runner.invoke(rollback, ['-n', 2])
        migr_ctx = MigrationContext.from_env(get_env())
        self.assertIsNone(migr_ctx.head)

    def test_rollback_raises(self):
        migr_ctx = MigrationContext.from_env(get_env())
        self.assertIsNone(migr_ctx.head)
        wd = WorkDirectory(self.work_dir)
        runner = CliRunner()
        # add revison with no downgrade_sql
        wd.add_revision(
            Revision(
                gen_rev_id(), "adding table foo", datetime.now(),
                upgrade_sql="create table test.foo (a string);",
                )
        )
        res = runner.invoke(upgrade)
        self.assertTrue(res.exit_code==0)
        migr_ctx = MigrationContext.from_env(get_env())
        self.assertIsNotNone(migr_ctx.head)
        self.assertTrue(len(migr_ctx.revisions) == 1)
        res = runner.invoke(rollback)
        self.assertNotEqual(res.exit_code, 0)

