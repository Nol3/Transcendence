#!/usr/bin/env node

/**
 * Backend Performance Test Script
 * Measures API endpoint latencies and generates reports
 */

const http = require('http');
const https = require('https');

const ENDPOINTS = [
  { method: 'GET', path: '/api/leaderboard/', name: 'Leaderboard' },
  { method: 'POST', path: '/api/auth/login/', name: 'Login', body: { email: 'test@example.com', password: 'password123' } },
  { method: 'GET', path: '/api/users/', name: 'List Users' },
  { method: 'GET', path: '/api/games/', name: 'List Games' },
  { method: 'GET', path: '/api/tournament/', name: 'List Tournaments' },
];

const BASE_URL = process.env.BACKEND_URL || 'http://localhost:8000';
const NUM_REQUESTS = 50;

async function makeRequest(url, method = 'GET', body = null) {
  return new Promise((resolve, reject) => {
    const startTime = Date.now();
    const protocol = url.startsWith('https') ? https : http;
    const urlObj = new URL(url);

    const options = {
      hostname: urlObj.hostname,
      port: urlObj.port,
      path: urlObj.pathname + urlObj.search,
      method,
      headers: {
        'Content-Type': 'application/json',
      },
    };

    const req = protocol.request(options, (res) => {
      let data = '';

      res.on('data', chunk => { data += chunk; });
      res.on('end', () => {
        const duration = Date.now() - startTime;
        resolve({
          status: res.statusCode,
          duration,
          timestamp: new Date().toISOString(),
        });
      });
    });

    req.on('error', reject);
    if (body) req.write(JSON.stringify(body));
    req.end();
  });
}

async function testEndpoint(endpoint) {
  const { method, path, name, body } = endpoint;
  const url = `${BASE_URL}${path}`;
  const results = [];

  console.log(`\n📊 Testing: ${name} (${method} ${path})`);
  console.log('─'.repeat(60));

  for (let i = 0; i < NUM_REQUESTS; i++) {
    try {
      const result = await makeRequest(url, method, body);
      results.push(result.duration);
      process.stdout.write('.');
    } catch (err) {
      process.stdout.write('x');
    }
  }

  console.log('\n');

  if (results.length === 0) {
    console.log('❌ No successful responses');
    return null;
  }

  const sorted = [...results].sort((a, b) => a - b);
  const stats = {
    count: results.length,
    min: Math.min(...results),
    max: Math.max(...results),
    avg: Math.round(results.reduce((a, b) => a + b) / results.length),
    p50: sorted[Math.floor(sorted.length * 0.5)],
    p95: sorted[Math.floor(sorted.length * 0.95)],
    p99: sorted[Math.floor(sorted.length * 0.99)],
  };

  console.log(`  ✅ Success Rate: ${results.length}/${NUM_REQUESTS}`);
  console.log(`  ⏱️  Min: ${stats.min}ms | Max: ${stats.max}ms | Avg: ${stats.avg}ms`);
  console.log(`  📈 p50: ${stats.p50}ms | p95: ${stats.p95}ms | p99: ${stats.p99}ms`);

  // Performance targets
  const targets = {
    'Leaderboard': 100,
    'Login': 150,
    'List Users': 80,
    'List Games': 100,
    'List Tournaments': 100,
  };

  const target = targets[name] || 100;
  const status = stats.p95 <= target ? '✅' : '⚠️';
  console.log(`  ${status} Target p95: ${target}ms (actual: ${stats.p95}ms)`);

  return stats;
}

async function main() {
  console.log('🚀 Backend Performance Test');
  console.log(`🎯 Base URL: ${BASE_URL}`);
  console.log(`📋 Requests per endpoint: ${NUM_REQUESTS}`);
  console.log('═'.repeat(60));

  const results = {};

  for (const endpoint of ENDPOINTS) {
    const stats = await testEndpoint(endpoint);
    if (stats) {
      results[endpoint.name] = stats;
    }
    // Rate limiting: wait 500ms between endpoints
    await new Promise(r => setTimeout(r, 500));
  }

  console.log('\n📊 Summary Report');
  console.log('═'.repeat(60));

  const allP95 = Object.values(results).map(r => r.p95);
  const avgP95 = Math.round(allP95.reduce((a, b) => a + b) / allP95.length);

  console.log(`\n  📈 Average p95 latency: ${avgP95}ms`);
  console.log(`  🎯 Target: < 150ms`);
  console.log(`  ${avgP95 <= 150 ? '✅' : '⚠️'} Status: ${avgP95 <= 150 ? 'PASS' : 'WARN'}`);

  console.log('\n✨ Test complete!');
}

main().catch(console.error);
