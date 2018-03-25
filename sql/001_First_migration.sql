use clef;

create table SchemaVersion(version int, comment varchar(255));

insert into SchemaVersion(version, comment) values(1, 'added SchemaVersion');
