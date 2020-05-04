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
    def __init__(self, id_, description, ts, upgrade_sql=None, downgrade_sql=None):
        self.id = id_
        self.description = description
        self.ts = ts
        self.upgrade_sql = upgrade_sql
        self.downgrade_sql = downgrade_sql

    def __repr__(self):
        return "<Revision id={} description={}>".format(self.id, self.description)

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

def parse_rev_file(rev_file) -> Revision:
    """
    Parse revision file with following format:
    -- identifiers used by mdb
    -- id=<revision_id>
    -- description=<revision description>
    -- ts=<time stamp>
    -- migration:upgrade
        <sql text>

    -- migration:downgrade
        <sql text>
    """
    with open(rev_file, 'rt') as file_:
        for l in file_:
            if 'id=' in l:
                id_ = l.split('id=').pop().strip()
                continue
            if 'description=' in l:
                description = l.split('description=').pop().strip()
                continue
            if 'ts=' in l:
                ts = l.split('ts=').pop().strip()
                continue
            if 'migration:upgrade' in l:
                break
        upgrade_sql = ''
        for l in file_:
            if 'migration:downgrade' in l:
                break
            upgrade_sql+=l
        downgrade_sql = ''
        for l in file_:
            downgrade_sql+=l
        assert id_
        assert description
        assert ts
        return Revision(id_, description, ts, upgrade_sql=upgrade_sql, downgrade_sql=downgrade_sql)



class WorkDirectory:
    def __init__(self, path):
        if not os.path.exists(path) and not os.listdir(path):
            raise RuntimeError('Script directory not initilezed. Run setup command first!')
        self.path = path
        self.revisions = self.load_revisions(path)

    def load_revisions(self, path):
        vers_dir = os.path.join(path or self.path, 'versions')
        res = []
        for f in os.listdir(vers_dir):
            if f.endswith('.sql'):
                res.append(parse_rev_file(os.path.join(vers_dir, f)))
        res.sort(key=lambda rev: datetime.fromisoformat(rev.ts))
        return res


# ----------------------------------

@click.group(chain=True)
@click.pass_context
def cli(ctx):
    ctx.ensure_object(dict)

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
    if not os.path.exists(SYS_CONFIG):
        os.mkdir(SYS_CONFIG)
    if not os.path.exists(MDB_CONFIG_DIR):
        os.mkdir(MDB_CONFIG_DIR)
    config = configparser.ConfigParser()
    config['mdb'] = dict(work_dir=directory)
    with open(MDB_CONFIG_FILE, 'w') as configfile:
        config.write(configfile)
    assert os.path.exists(MDB_CONFIG_FILE)
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
            fw.write('-- identifiers used by mdb\n')
            header = "-- id={}\n-- description={}\n-- ts={}\n".format(id_, description, ts)
            fw.write(header)
            fw.write(template)
        assert os.path.exists(fn)
    print('ok')

@cli.command(name='history')
def history():
    migr_ctx = MigrationContext.from_env(get_env())
    for r in migr_ctx.revisions:
        print('id={} desc={} ts={}'.format(r.id, r.description, r.ts))

@cli.command(name="show")
@click.pass_context
def show(ctx):
    ctx.obj['show_cmd'] = True
    
@cli.command(name="all_revisions")
def all_revisions():
    config = Config.from_file(MDB_CONFIG_FILE)
    wd = WorkDirectory(config.work_dir)
    for rev in wd.revisions:
        print(rev)

@cli.command(name='new_revisions')
def new_revisions():
    # TODO
    print('TODO: showing new revisions')

if __name__ == '__main__':
    cli()