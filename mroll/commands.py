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


def load_module_py(module_id, path):
    spec = importlib.util.spec_from_file_location(module_id, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def get_templates_dir():
    dir_ = os.path.dirname(__file__)
    return os.path.join(dir_, 'templates')

def get_env():
    config = Config.from_file(MROLL_CONFIG_FILE)
    path = os.path.join(config.work_dir, 'env.py')
    env = load_module_py('env', path)
    return env

def gen_rev_id():
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
    env = get_env()
    try:
        env.get_head()
    except:
        raise SystemExit("Error: mroll not initialized! Run init command first.")

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
        raise ValueError("specified path {} is not valid mroll working directory!")
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
    env = get_env()
    try:
        # if following succeeds then mroll revisons tbl exist.
        env.get_head()
        return print("Nothing to do! Mroll revisions table already exist.")
    except:
        pass
    try:
        env.create_revisions_table()
    except Exception as e:
        raise SystemExit(e)
    print('{} table created'.format(env.tbl_name))
    print('Done')
    
@cli.command(name='revision')
@click.option('-m', '--message', help='gets added to revision name')
def revision(message):
    """
    Creates new revision from a template.
    """
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
def history():
    """
    Shows applied revisions.
    """
    ensure_init()
    return applied_revisions()
    
def all_revisions(show_patch=False):
    config = Config.from_file(MROLL_CONFIG_FILE)
    wd = WorkDirectory(config.work_dir)
    for rev in wd.revisions:
        if show_patch:
            print(rev.serialize())
        else:
            print(rev)

def applied_revisions(show_patch=False):
    config = Config.from_file(MROLL_CONFIG_FILE)
    wd = WorkDirectory(config.work_dir)
    env = get_env()
    migr_ctx = MigrationContext.from_env(env)
    if migr_ctx.head is None:
        return
    for rev in wd.revisions:
        if datetime.fromisoformat(rev.ts) <= migr_ctx.head.ts:
            if show_patch:
                print(rev.serialize())
            else:
                print(rev)

def pending_revisions(show_patch=False):
    """
    Shows pending revisions not yet applied.
    """
    config = Config.from_file(MROLL_CONFIG_FILE)
    wd = WorkDirectory(config.work_dir)
    env = get_env()
    migr_ctx = MigrationContext.from_env(env)
    working_set = wd.revisions
    if migr_ctx.head is not None:
        def filter_fn(rev):
            return datetime.fromisoformat(rev.ts) > migr_ctx.head.ts
        working_set = list(filter(filter_fn, working_set))
    for r in working_set:
        if show_patch:
            print(r.serialize())
        else:
            print(r)

@cli.command(name="show")
@click.argument('subcmd', nargs=1)
@click.argument('options', required=False)
def show(subcmd, options):
    """
    Shows revisions information.\n
    mroll show [ all | pending | applied ] [-p|--patch]
    """
    ensure_init()
    def usage(err_msg: str):
        res ="Error: {}\n".format(err_msg) if err_msg else ''
        res += 'Usage:\n'
        res+='mroll show [pending|applied|all] [-p|--patch]\n'
        return res
    show_patch = False
    if subcmd not in ['all', 'pending', 'applied']:
        raise SystemExit(usage("Invalid subcommand!"))
    if options:
        if options not in ['-p', '--p']:
            raise SystemExit(usage("Invalid subcommand option!"))
        show_patch = True 
    if subcmd == 'pending':
        return pending_revisions(show_patch=show_patch)
    if subcmd == 'applied':
        return applied_revisions(show_patch=show_patch)
    return all_revisions(show_patch=show_patch)

@cli.command(name="upgrade")
@click.option('-n', '--num', 'step', help="run n number of pending revisions")
def upgrade(step):
    """
    Applies revisions in work dir not yet applied.
    """ 
    ensure_init()
    config = Config.from_file(MROLL_CONFIG_FILE)
    wd = WorkDirectory(config.work_dir)
    env = get_env()
    migr_ctx = MigrationContext.from_env(env)
    # compute working set
    working_set = wd.revisions
    if migr_ctx.head is not None:
        def filter_fn(rev):
            return datetime.fromisoformat(rev.ts) > migr_ctx.head.ts
        working_set = list(filter(filter_fn, working_set))
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
        env.add_revisions(working_set)
    except RevisionOperationError as e:
        raise SystemExit(repr(e))
    print('Done')

@cli.command(name='rollback')
@click.option('-n', '--num', 'step', default=1, help="rollbacks n number applied revisions")
@click.option('-r', '--rev', 'rev_id', help="rollbacks to specific revision id inclusive")
def rollback(step, rev_id):
    """
    Downgrades to previous revision by default. 
    """
    ensure_init()
    config = Config.from_file(MROLL_CONFIG_FILE)
    wd = WorkDirectory(config.work_dir)
    env = get_env()
    migr_ctx = MigrationContext.from_env(env)
    if migr_ctx.head is None:
        raise SystemExit('Nothing to do!')
    working_set: List[Revision] = list(filter(lambda rev: datetime.fromisoformat(rev.ts) <= migr_ctx.head.ts, wd.revisions))
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
        env.remove_revisions(working_set)
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
