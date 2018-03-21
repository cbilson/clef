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
       playlist_id char(30) references Playlist.id,
       user_id char(100) references User.id);

drop table if exists Playlist;
create table Playlist(
       id char(32) primary key,
       href varchar(255),
       owner char(100), -- references User.id,
       name varchar(100),
       public boolean,
       snapshot_id varchar(128),
       tracks_url varchar(255));

drop table if exists PlaylistImage;
create table PlaylistImage(
       playlist_id char(32) references Playlist.id,
       height int,
       width int,
       url varchar(255));

drop table if exists Artist;
create table Artist(
       id char(32) primary key,
       type varchar(20),
       name varchar(100),
       href varchar(255));

drop table if exists Album;
create table Album(
       id char(32) primary key,
       album_type varchar(20),
       href varchar(255),
       name varchar(255));

drop table if exists AlbumArtist;
create table AlbumArtist(
       album_id char(32) references Album.id,
       artist_id char(32) references Artist.id);

drop table if exists Track;
create table Track(
       id char(32) primary key,
       name varchar(255),
       type varchar(20),
       album_id char(32) references Album.id,
       disc_number int,
       duration_ms int,
       explicit boolean,
       href varchar(255),
       popularity int);

drop table if exists TrackArtist;
create table TrackArtist(
       track_id char(32) references Track.id,
       artist_id char(32) references Artist.id);

drop table if exists PlaylistTrack;
create table PlaylistTrack(
       playlist_id char(30) references Playlist.playlist_id,
       track_id char(30) references Track.track_id,
       added_at datetime,
       added_by char(100) references User.user_id);
