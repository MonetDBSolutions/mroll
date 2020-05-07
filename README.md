# MDB migration tool
Initial draft for db migration tool to be used with monetdb and pymonetdb.

# Usage
Project is setup with [Poetry](https://python-poetry.org/) dependency management tool.

```
$ poetry run mroll/commands.py --help
Usage: commands.py [OPTIONS] COMMAND1 [ARGS]... [COMMAND2 [ARGS]...]...

Options:
  --help  Show this message and exit.

Commands:
  all_revisions
  downgrade      Downgrades to the previous revison or to the revision with...
  history        Shows applied revisions.
  init           Creates mdb_revisions tbl.
  new_revisions  Shows revisions not applied yet
  revision       Creates new revision file from a template.
  rollback       Downgrades to the previous revision.
  setup          Set up work directory.
  show
  upgrade        Applies all revisions not yet applied in work dir.
```

## Usage example

Setup work directory. Use -p, --path command option to setup in specific location. Defaults to current working directory if no option provided. 
```
$ poetry run mroll/commands.py setup -p "/tmp/migrations"
ok
```
edit work directory configuration file to setup db connection options.
```
$ vi /tmp/migrations/mroll.ini 
```
create first revision with brief description 
```
$ poetry run mroll/commands.py revision -m "create table foo"
ok
$ poetry run mroll/commands.py show all_revisions
<Revision id=fe00de6bfa19 description=create table foo>
```
A new revison file was added under "/tmp/migrations/versions".Open and fill under "-- migration:upgrade" and "-- migration:downgrade" sections. Then run upgrade command.

```
$ poetry run mroll/commands.py upgrade

```

# Development

Install dependencies
```
poetry install
```
