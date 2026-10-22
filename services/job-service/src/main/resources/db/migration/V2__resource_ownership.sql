alter table jobs add column owner_id varchar(255) not null default 'local-development';
alter table jobs drop constraint uk_jobs_idempotency_key;
alter table jobs add constraint uk_jobs_owner_idempotency unique (owner_id, idempotency_key);
