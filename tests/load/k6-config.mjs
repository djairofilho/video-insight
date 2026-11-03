/** Parâmetros sem credenciais ou endereços fixos; a execução recebe tudo do ambiente. */
export function integer(env, name, fallback, minimum, maximum) {
  const value = env[name] === undefined ? fallback : Number(env[name]);
  if (!Number.isInteger(value) || value < minimum || value > maximum) {
    throw new Error(`${name} deve estar entre ${minimum} e ${maximum}.`);
  }
  return value;
}

export function apiOptions(env) {
  const rate = integer(env, 'RATE', 1, 1, 1000);
  const duration = integer(env, 'DURATION_SECONDS', 60, 10, 600);
  const maximum = integer(env, 'MAX_VUS', 500, 1, 1000);
  return {
    scenarios: {
      queries: {
        executor: 'constant-arrival-rate', rate, timeUnit: '1s',
        duration: `${duration}s`, preAllocatedVUs: maximum,
        maxVUs: maximum, gracefulStop: '10s',
      },
    },
    systemTags: ['status', 'method', 'name', 'scenario', 'expected_response', 'error_code'],
    summaryTrendStats: ['avg', 'min', 'med', 'max', 'p(95)', 'p(99)'],
    thresholds: {
      http_req_failed: ['rate<0.01', { threshold: 'rate<0.05', abortOnFail: true, delayAbortEval: '15s' }],
      http_req_duration: ['p(95)<2000', { threshold: 'p(99)<8000', abortOnFail: true, delayAbortEval: '15s' }],
      dropped_iterations: ['count==0'],
      checks: ['rate>0.99'],
      data_received: [{ threshold: 'count<134217728', abortOnFail: true }],
    },
  };
}

export function summary(data, env) {
  const metrics = {};
  for (const [name, metric] of Object.entries(data.metrics)) {
    metrics[name] = { values: metric.values, thresholds: metric.thresholds || {} };
  }
  return JSON.stringify({
    target: env.TARGET_LABEL || 'configured-target', mode: env.MODE || 'mixed',
    requested_rate: Number(env.RATE || 0), requested_vus: Number(env.UPLOAD_VUS || 0),
    duration_seconds: Number(env.DURATION_SECONDS || 0), metrics,
    test_run_duration_ms: data.state?.testRunDurationMs,
    preallocated_vus: env.UPLOAD_VUS ? null : Number(env.MAX_VUS || 500),
  }) + '\n';
}

export function storageProxyUrl(base, signed) {
  if (!/^https?:\/\/[^/]+\/videos\//.test(signed)) {
    throw new Error('URL de upload fora do bucket de vídeos.');
  }
  return base.replace(/\/$/, '') + '/storage' + signed.replace(/^https?:\/\/[^/]+/, '');
}
