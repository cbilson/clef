alter table User add column status varchar(20);

update User set status = 'new';

update SchemaVersion set version = 2, comment = 'Add user status.';
