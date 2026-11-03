# Testes de carga

`run_load.py` mede consultas autenticadas sem criar jobs ou consumir cota de IA.
Use um access token de teste na variável `E2E_ACCESS_TOKEN`, nunca em argumentos.

```bash
python -m pip install -r tests/end-to-end/requirements.txt
python tests/load/run_load.py https://video-insight-ruby.vercel.app/api/v1/videos --requests 50 --workers 5
```

O relatório JSON inclui códigos HTTP, erros, p50, p95, máximo e requisições por
segundo. Respostas 401/403 contam como falhas, não como sucesso de carga.
Os limites são 1.000 requisições e 20 clientes; aumentos exigem outro experimento.
Este teste não mede a capacidade máxima de processamento dos provedores de IA.
