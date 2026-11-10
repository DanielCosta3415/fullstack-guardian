'use strict';
const assert = require('node:assert/strict');
const variant = process.argv[2];
const allowed = ['baseline', 'absent-null', 'enum-strict', 'form-loss', 'form-navigation'];
if (!allowed.includes(variant)) throw new Error('Unknown reviewed variant');
const checks = [];
function check(id, fn) {
  try { fn(); checks.push({id, status: 'PASSED'}); }
  catch (error) {
    if (!(error instanceof assert.AssertionError)) throw error;
    checks.push({id, status: 'FAILED'});
  }
}
function encode(value) {
  if (variant === 'absent-null') return JSON.stringify(value, (_, v) => v === null ? undefined : v);
  return JSON.stringify(value);
}
check('absence_null_distinct', () => {
  assert.deepEqual(JSON.parse(encode({id: 1, note: undefined})), {id: 1});
  assert.deepEqual(JSON.parse(encode({id: 1, note: null})), {id: 1, note: null});
});
function consume(value, tolerant) {
  if (typeof value !== 'string') throw new TypeError('enum must be a string');
  if (['open', 'closed'].includes(value)) return {kind: 'known', value};
  if (tolerant || variant === 'enum-strict') return {kind: 'unknown', value};
  throw new RangeError('unsupported enum');
}
check('strict_enum_rejects_unknown', () => assert.throws(() => consume('future', false), RangeError));
check('tolerant_enum_preserves_unknown', () => {
  assert.deepEqual(consume('future', true), {kind: 'unknown', value: 'future'});
  assert.throws(() => consume(7, true), TypeError);
});
function navigate(state, target) {
  if (target === 'confirm' && !state.valid && variant !== 'form-navigation') return {...state, error: 'invalid'};
  return {...state, step: target, draft: variant === 'form-loss' ? '' : state.draft};
}
check('invalid_form_blocks_navigation', () => {
  const state = {step: 'edit', draft: 'typed data', valid: false};
  const next = navigate(state, 'confirm');
  assert.equal(next.step, 'edit');
});
check('navigation_preserves_input', () => {
  const state = {step: 'edit', draft: 'typed data', valid: true};
  const next = navigate(navigate(state, 'confirm'), 'edit');
  assert.equal(next.draft, 'typed data');
  assert.equal(state.draft, 'typed data');
});
console.log(JSON.stringify({stack: 'node', variant, checks}));
process.exitCode = checks.some(c => c.status === 'FAILED') ? 1 : 0;
