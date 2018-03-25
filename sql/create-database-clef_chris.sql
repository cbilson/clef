drop database if exists clef_chris;
create database clef_chris;

create user '__DB_USER__'@localhost identified by '__DB_PASSWORD__';

grant select, insert, delete, update on clef_chris.* to '__DB_USER__'@localhost;

flush privileges;
