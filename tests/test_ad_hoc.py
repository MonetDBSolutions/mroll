import os
from pathlib import Path
import shutil
from tempfile import mkdtemp
import unittest

from click.testing import CliRunner

from mroll.commands import *

class TestAdHoc(unittest.TestCase):
    def setUp(self):
        self.work_dir = mkdtemp()
        self.work_path = Path(self.work_dir)
        v = self.work_path / 'versions'
        v.mkdir()  # create versions directory
        self.db_name = os.environ.get('TEST_DB_NAME', 'mroll_test_db')

    def tearDown(self):
        if os.path.exists(self.work_dir):
            shutil.rmtree(self.work_dir)

    def test_revision(self):
        runner = CliRunner()
        r = runner.invoke(revision, ['-m', 'test-revision', '-d', self.work_dir])
        self.assertEqual(r.exit_code, 0)   # mroll revision ran correctly
        ln = list(self.work_path.rglob('*test-revision*'))
        self.assertEqual(len(ln), 1)   # it created one file that matches the glob *test-revision*
