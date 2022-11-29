import os
from pathlib import Path
import shutil
from tempfile import mkdtemp
import unittest

from click.testing import CliRunner
import pymonetdb

from mroll.commands import *

# The idea for the ad-hoc commands is that we have already a database
# that has some migrations applied and a non-empty migrations
# directory.  The use case is the re-deployment of a service that uses
# mroll. We clone the service's source code, we restore the database
# from a backup and we need to apply any migrations that have been
# added since last time. This usually fails because `mroll setup` has
# not been ran, and when we run it, it fails with the error that the
# `migrations` directory is not empty.

class TestAdHoc(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_name = 'mroll_test_db'
        cls.connection = pymonetdb.connect(cls.db_name, autocommit=True)

    @classmethod
    def tearDownClass(cls):
        cls.connection.close()

    def setUp(self):
        self.work_dir = mkdtemp()
        data_dir = Path(__file__).parent / "data"
        shutil.copytree(data_dir, self.work_dir, dirs_exist_ok=True)
        self.work_path = Path(self.work_dir)


        self.connection.execute("create schema if not exists test")
        self.connection.execute("create table if not exists sys.mroll_revisions(id string primary key, description string, ts timestamp)")


    def tearDown(self):
        if os.path.exists(self.work_dir):
            shutil.rmtree(self.work_dir)

        self.connection.execute("drop table sys.mroll_revisions;")
        self.connection.execute("drop schema test cascade;")


    def test_revision(self):
        runner = CliRunner()
        res = runner.invoke(revision, ['-m', 'test-revision', '-d', self.work_dir])
        self.assertEqual(res.exit_code, 0)   # mroll revision ran correctly
        ln = list(self.work_path.rglob('*test-revision*'))
        self.assertEqual(len(ln), 1)   # it created one file that matches the glob *test-revision*

    def test_upgrade(self):
        runner = CliRunner()
        res = runner.invoke(upgrade, ['-d', self.work_path])
        self.assertEqual(res.exit_code, 0)

        # make sure that the SQL commands in the revision had an
        # effect.

        cur = self.connection.cursor()
        r = cur.execute("select * from test.revision0")
        self.assertEqual(r, 2)

    def test_history(self):
        runner = CliRunner()
        res = runner.invoke(upgrade, ['-d', self.work_path])
        self.assertEqual(res.exit_code, 0)
        res = runner.invoke(history, ['-d', self.work_path])
        self.assertEqual(res.exit_code, 0)
        # count the lines in the output
        self.assertEqual(res.output.count("\n"), 1)
        self.assertTrue("test revision 0" in res.output)

    def test_show_pending(self):
        runner = CliRunner()
        res = runner.invoke(pending, ['-d', self.work_path])
        self.assertEqual(res.exit_code, 0)
        self.assertEqual(res.output.count("\n"), 1)
        self.assertTrue("test revision 0" in res.output)

    def test_show_all(self):
        runner = CliRunner()
        res = runner.invoke(upgrade, ['-d', self.work_path])
        self.assertEqual(res.exit_code, 0)
        res = runner.invoke(revision, ['-m', 'test revision 1', '-d', self.work_dir])
        self.assertEqual(res.exit_code, 0)
        res = runner.invoke(all, ['-d', self.work_dir])
        self.assertEqual(res.exit_code, 0)
        # count the lines in the output
        self.assertEqual(res.output.count("\n"), 2)
        self.assertTrue("test revision 0" in res.output)
        self.assertTrue("test revision 1" in res.output)

    def test_show_applied(self):
        runner = CliRunner()
        res = runner.invoke(upgrade, ['-d', self.work_path])
        self.assertEqual(res.exit_code, 0)
        res = runner.invoke(revision, ['-m', 'test revision 1', '-d', self.work_dir])
        self.assertEqual(res.exit_code, 0)
        res = runner.invoke(applied, ['-d', self.work_dir])
        self.assertEqual(res.exit_code, 0)
        self.assertEqual(res.output.count("\n"), 1)
        self.assertTrue("test revision 0" in res.output)
        self.assertTrue("test revision 1" not in res.output)

    def test_rollback(self):
        runner = CliRunner()
        res = runner.invoke(upgrade, ['-d', self.work_path])
        self.assertEqual(res.exit_code, 0)

        # make sure that the upgrade ran
        cur = self.connection.cursor()
        r = cur.execute("select * from test.revision0;")
        self.assertEqual(r, 2)

        res = runner.invoke(rollback, ['-d', self.work_path])
        cur = self.connection.cursor()
        r = cur.execute("select * from sys.mroll_revisions;")
        self.assertEqual(r, 0)
