#!/usr/bin/env node
'use strict';

const path = require('path');
const readline = require('readline');

const root = process.env.JSQL_NEO_JS_ROOT;
const pkg = root ? require(path.join(root, 'index.js')) : require('jsql-neo');

let db = null;
let closed = false;

function replacer(key, value) {
  if (typeof value === 'bigint') {
    if (value <= Number.MAX_SAFE_INTEGER && value >= Number.MIN_SAFE_INTEGER) {
      return Number(value);
    }
    return value.toString();
  }
  return value;
}

function send(payload) {
  let line;
  try {
    line = JSON.stringify(payload, replacer);
  } catch (e) {
    line = JSON.stringify({
      id: payload && payload.id,
      ok: false,
      error: { message: 'Result is not JSON-serializable: ' + e.message }
    });
  }
  process.stdout.write(line + '\n');
}

async function init(args) {
  const dbPath = args[0];
  const options = args[1] || {};
  db = new pkg.Database(dbPath, options);
  if (typeof db.loadDatabase === 'function') {
    await db.loadDatabase();
  }
  return { path: dbPath };
}

async function dispatch(method, args) {
  if (!db) {
    throw new Error('Database is not initialized');
  }
  if (typeof method !== 'string' || method.startsWith('_') || method === 'constructor') {
    throw new Error('Invalid method: ' + String(method));
  }
  const fn = db[method];
  if (typeof fn !== 'function') {
    throw new Error('Unknown method: ' + method);
  }
  for (const arg of args) {
    if (typeof arg === 'function') {
      throw new Error('Function arguments are not supported over the bridge');
    }
  }
  return await fn.apply(db, args);
}

async function handle(msg) {
  const id = msg.id;
  const method = msg.method;
  const args = Array.isArray(msg.args) ? msg.args : [];

  if (method === 'close') {
    try {
      if (db && !closed) {
        closed = true;
        await db.close();
      }
    } catch (e) {
      // closing is best-effort; the process exits either way
    }
    send({ id: id, ok: true, result: null });
    setTimeout(() => process.exit(0), 0);
    return;
  }

  if (method === 'ping') {
    send({ id: id, ok: true, result: 'pong' });
    return;
  }

  try {
    const result = method === '__init' ? await init(args) : await dispatch(method, args);
    send({ id: id, ok: true, result: result === undefined ? null : result });
  } catch (e) {
    send({
      id: id,
      ok: false,
      error: {
        name: e && e.name ? e.name : 'Error',
        message: e && e.message ? e.message : String(e),
        code: e && e.code != null ? e.code : null
      }
    });
  }
}

const rl = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
let chain = Promise.resolve();

rl.on('line', line => {
  if (!line.trim()) return;
  chain = chain.then(() => {
    let msg;
    try {
      msg = JSON.parse(line);
    } catch (e) {
      send({ id: null, ok: false, error: { message: 'Invalid JSON request' } });
      return;
    }
    return handle(msg);
  });
});

rl.on('close', () => {
  process.exit(0);
});
