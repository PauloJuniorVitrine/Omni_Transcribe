import http from 'k6/http';
import { check, sleep } from 'k6';

const port = __ENV.K6_TARGET_PORT || '8000';
const target = `http://localhost:${port}/health`;

export const options = {
  vus: 5,
  duration: '1m',
  thresholds: {
    http_req_failed: ['rate<0.01'],
  },
};

export default function () {
  const res = http.get(target);
  check(res, {
    'status 200/206': (r) => r.status === 200 || r.status === 206,
  });
  sleep(1);
}
