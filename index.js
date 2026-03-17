'use strict';

const fs = require('fs');
const path = require('path');

const SKILLS_DIR = path.join(__dirname, 'skills');
const AGENTS_DIR = path.join(__dirname, 'agents');
const PROMPTS_DIR = path.join(__dirname, 'prompts');

function readMarkdown(filePath) {
  return fs.readFileSync(filePath, 'utf8');
}

function loadCategory(dir) {
  if (!fs.existsSync(dir)) return {};
  return Object.fromEntries(
    fs
      .readdirSync(dir)
      .filter((f) => f.endsWith('.md'))
      .map((f) => [path.basename(f, '.md'), readMarkdown(path.join(dir, f))])
  );
}

module.exports = {
  skills: loadCategory(SKILLS_DIR),
  agents: loadCategory(AGENTS_DIR),
  prompts: loadCategory(PROMPTS_DIR),
};
