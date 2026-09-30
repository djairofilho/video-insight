create table jobs (
    id uuid primary key,
    video_id uuid not null,
    operations varchar(100) not null,
    status varchar(20) not null,
    stage varchar(40),
    progress_percent integer not null,
    attempt integer not null,
    error_code varchar(100),
    error_message varchar(2000),
    error_retryable boolean,
    idempotency_key varchar(128) not null,
    storage_key varchar(1024) not null,
    created_at timestamp with time zone not null,
    updated_at timestamp with time zone not null,
    version bigint not null,
    constraint uk_jobs_idempotency_key unique (idempotency_key)
);

create index idx_jobs_video_id on jobs (video_id);

-- Histórico de tentativas: uma nova tentativa preserva a falha anterior (RN04).
create table job_attempts (
    id uuid primary key,
    job_id uuid not null references jobs (id),
    attempt integer not null,
    status varchar(20) not null,
    stage varchar(40),
    error_code varchar(100),
    error_message varchar(2000),
    error_retryable boolean,
    created_at timestamp with time zone not null,
    started_at timestamp with time zone,
    finished_at timestamp with time zone,
    constraint uk_job_attempts_job_attempt unique (job_id, attempt)
);

create table job_results (
    job_id uuid primary key references jobs (id),
    transcript text not null,
    summary text,
    chapters text,
    models text not null,
    transcript_json_key varchar(1024) not null,
    transcript_txt_key varchar(1024),
    transcript_srt_key varchar(1024),
    completed_at timestamp with time zone not null
);

-- Consumidor idempotente: cada evento recebido é aplicado uma única vez.
create table processed_events (
    event_id uuid primary key,
    event_type varchar(64) not null,
    processed_at timestamp with time zone not null
);

-- Outbox transacional: eventos gravados com o job e publicados depois.
create table outbox_events (
    id uuid primary key,
    routing_key varchar(128) not null,
    payload text not null,
    created_at timestamp with time zone not null,
    published_at timestamp with time zone
);

create index idx_outbox_events_pending on outbox_events (published_at, created_at);
