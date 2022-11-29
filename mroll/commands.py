#!/usr/bin/env python3

import click
import os
import shutil
import configparser 
from datetime import datetime
import importlib.util
import importlib.machinery
from mroll.config import *
from mroll.migration import Revision, MigrationContext, WorkDirectory
from mroll.exceptions import RevisionOperationError
from mroll.databases import create_migration_ctx

def get_templates_dir():
    dir_ = os.path.dirname(__file__)
    return os.path.join(dir_, 'templates')

def gen_rev_id():
    """
    rev id generator
    """
    import uuid
    return uuid.uuid4().hex[-12:]

def ensure_setup():
    try:
        config = Config.from_file(MROLL_CONFIG_FILE)
        wd = WorkDirectory(config.work_dir)
        wd.config_validate()
    except RuntimeError as e:
        raise SystemExit(e)
    except ValueError as e:
        raise SystemExit(e)

def ensure_init():
    ensure_setup()
    config = Config.from_file(MROLL_CONFIG_FILE)
    wd = WorkDirectory(config.work_dir)
    try:
        ctx = create_migration_ctx(wd.get_migration_ctx_config())
        head = ctx.head
    except:
        raise SystemExit("Error: mroll not initialized! Run init command first.")

# ----------------------------------

@click.group()
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
        raise SystemExit("Error: Directory %s already exists and it is not empty" % directory)
    versions = os.path.join(directory, 'versions')
    os.mkdir(directory)
    os.mkdir(versions)
    tmpl_dir = get_templates_dir()
    shutil.copy(os.path.join(tmpl_dir, 'mroll.ini'), directory)
    #  setup config file
    if not os.path.exists(SYS_CONFIG):
        os.mkdir(SYS_CONFIG)
    if not os.path.exists(MROLL_CONFIG_DIR):
        os.mkdir(MROLL_CONFIG_DIR)
    config = configparser.ConfigParser()
    config['mroll'] = dict(work_dir=directory)
    with open(MROLL_CONFIG_FILE, 'w') as configfile:
        config.write(configfile)
    assert os.path.exists(MROLL_CONFIG_FILE)
    print('ok')

@cli.command(name='config')
@click.option('-p', '--path', help='path to work directory')
def config(path):
    """
    Set up mroll configuration under $HOME/.config/mroll
    """
    directory = path or os.path.join(os.getcwd(), 'migrations')
    dir_list = os.listdir(directory)
    check = ('mroll.ini' in dir_list) and ('versions' in dir_list)
    if not check:
        raise SystemExit("Error: specified path '{}' is not a valid mroll working directory!".format(path))
    #  setup config file
    if not os.path.exists(SYS_CONFIG):
        os.mkdir(SYS_CONFIG)
    if not os.path.exists(MROLL_CONFIG_DIR):
        os.mkdir(MROLL_CONFIG_DIR)
    config = configparser.ConfigParser()
    config['mroll'] = dict(work_dir=directory)
    with open(MROLL_CONFIG_FILE, 'w') as configfile:
        config.write(configfile)
    assert os.path.exists(MROLL_CONFIG_FILE)
    print('ok')

@cli.command(name='init')
def init():
    """
    Creates mroll_revisions tbl. Should be run once.
    """
    ensure_setup()
    config = Config.from_file(MROLL_CONFIG_FILE)
    wd = WorkDirectory(config.work_dir)
    migr_ctx_config = wd.get_migration_ctx_config()
    migr_ctx = create_migration_ctx(migr_ctx_config)
    try:
        # if following succeeds then mroll revisons tbl exist.
        migr_ctx.head
        return print("Nothing to do! Mroll revisions table already exist.")
    except:
        pass
    try:
        migr_ctx.create_revisions_tbl()
    except Exception as e:
        raise SystemExit(e)
    print('{} table created'.format(migr_ctx_config.tbl_name))
    print('Done')
    
@cli.command(name='revision')
@click.option('-m', '--message', help='gets added to revision name')
@click.option('-d', '--dir', 'mdir', help="the migrations directory")
def revision(message, mdir):
    """
    Creates new revision from a template.
    """
    if mdir:
        wd = WorkDirectory(mdir)
    else:
        ensure_setup()
        config = Config.from_file(MROLL_CONFIG_FILE)
        wd = WorkDirectory(config.work_dir)
    ts = datetime.now().isoformat()
    id_ = gen_rev_id()
    description = message or ''
    wd.add_revision(Revision(id_, description, ts))
    kebab = description.strip().replace(' ', '_')
    fn = os.path.join(wd.path, 'versions', '{}_{}.sql'.format(id_, kebab))
    assert os.path.exists(fn)
    print('ok')

@cli.command(name='history')
@click.option('-d', '--dir', 'mdir', help="the migrations directory")
def history(mdir):
    """
    Shows applied revisions.
    """
    if not mdir:
        ensure_init()
    return applied_revisions(mdir=mdir)
    
def all_revisions(show_patch=False, mdir=None):
    if mdir:
        wd = WorkDirectory(mdir)
    else:
        config = Config.from_file(MROLL_CONFIG_FILE)
        wd = WorkDirectory(config.work_dir)

    for rev in wd.revisions:
        if show_patch:
            print(rev.serialize())
        else:
            print(rev)

