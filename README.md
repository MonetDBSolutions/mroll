# Mroll migration tool
Database migration tool around MonetDB and pymonetdb.

![mroll ci](https://github.com/MonetDBSolutions/mroll/workflows/ci_workflow/badge.svg)

## Usage

With MonetDB installed and running a project database, following commands can be used to set up migration 
process in your project.

```
$ mroll --help
Usage: commands.py [OPTIONS] COMMAND1 [ARGS]... [COMMAND2 [ARGS]...]...

Options:
  --help  Show this message and exit.

Commands:
  all_revisions
  downgrade      Downgrades to the previous revison or to the revision with...
  history        Shows applied revisions.
  init           Creates mroll_revisions tbl.
  new_revisions  Shows revisions not applied yet
  revision       Creates new revision file from a template.
  rollback       Downgrades to the previous revision.
  setup          Set up work directory.
  show
  upgrade        Applies all revisions not yet applied in work dir.
```

To set working directory use setup command.
```
mroll setup --help
```

, use  -p/--path option to specify location. For an example lets use "/tmp/migration" location.

```
$ mroll setup -p "/tmp/migrations"
ok
```

In the working directory modify mroll.ini with specific connection options

```
$ vi /tmp/migrations/mroll.ini 
```
, then run "init" command to create revisions table 

```
$ mroll init
```
create first revision with brief description 

```
$ mroll revision -m "create table foo"
ok
$ mroll show all_revisions
<Revision id=fe00de6bfa19 description=create table foo>
```
A new revison file was added under "/tmp/migrations/versions". Open and fill under "-- migration:upgrade" and "-- migration:downgrade" sections. 

```
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

To revert last applied revision run "rollback" command. That will run the sql under "migration:downgrade"
section.
```
$ mroll rollback 
Rolling back id=fe00de6bfa19 description=create tbl foo ...
Done
```

## Development
* Developer notes

~mroll~ is developed using [[https://python-poetry.org/][Poetry]], for dependency management and
packaging.

** Installation for development
In order to install ~mroll~ do the following:

#+begin_src shell
  pip3 install --user poetry
  PYTHON_BIN_PATH="$(python3 -m site --user-base)/bin"
  export PATH="$PATH:$PYTHON_BIN_PATH"

  git clone git@github.com:MonetDBSolutions/mroll.git
  cd mroll
  poetry install
  poetry run mroll --help
#+end_src

On 30/04/2020 [[https://github.com/gijzelaerr/pymonetdb/releases/tag/1.3.1][pymonetdb 1.3.1]] was released, which includes a feature needed to
connect transparently to the MonetDB server. If you have installed the
development version of ~mroll~, before that date you need to update:

#+BEGIN_SRC shell
  cd monetdb-pystethoscope
  git pull
  poetry update
#+END_SRC
```
curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python
```
, install project dependencies with

```
poetry install
```
, this will create virtual environment and install dependencies from poetry.lock file. Any of the above 
commands then can be run with poetry

```
poetry run mroll/commands.py <command>
```
## Testing
Run all unit tests
```
make test
```
