import os
from configparser import ConfigParser
from datetime import datetime
from mroll.exceptions import InvalidWorkDirError
import sqlparse

def gen_rev_id():
    import uuid
    return uuid.uuid4().hex[-12:]

class Revision:
    def __init__(self, id_, description, ts, upgrade_sql=None, downgrade_sql=None):
        self.id = id_
        self.description = description
        self.ts = ts
        self.upgrade_sql = upgrade_sql
        self.downgrade_sql = downgrade_sql
        self.upgrade_stmts = sqlparse.split(upgrade_sql) if upgrade_sql else []
        self.downgrade_stmts = sqlparse.split(downgrade_sql) if downgrade_sql else []

    def __repr__(self):
        return "<Revision id={} description={}>".format(self.id, self.description)

    def serialize(self):
        from io import StringIO
        res=''
        with StringIO() as buf:
            buf.write('-- identifiers used by mroll\n')
            buf.write('-- id={}\n'.format(self.id))
            buf.write('-- description={}\n'.format(self.description))
            ts = self.ts.isoformat() if type(self.ts) == datetime else self.ts
            buf.write('-- ts={}\n'.format(ts))
            buf.write('-- migration:upgrade\n')
            buf.write('{}\n'.format(self.upgrade_sql or ''))
            buf.write('-- migration:downgrade\n')
            buf.write('{}\n'.format(self.downgrade_sql or ''))
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
            upgrade_sql = upgrade_sql.strip() or None
            upgrade_stmts = sqlparse.split(upgrade_sql) if upgrade_sql else []
            setattr(rev, 'upgrade_sql', upgrade_sql)
            setattr(rev, 'upgrade_stmts', upgrade_stmts)
            downgrade_sql = downgrade_sql.strip() or None
            downgrade_stmts = sqlparse.split(downgrade_sql) if downgrade_sql else []
            setattr(rev, 'downgrade_sql', downgrade_sql)
            setattr(rev, 'downgrade_stmts', downgrade_stmts)
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
        if not os.path.exists(path):
            raise RuntimeError("""Error: work directory doesn't exist. Run setup command first.""")
        if not os.listdir(path):
            raise RuntimeError("""Error: invalid work directory. Run setup command.""")
        self.path = path

    @property
    def config(self):
        configfile = os.path.join(self.path, 'mroll.ini')
        config = ConfigParser()
        config.read(configfile)
        return config

    def add_revision(self, rev: Revision):
        kebab = rev.description.strip().replace(' ', '_')
        fn = os.path.join(self.path, 'versions', '{}_{}.sql'.format(rev.id, kebab))
        with open(fn, 'w+') as fw:
            fw.write(rev.serialize())

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
    
    def config_validate(self):
        """
        Performs validation checks, e.g. mroll.ini is set and ready.
        """
        config = self.config
        sections = config.sections()
        for sec in sections:
            options = config.options(sec)
            for opt in options:
                try:
                    assert config.get(sec, opt)
                except AssertionError:
                    path = os.path.join(self.path, 'mroll.ini')
                    raise ValueError("Error: [{}][{}] not set in {}".format(sec, opt, path))

def get_all_upgrade_sql(work_dir=None):
    if work_dir is None:
        from .config import Config, MROLL_CONFIG_FILE
        config = Config.from_file(MROLL_CONFIG_FILE)
        work_dir = config.work_dir
    wd = WorkDirectory(work_dir)
    from io import StringIO
    res=''
    with StringIO() as buf:
        for rev in wd.revisions:
            buf.write(rev.upgrade_sql)
            buf.write('\n')
        res = buf.getvalue()
    return res.strip()
    
