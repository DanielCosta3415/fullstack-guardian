'use strict';
const variant = new URL(location.href).searchParams.get('variant');
const byId = id => document.getElementById(id);
let composing = false;
let actions = 0;
let generation = 0;
let complete;
const focusLog = [];
document.addEventListener('focusin', event => focusLog.push(event.target.id));
byId('draft').addEventListener('compositionstart', () => { composing = true; });
byId('draft').addEventListener('compositionend', () => { composing = false; });
byId('draft').addEventListener('keydown', event => {
  if (event.key !== 'Enter') return;
  event.preventDefault();
  if (!composing || variant === 'composition-unchecked') byId('form').requestSubmit();
  if (variant === 'double-submit' && !composing) byId('form').requestSubmit();
});
byId('form').addEventListener('submit', event => {
  event.preventDefault();
  actions += 1;
  byId('status').textContent = 'pending';
});
byId('open').addEventListener('click', () => {
  byId('dialog').hidden = false;
  byId('close').focus();
});
byId('dialog').addEventListener('keydown', event => {
  if (event.key === 'Tab' && variant !== 'focus-leak') {
    const atFirst = document.activeElement === byId('close');
    const atLast = document.activeElement === byId('dialogField');
    if (event.shiftKey && atFirst) { event.preventDefault(); byId('dialogField').focus(); }
    if (!event.shiftKey && atLast) { event.preventDefault(); byId('close').focus(); }
  }
  if (event.key === 'Escape') {
    event.preventDefault();
    byId('dialog').hidden = true;
    if (variant !== 'restore-lost') (byId('open') || byId('heading')).focus();
  }
});
byId('close').addEventListener('click', () => {
  byId('dialog').dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true}));
});
const cache = new Map();
window.fixture = {
  get actions() { return actions; }, get focusLog() { return focusLog; },
  fail() {
    byId('error').textContent = 'Please retry; draft retained';
    byId('draft').setAttribute('aria-invalid', 'true');
    if (variant === 'error-clears') byId('draft').value = '';
    if (variant === 'error-unassociated') byId('draft').removeAttribute('aria-describedby');
    byId('draft').focus();
  },
  pending() {
    const started = generation;
    new Promise(resolve => { complete = resolve; }).then(value => {
      if (started === generation || variant === 'stale-applies') byId('status').textContent = value;
    });
  },
  navigate() { generation += 1; byId('status').textContent = 'new-screen'; },
  finishOld() { complete('old-screen-success'); },
  render(tenant, locale, count) {
    const key = variant === 'cache-unscoped' ? 'page' : JSON.stringify([tenant, locale, count]);
    if (!cache.has(key)) {
      const plural = new Intl.PluralRules(locale).select(count);
      const text = locale === 'ar' ? (plural === 'two' && variant !== 'plural-wrong' ? 'عنصران' : 'عناصر') : (count === 1 ? 'item' : 'items');
      cache.set(key, {tenant, locale, text, count, date: new Intl.DateTimeFormat(locale, {timeZone: 'Asia/Riyadh', hour: '2-digit', hourCycle: 'h23'}).format(new Date('2026-01-01T00:00:00Z'))});
    }
    const view = cache.get(key);
    byId('locale').dir = view.locale === 'ar' ? 'rtl' : 'ltr';
    byId('locale').textContent = view.tenant + ':' + view.text + ':' + view.date;
    byId('locale').lang = view.locale;
    return {...view, direction: getComputedStyle(byId('locale')).direction};
  }
};
