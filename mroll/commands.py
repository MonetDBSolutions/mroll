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
MDB_CONFIG_DIR = os.path.join(SYS_CONFIG, 'mroll')
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
        mdb_config_map = config['mroll']
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

    def serialize(self):
        from io import StringIO
        res=''
        with StringIO() as buf:
            buf.write('-- identifiers used by mroll\n')
            buf.write('-- id={}\n'.format(self.id))
            ts = self.ts.isoformat() if type(self.ts) == datetime else self.ts
            buf.write('-- ts={}\n'.format(ts))
            buf.write('-- migration:upgrade\n')
            buf.write('{}\n'.format(self.upgrade_sql))
            buf.write('-- migration:downgrade\n')
            buf.write('{}\n'.format(self.downgrade_sql))
            res = buf.getvalue()
        return res

    @classmethod
    def from_file(cls, rev_file):
        """
        Parse revision file with following format:
        -- identifiers used by mroll
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
            rev = cls.__new__(cls)
            setattr(rev, 'id', id_)
            setattr(rev, 'description', description)
            setattr(rev, 'ts', ts)
            setattr(rev, 'upgrade_sql', upgrade_sql.strip())
            setattr(rev, 'downgrade_sql', downgrade_sql.strip())
            return rev


class MigrationContext:
    def __init__(self, head=None, revisions=[]):
        self.head = head
        self.revisions = revisions

    def __repr__(self):
        return "<MigrationContext head={} revisions={}>".format(self.head, self.revisions)

    @classmethod
    def from_env(cls, env):
        head = env.get_head()
        if head is not None:
            id_, description, ts = head
            head = Revision(id_, description, ts)
        revisions = [Revision(id_, description, ts) for id_, description, ts in env.get_revisions()]
        mc = cls.__new__(cls)
        mc.head = head
        mc.revisions = revisions
        return mc


class WorkDirectory:
    def __init__(self, path):
        if not os.path.exists(path) and not os.listdir(path):
            raise RuntimeError('Script directory not initilezed. Run setup command first!')
        self.path = path
        # self.revisions = self.load_revisions(path)

    @property
    def config(self):
        configfile = os.path.join(self.path, 'mroll.ini')
        config = configparser.ConfigParser()
        config.read(configfile)
        return config

    def _set_config(self, section, key, value):
        """
        Alter work dir config file (mroll.ini). Used in setting up test scenarios.
        Otherwise end user should directly edit the file.
        """
        configfile = os.path.join(self.path, 'mroll.ini')
        config = self.config
        config[section][key] = value
        with open(configfile, 'w') as f:
            config.write(f)

    @property
    def revisions(self):
        return self.load_revisions(self.path)

    def load_revisions(self, path):
        vers_dir = os.path.join(path or self.path, 'versions')
        res = []
        for f in os.listdir(vers_dir):
            if f.endswith('.sql'):
                rev_file = os.path.join(vers_dir, f)
                res.append(Revision.from_file(rev_file))
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
    """
    Set up work directory. Should be run once.
    """
    directory = path or os.path.join(os.getcwd(), dir_)
    if os.access(directory, os.F_OK) and os.listdir(directory):
        raise ValueError("Directory %s already exists and is not empty" % directory)
    versions = os.path.join(directory, 'versions')
    os.mkdir(directory)
    os.mkdir(versions)
    tmpl_dir = get_templates_dir()
    shutil.copy(os.path.join(tmpl_dir, 'mroll.ini'), directory)
    shutil.copy(os.path.join(tmpl_dir, 'env.py'), directory)
    #  setup config file
    if not os.path.exists(SYS_CONFIG):
        os.mkdir(SYS_CONFIG)
    if not os.path.exists(MDB_CONFIG_DIR):
        os.mkdir(MDB_CONFIG_DIR)
    config = configparser.ConfigParser()
    config['mroll'] = dict(work_dir=directory)
    with open(MDB_CONFIG_FILE, 'w') as configfile:
        config.write(configfile)
    assert os.path.exists(MDB_CONFIG_FILE)
    print('ok')

@cli.command(name='init')
def init():
    """
    Creates mdb_revisions tbl. Shuld be run once.
    """
    env = get_env()
    try:
        env.create_revisions_table() and print('rev tbl created')
    except Exception as e:
        print(e)
        raise SystemExit('init failed')
    print('Done')
    
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
            fw.write('-- identifiers used by mroll\n')
            header = "-- id={}\n-- description={}\n-- ts={}\n".format(id_, description, ts)
            fw.write(header)
            fw.write(template)
        assert os.path.exists(fn)
    print('ok')

@cli.command(name='history')
def history():
    """
    Shows applied revisions.
    """
    migr_ctx = MigrationContext.from_env(get_env())
    for r in migr_ctx.revisions:
        print(r)

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
    """
    Shows revisions not applied yet
    """
    config = Config.from_file(MDB_CONFIG_FILE)
    wd = WorkDirectory(config.work_dir)
    env = get_env()
    migr_ctx = MigrationContext.from_env(env)
    working_set = wd.revisions
    if migr_ctx.head is not None:
        def filter_fn(rev):
            return datetime.fromisoformat(rev.ts) > migr_ctx.head.ts
        working_set = list(filter(filter_fn, working_set))
    for r in working_set:
        print(r)

@cli.command(name="upgrade")
def upgrade():
    """
    Applies all revisions not yet applied in work dir.
    """
    config = Config.from_file(MDB_CONFIG_FILE)
    wd = WorkDirectory(config.work_dir)
    env = get_env()
    migr_ctx = MigrationContext.from_env(env)
    working_set = wd.revisions
    if migr_ctx.head is not None:
        print('adjusting working set ...')
        def filter_fn(rev):
            return datetime.fromisoformat(rev.ts) > migr_ctx.head.ts
        working_set = list(filter(filter_fn, working_set))
    for rev in working_set:
        try:
            env.add_revision(rev.id, rev.description, rev.ts, rev.upgrade_sql)
        except Exception as e:
            print(e)
            raise SystemExit('Upgrade failed at revision id={} description={}'.format(rev.id, rev.description))
    print('Done')

@cli.command(name="downgrade")
@click.option('-r', '--rev', 'rev_id', help="revision id")
def downgrade(rev_id):
    """
    Downgrades to the previous revison or to the revision with the id specified.
    """
    # TODO
    print("TODO: not yet implemented")

@cli.command(name='rollback')
def rollback():
    """
    Downgrades to the previous revision. It has same effect as downgrade without specified
    revision id. 
    """
    config = Config.from_file(MDB_CONFIG_FILE)
    wd = WorkDirectory(config.work_dir)
    env = get_env()
    migr_ctx = MigrationContext.from_env(env)
    if migr_ctx.head is None:
        print("Nothing to do!")
        return
    print('Rolling back id={} description={} ...'.format(migr_ctx.head.id, migr_ctx.head.description)) 
    downgrade_sql = ''
    for rev in wd.revisions:
        if rev.id == migr_ctx.head.id:
            downgrade_sql = rev.downgrade_sql
            break
    try:
        env.remove_revision(migr_ctx.head.id, downgrade_sql)
    except Exception as e:
        print(e)
        raise SystemExit('Rollback failed!')
    print('Done')


@cli.command(name='version')
def version():
    from . import __version__
    print(__version__)

if __name__ == '__main__':
    cli()