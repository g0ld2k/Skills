'use strict';

const { describe, it, before, after } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const os = require('os');
const { execSync } = require('child_process');

const ROOT = path.join(__dirname, '..');
const BIN = path.join(ROOT, 'bin', 'skills.js');

function run(args = '') {
  return execSync(`node "${BIN}" ${args}`, {
    encoding: 'utf8',
    cwd: ROOT,
  });
}

describe('skills CLI', () => {
  it('shows help with --help flag', () => {
    const output = run('--help');
    assert.match(output, /Usage:/);
    assert.match(output, /install/);
    assert.match(output, /list/);
  });

  it('shows help with help command', () => {
    const output = run('help');
    assert.match(output, /Usage:/);
  });

  it('lists available skills, agents, and prompts', () => {
    const output = run('list');
    assert.match(output, /Skills/i);
    assert.match(output, /Agents/i);
    assert.match(output, /Prompts/i);
    assert.match(output, /code-review/);
    assert.match(output, /summarize/);
    assert.match(output, /dev-assistant/);
    assert.match(output, /commit-message/);
  });

  describe('install command', () => {
    let tmpDir;

    before(() => {
      tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'skills-test-'));
    });

    after(() => {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    });

    it('installs skills to the specified directory', () => {
      const output = run(`install "${tmpDir}"`);
      assert.match(output, /Installing skills to/);
      assert.match(output, /Done!/);
    });

    it('copies skills files to the target directory', () => {
      const skillsDir = path.join(tmpDir, 'skills');
      assert.ok(fs.existsSync(skillsDir), 'skills/ directory should exist');
      assert.ok(
        fs.existsSync(path.join(skillsDir, 'code-review.md')),
        'code-review.md should be installed'
      );
    });

    it('copies agents files to the target directory', () => {
      const agentsDir = path.join(tmpDir, 'agents');
      assert.ok(fs.existsSync(agentsDir), 'agents/ directory should exist');
      assert.ok(
        fs.existsSync(path.join(agentsDir, 'dev-assistant.md')),
        'dev-assistant.md should be installed'
      );
    });

    it('copies prompts files to the target directory', () => {
      const promptsDir = path.join(tmpDir, 'prompts');
      assert.ok(fs.existsSync(promptsDir), 'prompts/ directory should exist');
      assert.ok(
        fs.existsSync(path.join(promptsDir, 'commit-message.md')),
        'commit-message.md should be installed'
      );
    });
  });
});

describe('skills index (programmatic API)', () => {
  let api;

  before(() => {
    api = require('../index.js');
  });

  it('exports skills object', () => {
    assert.ok(typeof api.skills === 'object');
    assert.ok('code-review' in api.skills);
    assert.ok('summarize' in api.skills);
  });

  it('exports agents object', () => {
    assert.ok(typeof api.agents === 'object');
    assert.ok('dev-assistant' in api.agents);
  });

  it('exports prompts object', () => {
    assert.ok(typeof api.prompts === 'object');
    assert.ok('code-review' in api.prompts);
    assert.ok('commit-message' in api.prompts);
  });

  it('skill content is a non-empty string', () => {
    assert.ok(typeof api.skills['code-review'] === 'string');
    assert.ok(api.skills['code-review'].length > 0);
  });
});
