import os
import unittest
from mdb.commands import parse_rev_file, Revision

class TestUtils(unittest.TestCase):

    def test_parse_rev_file(self):
        content="""
        -- identifiers used by mdb
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
        res: Revision = parse_rev_file(fn)
        self.assertEqual(res.id, '099c9a23ab3b')
        self.assertEqual(res.description, 'add column')
        self.assertEqual(res.ts, '2020-05-04T23:14:37.498799')
        self.assertIsNotNone(res.upgrade_sql)
        self.assertIsNotNone(res.downgrade_sql)


