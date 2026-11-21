'use strict';
const form = document.getElementById('signup-form');
const button = document.getElementById('submit');
const status = document.getElementById('form-status');
let available = form.dataset.available === 'true';
let signupToken = document.querySelector('meta[name="signup-token"]').content;
button.disabled = !available;
status.textContent = available ? '' : 'Signups are unavailable in this preview. The operator must configure a private signup directory.';
if (form.dataset.available === '__AVAILABLE__') {
  status.textContent = 'Checking signup availability…';
  fetch('/api/config', {cache: 'no-store'})
    .then(async response => {
      const config = await response.json();
      if (!response.ok || config.available !== true || typeof config.token !== 'string') throw new Error();
      signupToken = config.token;
      available = true;
      button.disabled = false;
      status.textContent = '';
    })
    .catch(() => {
      status.textContent = 'Signups are unavailable. Please try again later.';
    });
}
const fields = ['email', 'tool', 'problem', 'consent'];
for (const name of fields) {
  document.getElementById(name).addEventListener('input', () => {
    document.getElementById(name).removeAttribute('aria-invalid');
    document.getElementById(`${name}-error`).textContent = '';
  });
}
form.addEventListener('submit', async event => {
  event.preventDefault();
  if (!available || button.disabled) return;
  let firstInvalid = null;
  const payload = {};
  for (const name of fields) {
    const input = document.getElementById(name);
    payload[name] = name === 'consent' ? input.checked : input.value.trim();
    const valid = input.checkValidity() && Boolean(payload[name]);
    input.setAttribute('aria-invalid', String(!valid));
    document.getElementById(`${name}-error`).textContent = valid ? '' :
      name === 'email' ? 'Enter a valid email address.' :
      name === 'consent' ? 'Please give consent before submitting.' : 'Please complete this field.';
    if (!valid && !firstInvalid) firstInvalid = input;
  }
  if (firstInvalid) {
    status.textContent = 'Please check the highlighted fields.';
    firstInvalid.focus();
    return;
  }
  button.disabled = true;
  status.textContent = 'Saving your interest…';
  try {
    const response = await fetch('/api/signup', {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-SCOP-Token': signupToken},
      body: JSON.stringify(payload)
    });
    const result = await response.json();
    if (!response.ok || result.saved !== true) throw new Error('Submission failed');
    status.textContent = 'Your interest has been saved. Thank you for helping shape SCOP.';
    form.reset();
  } catch {
    status.textContent = 'We could not confirm your submission. Please try again later. No confirmation email has been sent.';
  } finally {
    button.disabled = false;
  }
});

// One scheduled frame per scroll event batch; no perpetual animation loop.
const motionQuery = matchMedia('(prefers-reduced-motion: no-preference) and (min-width: 1001px)');
const hero = document.querySelector('.hero');
const art = document.querySelector('.hero-art');
const depth = document.querySelector('.hero-depth');
const content = document.querySelector('.hero-content');
let pointerX = 0;
let pointerY = 0;
const pointerQuery = matchMedia('(hover: hover) and (pointer: fine)');
let motionFrame = null;
let heroHeight = hero.offsetHeight;
function paintDepth() {
  motionFrame = null;
  if (!motionQuery.matches) return;
  const progress = Math.min(Math.max(window.scrollY / heroHeight, 0), 1);
  depth.style.transform = `translate3d(${-pointerX}px, ${progress * 15 - pointerY}px, -35px)`;
  art.style.transform = `translate3d(${pointerX}px, ${progress * 28 + pointerY}px, 0) scale(${1 + progress * 0.025}) rotateX(${progress * 1.2}deg)`;
  content.style.transform = `translate3d(0, ${progress * -10}px, 15px)`;
}
function scheduleDepth() {
  if (motionQuery.matches && motionFrame === null) motionFrame = requestAnimationFrame(paintDepth);
}
function resetMotion() {
  if (motionFrame !== null) cancelAnimationFrame(motionFrame);
  motionFrame = null;
  pointerX = 0;
  pointerY = 0;
  for (const layer of [depth, art, content]) layer.style.removeProperty('transform');
  heroHeight = hero.offsetHeight;
  scheduleDepth();
}
window.addEventListener('scroll', scheduleDepth, {passive:true});
window.addEventListener('resize', resetMotion, {passive:true});
motionQuery.addEventListener('change', resetMotion);
scheduleDepth();

hero.addEventListener('pointermove', event => {
  if (!motionQuery.matches || !pointerQuery.matches || event.pointerType !== 'mouse') return;
  pointerX = (event.clientX / window.innerWidth - 0.5) * 6;
  pointerY = (event.clientY / window.innerHeight - 0.5) * 4;
  scheduleDepth();
}, {passive: true});
hero.addEventListener('pointerleave', () => {
  pointerX = 0;
  pointerY = 0;
  scheduleDepth();
}, {passive: true});
