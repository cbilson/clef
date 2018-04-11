create table SearchTerm (
        term varchar(50),
        entity_id varchar(32),
        entity_type varchar(32),
        primary key(term, entity_id, entity_type));

-- Add an entry for each artist
insert into  SearchTerm(term, entity_id, entity_type)
select       substr(name, 50), id, 'Artist' from Artist;

-- Add an entry for each artist genre to the artist (I don't think these will be that useful)
insert into  SearchTerm(term, entity_id, entity_type)
select       ag.genre, a.id, 'Artist'
from         Artist a
             inner join ArtistGenre ag on a.id = ag.artist_id;

-- Add an entry for each album name pointing to the album itself
insert into  SearchTerm(term, entity_id, entity_type)
select       a.name, a.id, 'Album'
from         Album a;

-- Add an entry for each album name pointing to the artist
insert ignore into
             SearchTerm(term, entity_id, entity_type)
select       substr(a.name, 50), ae.artist_id, 'Artist'
from         Album a
    inner join AlbumArtist ae on a.id = ae.album_id;

-- Add an entry for each track pointing to the album
insert ignore into
             SearchTerm(term, entity_id, entity_type)
select       substr(name, 50), album_id, 'Album'
from         Track;

-- Add an entry for each track pointing to the artist
insert ignore into
             SearchTerm(term, entity_id, entity_type)
select       substr(t.name, 50), ta.artist_id, 'Artist'
from         Track t
    inner join TrackArtist ta on t.id = ta.track_id;

-- Could do a lot more here.

-- TODO: Trigger

create view SearchEntity as
select id, 'Artist' as type, name from Artist
union
select id, 'Album' as type, name from Artist
union
select id, 'Track' as type, name from Track;

update SchemaVersion set version = 5, comment = 'Add search table.';
