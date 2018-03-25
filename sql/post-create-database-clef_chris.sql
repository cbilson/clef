-- seed with some data from the other database
insert into clef_chris.User(id,name,joined,email,auth_code,access_token,token_expiration,refresh_token)
select id,name,joined,email,auth_code,access_token,token_expiration,refresh_token from clef.User
where clef.User.id = 'cbilson';
