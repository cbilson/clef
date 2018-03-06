drop database if exists clef_app;

create database clef;

grant usage on clef to clefapp@localhost identified by 'temppasword';

grant select, insert, delete, update on clef.* to clefapp@localhost;

flush privileges;

use clef;

create table User(
       id char(100) primary key,
       name varchar(255),
       average_dancability);

create table Profile(
       user_id char(100) references User.id,
       date_created timestamp);

