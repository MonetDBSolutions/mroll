![mroll ci](https://github.com/MonetDBSolutions/mroll/workflows/ci_workflow/badge.svg)

# Mroll migration tool
`mroll` has been designed to aid MonetDB users with managing database migrations.
The functionality covers both roll forward and backward migration functionality.
Although you can deploy `mroll` from any point in time onwards, it is advised to use it
from day one, i.e. the creation of the database.
`mroll` has been used internally to manage the continuous integration workflow of MonetDB.

## Install

Install mroll from PyPi

```
$ pip install mroll
```

## Synopsis
The command synopsis summarizes the functionality.

```
$ mroll --help
Usage: commands.py [OPTIONS] COMMAND1 [ARGS]... [COMMAND2 [ARGS]...]...

Options:
  --help  Show this message and exit.

Commands:
  config    Set up mroll configuration under $HOME/.config/mroll
  history   Shows applied revisions.
  init      Creates mroll_revisions tbl.
  revision  Creates new revision from a template.
  rollback  Downgrades to previous revision by default.
  setup     Set up work directory.
  show      Shows revisions information.
  upgrade   Applies all revisions not yet applied in work dir.
  version   Shows current version
```

Each command may come with some options, explained by the `--help` addition.
For example, the location of the migration directory can be specified when you install mroll
with an option `--path` option to specify location. For an example, `--path "/tmp/migration"` location.

To update/set `mroll` configuration use the `config` command.
For example to update configuration setting for working directory path run.
```
mroll config -p <workdir_path>
```

## Usage
To illustrate the functionality we walk you through the steps to get a MonetDB database, called
*demo*, created and managed. We assume you have downloaded `mroll` (see below) and are all set to give it a try.

#### Setup 
`mroll` needs a working directory for each database you want to manage. There is no restriction on
its location, but you could keep the migration scripts in your application 
folder, e.g. `.../app/migrations`. From the `.../app` directory issue the command:

```
$ mroll setup
ok
```
A subdirectory `migrations` is being created to manage migrations versions.

#### Configuration
`mroll` needs information on the database whereabouts and credentials to initiate the migration steps.
Make sure you have already created and released the demo database using the `monetdb` tools.
Then complete the file `migrations/mroll.ini` to something like:
```
[db]
db_name=demo
user=monetdb
password=monetdb
port=50000

[mroll]
rev_history_tbl_name = mroll_revisions
```
The final step for managing the migrations is
```
$ mroll init
```
#### Define the first revision
The empty database will be populated with a database schema.
For this we define a revision. Revision names are generated

```
$ mroll revision -m "Initialize the database"
ok
$ mroll show all_revisions
<Revision id=fe00de6bfa19 description=Initialize the database>
```
A new revison file was added under `/tmp/migrations/versions`. 
Open it and add the SQL commands under `-- migration:upgrade` and `-- migration:downgrade` sections.

```
vi tmp/migrations/versions/<rev_file>
-- identifiers used by mroll
-- id=fe00de6bfa19
-- description=create tbl foo
-- ts=2020-05-08T14:19:46.839773
-- migration:upgrade
	create table foo (a string, b string);
	alter table foo add constraint foo_pk primary key (a);
-- migration:downgrade
	drop table foo;
```
Then run "upgrade" command.

```
$ mroll upgrade
Done
```

Inspect what has being applied with "history" command
```
$ mroll history
<Revision id=fe00de6bfa19 description=create tbl foo>
```
For revisions overview use `mroll show [all|pending|applied]`, `mroll applied` is equivalent to 
`mroll history`.
```
$mroll show applied
<Revision id=fe00de6bfa19 description=create tbl foo>
```

To revert last applied revision run the `rollback` command. That will run the sql under `migration:downgrade`
section.
```
$ mroll rollback 
Rolling back id=fe00de6bfa19 description=create tbl foo ...
Done
```

## Development
### Developer notes

`mroll` is developed using [Poetry](https://python-poetry.org/), for dependency management and
packaging.

### Installation for development
In order to install `mroll` do the following:

```
  pip3 install --user poetry
  PYTHON_BIN_PATH="$(python3 -m site --user-base)/bin"
  export PATH="$PATH:$PYTHON_BIN_PATH"

  git clone git@github.com:MonetDBSolutions/mroll.git
  cd mroll
  poetry install
  poetry run mroll/commands.py --help
```
Install project dependencies with

```
poetry install
```
This will create virtual environment and install dependencies from the `poetry.lock` file. Any of the above 
commands then can be run with poetry

```
poetry run mroll/commands.py <command>
```
## Testing
Run all unit tests
```
make test
```
