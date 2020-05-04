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

    def add_rev_cmd(self, message):
        from mdb.commands import revision
        runner = CliRunner()
        return runner.invoke(revision, ['-m', str(message)])

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
        self.run_setup_cmd()
        res = self.add_rev_cmd('add column b to foo')
        self.assertTrue(res.exit_code==0)

    def test_show_all_revisions(self):
        self.run_setup_cmd()
        self.add_rev_cmd('add column a to foo')
        self.add_rev_cmd('add column b to foo')
        self.add_rev_cmd('add column c to foo')
        from mdb.commands import all_revisions
        runner = CliRunner()
        res = runner.invoke(all_revisions)
        self.assertTrue(res.exit_code==0)
        
