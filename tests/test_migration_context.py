import os
import shutil
from unittest import TestCase
from click.testing import CliRunner
from mroll.migration import Revision, get_all_upgrade_sql
from mroll.commands import setup, revision, rev_id
from mroll.config import MROLL_CONFIG_DIR

class TestMigrationContext(TestCase):
    work_dir = os.path.join('/tmp', 'migrations')
    db_name = os.environ.get('TEST_DB_NAME', 'mroll_test_db')

    def setUp(self):
        runner = CliRunner() 
        runner.invoke(setup, ['-p', str(self.work_dir)])
        
    def tearDown(self):
        if os.path.exists(self.work_dir):
            shutil.rmtree(self.work_dir)
        if os.path.exists(MROLL_CONFIG_DIR):
            shutil.rmtree(MROLL_CONFIG_DIR)
    
    def add_rev_cmd(self, message):
        runner = CliRunner()
        return runner.invoke(revision, ['-m', str(message)])

    def test_rev_from_file(self):
        content="""
        -- identifiers used by mroll
        -- id=099c9a23ab3b
        -- description=add column
        -- ts=2020-05-04T23:14:37.498799
        -- migration:upgrade
            alter table foo add column b string;

        -- migration:downgrade
            alter table foo drop column b;
        """
        fn = '/tmp/foo.sql'
        with open(fn, 'wt') as f:
            f.write(content)
        res = Revision.from_file(fn)
        self.assertEqual(res.id, '099c9a23ab3b')
        self.assertEqual(res.description, 'add column')
        self.assertEqual(res.ts, '2020-05-04T23:14:37.498799')
        self.assertIsNotNone(res.upgrade_sql)
        self.assertIsNotNone(res.downgrade_sql)

    def test_serialize(self):
        content="""
        -- identifiers used by mroll
        -- id=099c9a23ab3b
        -- description=add column
        -- ts=2020-05-04T23:14:37.498799
        -- migration:upgrade
            alter table foo add column b string;

        -- migration:downgrade
            alter table foo drop column b;
        """

        rev = Revision(
            '099c9a23ab3b',
            'add column',
            '2020-05-04T23:14:37.498799',
            upgrade_sql='alter table foo add column b string;',
            downgrade_sql='alter table foo drop column b;')
        pass
        # print()
        # res = rev.serialize().strip()
        # print(res)
        # expected = content.strip()
        # print()
        # print(expected)
        # self.assertEquals(res, expected)

    def test_get_all_upgrade_sql(self):
        for i in range(3):
            id_ = rev_id()
            content="""
            -- identifiers used by mroll
            -- id={}
            -- description=add column
            -- ts=2020-05-04T23:14:37.498799
            -- migration:upgrade
                alter table foo add column b string;

            -- migration:downgrade
            """.format(id_)
            fn = os.path.join(self.work_dir, 'versions', "{}.sql".format(id_))
            with open(fn, 'w') as f:
                f.write(content)
        res = get_all_upgrade_sql(self.work_dir)
        self.assertNotEqual(res, '')



