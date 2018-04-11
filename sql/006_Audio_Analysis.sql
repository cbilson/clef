alter table Track
add column acousticness float,
add column danceability float,
add column energy float,
add column instrumentalness float,
add column `key` int,
add column liveness float,
add column loudness float,
add column mode int,
add column speechiness float,
add column tempo float,
add column time_signature int,
add column valence float;

update SchemaVersion set version = 6, comment = 'Add Audio Analysis attributes to Track.';
