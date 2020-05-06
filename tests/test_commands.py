import os
import shutil
import unittest
import logging
import shutil
from click.testing import CliRunner

from mdb import __version__
from mdb.commands import *

def test_version():
    assert __version__ == '0.1.0'

class TestCommands(unittest.TestCase):
    work_dir = os.path.join('/tmp', 'migrations')
    setup_res = None

    def setUp(self):
        self.setup_res = self.run_setup_cmd()

    def tearDown(self):
        if os.path.exists(self.work_dir):
            shutil.rmtree(self.work_dir)
        if os.path.exists(MDB_CONFIG_DIR):
            shutil.rmtree(MDB_CONFIG_DIR)

    def run_setup_cmd(self):
        runner = CliRunner() 
        return runner.invoke(setup, ['-p', str(self.work_dir)])

    def add_rev_cmd(self, message):
        runner = CliRunner()
        return runner.invoke(revision, ['-m', str(message)])

    def test_setup_command(self):
        res = self.setup_res
        self.assertTrue(res.exit_code == 0)
        self.assertTrue(os.path.exists(MDB_CONFIG_FILE))

    def test_init_cmd(self):
        runner = CliRunner()
        res = runner.invoke(init)
        self.assertTrue(res.exit_code==0)
    
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
        
    def test_upgrade_cmd(self):

        pass

    def test_downgrade_cmd(self):
        pass

    def test_rollback_cmd(self):
        pass