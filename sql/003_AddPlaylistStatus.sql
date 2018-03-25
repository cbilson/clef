alter table Playlist add column status varchar(20);

update Playlist set status = 'loaded';

update SchemaVersion set version = 3, comment = 'Add playlist status.';
