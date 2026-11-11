// Tests for the fake_urgency rule of the dsPreFilter pre-filter.
// Run with: node --test extension/utils/classifier.test.js
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

// Load the content-script style classifier (no bundler, no exports) into a
// fresh context and grab the exported pre-filter function.
const source = fs.readFileSync(path.join(__dirname, "classifier.js"), "utf8");
const sandbox = {};
vm.runInNewContext(source, sandbox);
const dsPreFilter = sandbox.dsPreFilterExport;

test("fake_urgency example from the annotation guide is flagged", () => {
  const result = dsPreFilter("Only 2 left — offer ends in 00:04:12.");
  assert.equal(result.shouldClassify, true);
  assert.equal(result.likelyCategory, "fake_urgency");
});

test("input shorter than 12 characters is not classified", () => {
  const result = dsPreFilter("Only 2");
  assert.equal(result.shouldClassify, false);
});
