drop database if exists clef;
create database clef;

grant select, insert, delete, update on clef.* to '__DB_USER__'@localhost identified by '__DB_PASSWORD__';

flush privileges;

use clef;

drop table if exists User;
create table User(
       id char(100) primary key,
       name varchar(255),
       joined datetime,
       email varchar(255),
       average_dancability float,
       auth_code varchar(500),
       access_token varchar(255),
       token_expiration datetime,
       refresh_token varchar(255));

drop table if exists Profile;
create table Profile(
       user_id char(100) references User.id,
       date_created datetime);

drop table if exists Friend;
create table Friend(
       user_id char(100) references User.id,
       friend_id char(100) references User.id,
       added_at datetime,
       strength float);

drop table if exists PlaylistFollow;
create table PlaylistFollow(
       playlist_id char(30),
       user_id char(100) references User.id);

drop table if exists Playlist;
create table Playlist(
       id char(30),
       user_id char(100),
       name varchar(100),
       is_public boolean,
       created datetime,
       snapshot_id varchar(128));

drop table if exists Artist;
create table Artist (
       id char(30),
       name varchar(100),
       digital_id int,
       mbid varchar(100),
       mbtags varchar(100),
       mbtags_count int,
       playmeid int,
       familiarity float,
       hotttnesss float,
       location varchar(100),
       latitude float,
       longitude float);

drop table if exists ArtistTerm;
create table ArtistTerm (
       artist_id char(30),
       term varchar(30),
       frequency float,
       weight float);

drop table if exists MusicalRelease;
create table MusicalRelease(
       id_7digital int,
       name varchar(100));

drop table if exists Track;
create table Track(
       track_id char(30) primary key,
       name varchar(200),
       analysis_sample_rate float,
       audio_md5 char(32),
       -- bars_confidence float array,
       -- bars_start float array,
       -- beats_confidence float array,
       -- beats_start float array,
       danceability float,
       duration float,
       end_of_fade_in float,
       energy float,
       musical_key int,
       key_confidence float,
       loudness float,
       mode int,
       mode_confidence float,
       num_songs float,
       release_7digitalid int,
       -- these are all arrays too
       -- sections_confidence float,
       -- sections_start float,
       -- segments_confidence float,
       -- segments_loudness_max float,
       -- segments_loudness_max_time float,
       -- segments_loudness_start float,
       -- segments_pitches float,
       -- segments_start float,
       -- segments_timbre float,
       song_hotttnesss float,
       song_id varchar(100), -- echo nest song id
       start_of_fade_out float, -- time in seconds
       -- more arrays
       -- tatums_confidence float,
       -- tatums_start float,
       tempo float,
       time_signature int, -- beats per bar
       time_signature_confidence float,
       title varchar(100),
       track_7digitalid int,
       year int);

drop table if exists TrackSimillarArtist;
create table TrackSimillarArtist(
       track_id char(30) references Track.track_id,
       similar_artist_id char(30) references Artist.artist_id
       );

drop table if exists PlaylistTrack;
create table PlaylistTrack(
       playlist_id char(30) references Playlist.playlist_id,
       track_id char(30) references Track.track_id,
       added_at datetime,
       added_by char(100) references User.user_id);
