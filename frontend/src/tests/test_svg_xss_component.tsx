/**
 * XSS-safety regression test for VisualArtifactRenderer.
 *
 * Renders the real component with a malicious SVG payload using
 * renderToStaticMarkup and asserts that:
 *   1. The output contains a data:image/svg+xml src (sandboxed img approach).
 *   2. The raw <image element is NOT present in the HTML output.
 *   3. The onerror= attribute is NOT present in the HTML output.
 *
 * This test FAILS if the renderer switches back to dangerouslySetInnerHTML,
 * because the raw SVG tags (including event handlers) would appear in the markup.
 */

import assert from 'node:assert';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { VisualArtifactRenderer } from '../components/VisualArtifactRenderer';
import type { VisualArtifact } from '../types/chat';

console.log('🧪 Starting SVG XSS Component Regression Test...\n');

// A malicious SVG payload: contains an event handler that would execute
// script if the SVG were injected as inline HTML.
const maliciousSvgContent =
  `<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">` +
  `<image href="x" onerror="document.title='XSS';window._xss=true"/>` +
  `</svg>`;

const maliciousSvgArtifact: VisualArtifact = {
  id: 'test-xss-svg',
  type: 'svg',
  content: maliciousSvgContent,
  title: 'XSS Test Diagram',
};

function runTest() {
  // Render the component to static markup (server-side, no browser DOM)
  const html = renderToStaticMarkup(
    React.createElement(VisualArtifactRenderer, { artifact: maliciousSvgArtifact })
  );

  // 1. The preview must use the data-URI img approach
  assert(
    html.includes('data:image/svg+xml'),
    `Expected output to contain "data:image/svg+xml" (sandboxed img), but got:\n${html}`
  );

  // 2. The raw <image element must NOT appear in the HTML output
  assert(
    !html.includes('<image'),
    `SECURITY FAIL: Raw <image element found in rendered HTML.\n` +
    `This means dangerouslySetInnerHTML was used — the XSS fix has been reverted.\n` +
    `HTML output:\n${html}`
  );

  // 3. The onerror= handler must NOT appear in the HTML output
  assert(
    !html.includes('onerror='),
    `SECURITY FAIL: "onerror=" attribute found in rendered HTML.\n` +
    `The event handler payload was injected as live markup — XSS vector is open.\n` +
    `HTML output:\n${html}`
  );

  console.log('▶ [1/1] VisualArtifactRenderer XSS-safety (component rendering)');
  console.log('  ✔ Rendered HTML contains data:image/svg+xml (sandboxed img)');
  console.log('  ✔ Rendered HTML does NOT contain raw <image element');
  console.log('  ✔ Rendered HTML does NOT contain onerror= attribute');
  console.log('\n✅ SVG XSS Component Regression Test Passed!\n');
}

runTest();