def applied_revisions(show_patch=False, mdir=None):
    if mdir:
        wd = WorkDirectory(mdir)
    else:
        config = Config.from_file(MROLL_CONFIG_FILE)
        wd = WorkDirectory(config.work_dir)

    migr_ctx = create_migration_ctx(wd.get_migration_ctx_config())
    if migr_ctx.head is None:
        print('No revisions have being applied yet!')
        return
    # create lookup
    lookup = {}
    for r in migr_ctx.revisions:
        lookup[r.id] = r

    working_set: List[Revision] = list(filter(lambda rev: rev.id in lookup, wd.revisions))
    for rev in working_set:
        if show_patch:
            print(rev.serialize())
        else:
            print(rev)

def pending_revisions(show_patch=False, mdir=None):
    """
    Shows pending revisions not yet applied.
    """
    if mdir:
        wd = WorkDirectory(mdir)
    else:
        config = Config.from_file(MROLL_CONFIG_FILE)
        wd = WorkDirectory(config.work_dir)
    migr_ctx = create_migration_ctx(wd.get_migration_ctx_config())
    # create lookup
    lookup = {}
    for r in migr_ctx.revisions:
        lookup[r.id] = r

    working_set: List[Revision] = list(filter(lambda rev: rev.id not in lookup, wd.revisions))
    for r in working_set:
        if show_patch:
            print(r.serialize())
        else:
            print(r)

@cli.group(name="show")
def show():
    pass

@show.command(name="all")
@click.option('-p', '--patch', is_flag=True)
@click.option('-d', '--dir', 'mdir', help="the migrations directory")
def all(patch, mdir):
    if not mdir:
        ensure_init()

    return all_revisions(show_patch=patch, mdir=mdir)

@show.command(name="pending")
@click.option('-p', '--patch', is_flag=True)
@click.option('-d', '--dir', 'mdir', help="the migrations directory")
def pending(patch, mdir):
    if not mdir:
        ensure_init()

    return pending_revisions(show_patch=patch, mdir=mdir)

@show.command(name="applied")
@click.option('-p', '--patch', is_flag=True)
@click.option('-d', '--dir', 'mdir', help="the migrations directory")
def applied(patch, mdir):
    if not mdir:
        ensure_init()

    return applied_revisions(show_patch=patch, mdir=mdir)

@cli.command(name="upgrade")
@click.option('-n', '--num', 'step', help="run n number of pending revisions")
@click.option('-d', '--dir', 'mdir', help="the migrations directory")
def upgrade(step, mdir):
    """
    Applies revisions in work dir not yet applied.
    """
    if mdir:
        wd = WorkDirectory(mdir)
    else:
        ensure_init()
        config = Config.from_file(MROLL_CONFIG_FILE)
        wd = WorkDirectory(config.work_dir)
    migr_ctx = create_migration_ctx(wd.get_migration_ctx_config())
    # create lookup
    lookup = {}
    for r in migr_ctx.revisions:
        lookup[r.id] = r
    working_set: List[Revision] = list(filter(lambda rev: lookup.get(rev.id, None) is None, wd.revisions))
    ptr = step or len(working_set)
    # adjust working set
    working_set = working_set[:ptr]
    # ensure idempotency
    for rev in working_set:
        if rev.upgrade_sql is None:
            msg="""
            Error: No upgrade sql script @{}!
            """.format(rev.id)
            if rev.downgrade_sql is not None:
                msg="""
                Error: No upgrade sql script @{}, while there is a
                downgrade sql:
                {}
                Scripts should be idempotent.
                """.format(rev.id, rev.downgrade_sql)
            raise SystemExit(msg)
    # execute
    try:
        migr_ctx.add_revisions(working_set)
    except RevisionOperationError as e:
        raise SystemExit(repr(e))
    print('Done')

@cli.command(name='rollback')
@click.option('-n', '--num', 'step', default=1, help="rollbacks n number applied revisions")
@click.option('-r', '--rev', 'rev_id', help="rollbacks to specific revision id inclusive")
@click.option('-d', '--dir', 'mdir', help="the migrations directory")
def rollback(step, rev_id, mdir):
    """
    Downgrades to previous revision by default. 
    """
    if mdir:
        wd = WorkDirectory(mdir)
    else:
        ensure_init()
        config = Config.from_file(MROLL_CONFIG_FILE)
        wd = WorkDirectory(config.work_dir)
    migr_ctx = create_migration_ctx(wd.get_migration_ctx_config())
    if migr_ctx.head is None:
        raise SystemExit('Nothing to do!')
    # create lookup
    lookup = {}
    for r in migr_ctx.revisions:
        lookup[r.id] = r
    working_set: List[Revision] = list(filter(lambda rev: lookup.get(rev.id, None) is not None, wd.revisions))
    count = 0
    buff=[]
    for rev in reversed(working_set):
        if rev_id is None and count==step:
            break
        if rev_id is not None:
            if rev.id == rev_id:
                buff.append(rev)
                break
        buff.append(rev)
        count+=1
    working_set: List[Revision] = [] + buff
     # insure idempotency
    for rev in working_set:
        if rev.downgrade_sql is None:
            msg="""
                Error: No downgrade sql script @{}!
                """.format(rev.id)
            if rev.upgrade_sql is not None:
                msg="""
                Error: No downgrade sql script @{}, while there is a
                upgrade sql:
                {}
                Scripts should be idempotent.
                """.format(rev.id, rev.upgrade_sql)
            raise SystemExit(msg)
    try:
        migr_ctx.remove_revisions(working_set)
    except RevisionOperationError as e:
        raise SystemExit(repr(e))
    print('Done')

@cli.command(name='version')
def version():
    """
    Shows current version
    """
    from . import __version__
    print(__version__)

if __name__ == '__main__':
    cli()
