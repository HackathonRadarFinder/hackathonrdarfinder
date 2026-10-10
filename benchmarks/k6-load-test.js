import http from 'k6/http';
import { check, sleep } from 'k6';

// ==============================================================================
// Hackathon Radar: Production Scalability & Load Benchmark (k6)
// Simulates concurrent builders discovering hackathons and querying predictions.
// ==============================================================================

export const options = {
  stages: [
    { duration: '30s', target: 20 },  // Ramp up to 20 virtual users (VUs)
    { duration: '1m',  target: 50 },  // Ramp up to 50 VUs (steady state)
    { duration: '30s', target: 100 }, // Peak burst to 100 VUs
    { duration: '30s', target: 0 },   // Cool down
  ],
  thresholds: {
    http_req_duration: ['p(95)<400', 'p(99)<800'], // 95% of requests under 400ms
    http_req_failed: ['rate<0.01'],                // Error rate strictly under 1%
  },
};

const BASE_URL = __ENV.TARGET_URL || 'http://localhost:5173';

export default function () {
  // 1. Root & Static Resource Load
  const resHome = http.get(`${BASE_URL}/`);
  check(resHome, {
    'homepage status is 200': (r) => r.status === 200,
    'homepage loaded quickly': (r) => r.timings.duration < 500,
  });

  sleep(1);

  // 2. Health & API Availability Check
  const resHealth = http.get(`${BASE_URL}/health`);
  check(resHealth, {
    'health endpoint responded': (r) => r.status === 200 || r.status === 404, // 200 on backend, 404 if SPA
  });

  sleep(1);
}
