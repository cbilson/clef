-- Create the default database
drop database if exists clef;
create database clef;

grant select, insert, delete, update on clef.* to '__DB_USER__'@localhost identified by '__DB_PASSWORD__';

flush privileges;
