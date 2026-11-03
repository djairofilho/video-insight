import http from 'k6/http';
import { check, fail } from 'k6';
import exec from 'k6/execution';
import { Counter } from 'k6/metrics';
import { apiOptions, summary } from './k6-config.mjs';

export const options = apiOptions(__ENV);
const base = (__ENV.E2E_BASE_URL || '').replace(/\/$/, '');
const token = __ENV.E2E_ACCESS_TOKEN;
const fixture = JSON.parse(__ENV.E2E_LOAD_FIXTURE || '{}');
const counters = Object.fromEntries(['responses_2xx', 'responses_401', 'responses_429', 'responses_5xx', 'responses_network', 'responses_other'].map(name => [name, new Counter(name)]));
const params = name => ({ headers: { Authorization: `Bearer ${token}` }, timeout: '10s', tags: { name } });

export function setup() {
  if (!base || !token) fail('Defina E2E_BASE_URL e E2E_ACCESS_TOKEN.');
  const response = http.get(`${base}/api/v1/videos?limit=20`, params('preflight-list-videos'));
  if (response.status !== 200 || !Array.isArray(response.json('items'))) fail('Pré-verificação autenticada falhou.');
  if ((__ENV.MODE || 'mixed') === 'mixed' && (!fixture.video_id || !fixture.job_id)) fail('A carga mista requer vídeo e job de teste.');
}

export default function () {
  const choice = exec.scenario.iterationInTest % 10;
  let path = '/api/v1/videos?limit=20';
  let name = 'list-videos';
  if ((__ENV.MODE || 'mixed') === 'mixed') {
    if (choice >= 4 && choice < 6) { path = `/api/v1/videos/${fixture.video_id}`; name = 'get-video'; }
    else if (choice >= 6 && choice < 8) { path = `/api/v1/videos/${fixture.video_id}/jobs?limit=20`; name = 'list-jobs'; }
    else if (choice >= 8) { path = `/api/v1/jobs/${fixture.job_id}`; name = 'get-job'; }
  }
  const response = http.get(base + path, params(name));
  const status = response.status;
  const counter = status >= 200 && status < 300 ? 'responses_2xx' : status === 401 ? 'responses_401' : status === 429 ? 'responses_429' : status >= 500 ? 'responses_5xx' : status === 0 ? 'responses_network' : 'responses_other';
  counters[counter].add(1);
  check(response, { 'HTTP 200': r => r.status === 200, 'JSON': r => String(r.headers['Content-Type'] || '').includes('application/json') });
}

export function handleSummary(data) { return { stdout: summary(data, __ENV) }; }
