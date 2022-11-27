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
        data_dir = Path(__file__).parent / "data"
        shutil.copy2(data_dir, self.work_dir)
        self.work_path = Path(self.work_dir)
        self.db_name = 'mroll_test_db'

    def tearDown(self):
        if os.path.exists(self.work_dir):
            shutil.rmtree(self.work_dir)

    def test_revision(self):
        runner = CliRunner()
        r = runner.invoke(revision, ['-m', 'test-revision', '-d', self.work_dir])
        self.assertEqual(r.exit_code, 0)   # mroll revision ran correctly
        ln = list(self.work_path.rglob('*test-revision*'))
        self.assertEqual(len(ln), 1)   # it created one file that matches the glob *test-revision*

    def test_history(self):
        pass
