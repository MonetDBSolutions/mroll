import os
import shutil
import unittest
import logging
import shutil
from click.testing import CliRunner

from mdb import __version__

def test_version():
    assert __version__ == '0.1.0'

class TestCommands(unittest.TestCase):
    work_dir = os.path.join('/tmp', 'migrations')

    def setUp(self):
        pass

    def tearDown(self):
        if os.path.exists(self.work_dir):
            shutil.rmtree(self.work_dir)
        from mdb.commands import MDB_CONFIG_DIR
        if os.path.exists(MDB_CONFIG_DIR):
            shutil.rmtree(MDB_CONFIG_DIR)

    def run_setup_cmd(self):
        from mdb.commands import setup
        runner = CliRunner() 
        return runner.invoke(setup, ['-p', str(self.work_dir)])

    def test_setup_command(self):
        result = self.run_setup_cmd()
        self.assertTrue(result.exit_code == 0)
        from mdb.commands import MDB_CONFIG_FILE
        self.assertTrue(os.path.exists(MDB_CONFIG_FILE))

    def test_init_cmd(self):
        from mdb.commands import init
        self.run_setup_cmd()
        runner = CliRunner()
        res = runner.invoke(init)
        self.assertTrue(res.exit_code==0)
    
    def test_revision_cmd(self):
        from mdb.commands import revision
        self.run_setup_cmd()
        runner = CliRunner()
        res = runner.invoke(revision, ['-m', 'add column to foo'])
        self.assertTrue(res.exit_code==0)
        
