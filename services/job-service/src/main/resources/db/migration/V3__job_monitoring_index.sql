-- O estado e o horário atendem a fila e a janela de conclusões sem percorrer todos os jobs.
create index idx_jobs_status_updated_at on jobs (status, updated_at);
