alter table videos add column owner_id varchar(255) not null default 'local-development';
create index idx_videos_owner_created on videos (owner_id, created_at desc, id desc);
