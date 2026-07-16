// WHAT THIS FILE IS
// A small k6 load script for the T61 verification gate. It checks that the public
// app shell and health endpoint survive five concurrent users, and it can also
// exercise authenticated API paths when an AUTH_TOKEN is supplied.
//
// Usage:
//   k6 run -e BASE_URL=https://brink-xg7p.onrender.com load/k6-script.js
//   k6 run -e BASE_URL=http://127.0.0.1:3001 -e AUTH_TOKEN=... load/k6-script.js

import http from "k6/http";
import { check, sleep } from "k6";

const BASE_URL = (__ENV.BASE_URL || "http://127.0.0.1:3001").replace(/\/$/, "");
const AUTH_TOKEN = __ENV.AUTH_TOKEN || "";
const CRON_SECRET = __ENV.CRON_SECRET || "";

export const options = {
  vus: 5,
  duration: "1m",
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<1000"],
    checks: ["rate>0.99"],
  },
};

function authHeaders() {
  return AUTH_TOKEN ? { Authorization: `Bearer ${AUTH_TOKEN}` } : {};
}

export default function () {
  const home = http.get(`${BASE_URL}/`);
  check(home, {
    "home returns 200": (res) => res.status === 200,
  });

  const health = http.get(`${BASE_URL}/api/health`);
  check(health, {
    "health returns 200": (res) => res.status === 200,
    "health uses data envelope": (res) => {
      const body = res.json();
      return body && body.data && body.data.ok === true;
    },
  });

  if (AUTH_TOKEN) {
    const feed = http.get(`${BASE_URL}/api/feed`, { headers: authHeaders() });
    check(feed, {
      "feed auth path returns 200": (res) => res.status === 200,
      "feed uses data envelope": (res) => Boolean(res.json("data")),
    });

    const people = http.get(`${BASE_URL}/api/users/search?q=an`, { headers: authHeaders() });
    check(people, {
      "user search auth path returns 200": (res) => res.status === 200,
      "user search uses data envelope": (res) => Array.isArray(res.json("data")),
    });
  }

  if (CRON_SECRET) {
    const snapshot = http.post(`${BASE_URL}/api/snapshot`, null, {
      headers: { "X-Cron-Secret": CRON_SECRET },
      timeout: "30s",
    });
    check(snapshot, {
      "snapshot cron path does not auth-fail": (res) => res.status !== 401,
    });
  }

  sleep(1);
}
