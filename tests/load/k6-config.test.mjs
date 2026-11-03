import test from 'node:test';
import assert from 'node:assert/strict';
import { apiOptions, storageProxyUrl, summary } from './k6-config.mjs';

test('carga aberta tem taxa independente de latência e limites de recursos', () => {
  const options = apiOptions({ RATE: '160', DURATION_SECONDS: '60', MAX_VUS: '200' });
  assert.equal(options.scenarios.queries.executor, 'constant-arrival-rate');
  assert.equal(options.scenarios.queries.rate, 160);
  assert.equal(options.scenarios.queries.maxVUs, 200);
  assert.equal(options.scenarios.queries.preAllocatedVUs, 200);
  assert.ok(!options.systemTags.includes('url'));
  assert.deepEqual(options.thresholds.dropped_iterations, ['count==0']);
  assert.ok(options.thresholds.http_req_failed.some(t => t.abortOnFail));
});
test('parâmetros fora dos limites não iniciam carga', () => {
  for (const env of [{ RATE: '1001' }, { RATE: 'NaN' }, { MAX_VUS: '1001' }, { DURATION_SECONDS: '0' }]) assert.throws(() => apiOptions(env));
});
test('proxy preserva assinatura sem enviar o bearer ao storage', () => {
  const url = storageProxyUrl('https://app.example', 'http://storage.example/videos/object.mp4?X-Amz-Signature=synthetic');
  assert.equal(url, 'https://app.example/storage/videos/object.mp4?X-Amz-Signature=synthetic');
  assert.throws(() => storageProxyUrl('https://app.example', 'https://other.example/private/data'));
});
test('resumo não inclui ambiente com token ou endereço do alvo', () => {
  const value = summary({ metrics: { http_reqs: { values: { count: 12 } } } }, { RATE: '5', E2E_ACCESS_TOKEN: 'synthetic-secret', E2E_BASE_URL: 'https://private.example' });
  assert.equal(JSON.parse(value).metrics.http_reqs.values.count, 12);
  assert.ok(!value.includes('synthetic-secret') && !value.includes('private.example'));
});
