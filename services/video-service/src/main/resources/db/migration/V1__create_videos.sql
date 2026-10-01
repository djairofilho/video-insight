create table videos (
    id uuid primary key,
    file_name varchar(255) not null,
    content_type varchar(100) not null,
    size_bytes bigint not null,
    duration_seconds double precision,
    upload_status varchar(20) not null,
    created_at timestamp with time zone not null,
    updated_at timestamp with time zone not null,
    version bigint not null
);

-- Paginação por cursor: mais recentes primeiro, com o id desempatando.
create index idx_videos_created_at_id on videos (created_at desc, id desc);
