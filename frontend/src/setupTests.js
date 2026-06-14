/* eslint-env jest */
/* global jest */
// Jest DOM matchers (toBeInTheDocument, etc.)
import '@testing-library/jest-dom';
import { TextEncoder, TextDecoder } from 'util';

// JSDOM does not polyfill TextEncoder/TextDecoder — required by react-router v7.
if (!global.TextEncoder) global.TextEncoder = TextEncoder;
if (!global.TextDecoder) global.TextDecoder = TextDecoder;

// React-Scripts already polyfills fetch in JSDOM via msw-like setup,
// but we mock fetch globally just in case any code path slips through
// the api mock and tries to hit the network.
if (!global.fetch) {
  global.fetch = jest.fn(() =>
    Promise.resolve({ ok: true, json: () => Promise.resolve({}) }),
  );
}

// JSDOM does not implement matchMedia — some shadcn components query it.
if (typeof window !== 'undefined' && !window.matchMedia) {
  window.matchMedia = (query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  });
}
