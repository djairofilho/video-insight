import http from 'k6/http';
import { check, fail } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';
import { integer, storageProxyUrl, summary } from './k6-config.mjs';

const base = (__ENV.E2E_BASE_URL || '').replace(/\/$/, '');
const token = __ENV.E2E_ACCESS_TOKEN;
const run = __ENV.LOAD_RUN_ID || '';
if (!/^loadtest-[a-z0-9-]{6,60}$/.test(run)) throw new Error('LOAD_RUN_ID inválido.');
if (!__ENV.VIDEO_FILE) throw new Error('Defina VIDEO_FILE com o MP4 de teste.');
const content = open(__ENV.VIDEO_FILE, 'b');
if (content.byteLength > 104857600) throw new Error('O arquivo excede 100 MiB.');
const vus = integer(__ENV, 'UPLOAD_VUS', 1, 1, 16);
const iterations = integer(__ENV, 'UPLOAD_ITERATIONS', vus, 1, 32);
const completed = new Counter('completed_uploads');
const failures = new Rate('upload_failures');
const latency = new Trend('upload_transaction_ms', true);
export const options = {
  scenarios: { uploads: { executor: 'shared-iterations', vus, iterations, maxDuration: '8m', gracefulStop: '15s' } },
  systemTags: ['status', 'method', 'name', 'scenario', 'expected_response', 'error_code'],
  summaryTrendStats: ['avg', 'min', 'med', 'max', 'p(95)', 'p(99)'],
  thresholds: { upload_failures: ['rate==0'], checks: ['rate==1'] },
};
const params = name => ({ headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }, timeout: '30s', tags: { name } });
function requireStatus(response, status) {
  if (!check(response, { 'status esperado': r => r.status === status })) fail('Etapa do upload falhou.');
  return response;
}
export function setup() {
  if (!base || !token) fail('Defina E2E_BASE_URL e E2E_ACCESS_TOKEN.');
  requireStatus(http.get(`${base}/api/v1/videos?limit=1`, params('upload-preflight')), 200);
}
export default function () {
  let id; let ok = false; const started = Date.now();
  try {
    const created = requireStatus(http.post(`${base}/api/v1/videos`, JSON.stringify({ file_name: `${run}-${__VU}-${__ITER}.mp4`, content_type: 'video/mp4', size_bytes: content.byteLength }), params('create-upload-video')), 201);
    id = created.json('id');
    const signed = requireStatus(http.post(`${base}/api/v1/videos/${id}/upload-url`, null, params('sign-upload')), 200).json();
    requireStatus(http.put(storageProxyUrl(base, signed.url), content, { headers: signed.headers || {}, timeout: '180s', tags: { name: 'put-video-content' } }), 200);
    const ready = requireStatus(http.post(`${base}/api/v1/videos/${id}/upload-complete`, JSON.stringify({ duration_seconds: 2 }), params('confirm-upload')), 200);
    ok = check(ready, { 'vídeo pronto': r => r.json('upload_status') === 'ready' || r.json('uploadStatus') === 'ready' });
    if (ok) completed.add(1);
  } finally {
    latency.add(Date.now() - started); failures.add(!ok);
    if (id) {
      const deleted = http.del(`${base}/api/v1/videos/${id}`, null, params('delete-upload-fixture'));
      check(deleted, { 'fixture removida': r => r.status === 204 || r.status === 200 });
    }
  }
}
export function handleSummary(data) { return { stdout: summary(data, __ENV) }; }
