-- identifiers used by mroll
-- id=6c163e323a89
-- description=test revision 0
-- ts=2022-11-25T18:25:16.940894
-- migration:upgrade

create table test.revision0 (i int);
insert into test.revision0 values (1), (2);

-- migration:downgrade

drop table test.revision0;
