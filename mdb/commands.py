#!/usr/bin/env python3

import click
import os
import shutil
import configparser
from os.path import expanduser
from datetime import datetime
import importlib.util
import importlib.machinery
from functools import wraps

HOME = expanduser("~")
SYS_CONFIG = os.path.join(HOME, '.config')
MDB_CONFIG_DIR = os.path.join(SYS_CONFIG, 'mdb')
MDB_CONFIG_FILE = os.path.join(MDB_CONFIG_DIR, 'config.ini')


def load_module_py(module_id, path):
    spec = importlib.util.spec_from_file_location(module_id, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def get_templates_dir():
    dir_ = os.path.dirname(__file__)
    return os.path.join(dir_, 'templates')

def get_env():
    config = Config.from_file(MDB_CONFIG_FILE)
    path = os.path.join(config.work_dir, 'env.py')
    env = load_module_py('env', path)
    return env

def rev_id():
    import uuid
    return uuid.uuid4().hex[-12:]

class Config:
    work_dir = None

    @classmethod
    def from_file(cls, configfile):
        if not os.path.exists(configfile):
            raise RuntimeError('No config file found in \'{}\'. Run setup command first!'.format(MDB_CONFIG_DIR))
        import configparser
        config = configparser.ConfigParser()
        config.read(configfile)
        mdb_config_map = config['mdb']
        conf = cls.__new__(cls)
        for k in mdb_config_map:
            setattr(conf, k, mdb_config_map[k])
        return conf

    
class Revision:
    def __init__(self, id_, ts, description, upgrade=None, downgrade=None):
        self.id_ = id_
        self.ts = ts
        self.description = description
        self.upgrade = upgrade
        self.downgrade = downgrade

class MigrationContext:
    def __init__(self, head=None, revisions=[]):
        self.head = head
        self.revisions = revisions

    def __repr__(self):
        return "<MigrationContext head={} revisions={}>".format(self.head, self.revisions)

    @classmethod
    def from_env(cls, env):
        head = env.get_head()
        revisions = [Revision(id_, description, ts) for id_, description, ts in env.get_revisions()]
        mc = cls.__new__(cls)
        mc.head = head
        mc.revisions = revisions
        return mc

class WorkDirectory:
    def __init__(self, path):
        if not os.path.exists(path) and not os.listdir(path):
            raise RuntimeError('Script directory not initilezed. Run setup command first!')
        self.path=path

    def load_revissions(self):
        pass


# ----------------------------------

@click.group()
def cli():
    pass

@cli.command(name='setup')
@click.option('-d', '--dir', 'dir_', default='migrations', help='name of the work directory')
@click.option('-p', '--path', help='path to work directory')
def setup(dir_, path):
    directory = path or os.path.join(os.getcwd(), dir_)
    if os.access(directory, os.F_OK) and os.listdir(directory):
        raise ValueError("Directory %s already exists and is not empty" % directory)
    versions = os.path.join(directory, 'versions')
    os.mkdir(directory)
    os.mkdir(versions)
    tmpl_dir = get_templates_dir()
    shutil.copy(os.path.join(tmpl_dir, 'mdb.ini'), directory)
    shutil.copy(os.path.join(tmpl_dir, 'env.py'), directory)
    #  setup config file
    home = expanduser("~")
    sys_config = os.path.join(home, '.config')
    if not os.path.exists(sys_config):
        os.mkdir(sys_config)
    if not os.path.exists(os.path.join(sys_config, 'mdb')):
        os.mkdir(os.path.join(sys_config, 'mdb'))
    config = configparser.ConfigParser()
    config['mdb'] = dict(work_dir=directory)
    mdb_config = os.path.join(sys_config, 'mdb', 'config.ini')
    with open(mdb_config, 'w') as configfile:
        config.write(configfile)
    print('ok')

@cli.command(name='init')
def init():
    env = get_env()
    try:
        # env.create_head_tbl() and print('head tbl created')
        env.create_revisions_table() and print('rev tbl created')
        print('done')
    except Exception as e:
        print(e)
    
@cli.command(name='revision')
@click.option('-m', '--message', help='gets added to revision name')
def revision(message):
    """
    Creates new revision file from a template.
    """
    config = Config.from_file(MDB_CONFIG_FILE)
    wd = WorkDirectory(config.work_dir)
    ts = datetime.now().isoformat()
    id_ = rev_id()
    description = message or ''
    file_ = os.path.join(get_templates_dir(), 'revision_template.txt')
    with open(file_, 'r') as f:
        template = f.read()
        kebab = description.strip().replace(' ', '_')
        fn = os.path.join(wd.path, 'versions', '{}_{}.sql'.format(id_, kebab))
        with open(fn, 'w+') as fw:
            header = "-- {}\n-- {}\n-- {}\n".format(id_, description, ts)
            fw.write(header)
            fw.write(template)
        assert os.path.exists(fn)
    print('ok')

@cli.command(name='history')
def history():
    migr_ctx = MigrationContext.from_env(get_env())
    for r in migr_ctx.revisions:
        print('id={} desc={} ts={}'.format(r.id, r.description, r.ts))


if __name__ == '__main__':
    cli()