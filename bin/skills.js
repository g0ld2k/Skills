#!/usr/bin/env node

'use strict';

const fs = require('fs');
const path = require('path');
const os = require('os');

const SKILLS_DIR = path.join(__dirname, '..', 'skills');
const AGENTS_DIR = path.join(__dirname, '..', 'agents');
const PROMPTS_DIR = path.join(__dirname, '..', 'prompts');

const DEFAULT_INSTALL_DIR = path.join(os.homedir(), '.skills');

function listEntries(dir) {
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir).filter((f) => !f.startsWith('.'));
}

function copyDir(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  for (const entry of fs.readdirSync(src)) {
    const srcPath = path.join(src, entry);
    const destPath = path.join(dest, entry);
    const stat = fs.statSync(srcPath);
    if (stat.isDirectory()) {
      copyDir(srcPath, destPath);
    } else {
      fs.copyFileSync(srcPath, destPath);
    }
  }
}

function install(targetDir) {
  const dest = targetDir || DEFAULT_INSTALL_DIR;

  console.log(`Installing skills to ${dest} ...`);

  const categories = [
    { name: 'skills', src: SKILLS_DIR },
    { name: 'agents', src: AGENTS_DIR },
    { name: 'prompts', src: PROMPTS_DIR },
  ];

  let installed = 0;
  for (const { name, src } of categories) {
    if (!fs.existsSync(src)) continue;
    const entries = listEntries(src);
    if (entries.length === 0) continue;
    const categoryDest = path.join(dest, name);
    copyDir(src, categoryDest);
    console.log(`  ✓ Installed ${entries.length} ${name}`);
    installed += entries.length;
  }

  if (installed === 0) {
    console.log('  No skills, agents, or prompts found to install.');
  } else {
    console.log(`\nDone! ${installed} item(s) installed to ${dest}`);
  }
}

function list() {
  const skills = listEntries(SKILLS_DIR);
  const agents = listEntries(AGENTS_DIR);
  const prompts = listEntries(PROMPTS_DIR);

  console.log('Available Skills:');
  if (skills.length) {
    skills.forEach((s) => console.log(`  - ${s}`));
  } else {
    console.log('  (none)');
  }

  console.log('\nAvailable Agents:');
  if (agents.length) {
    agents.forEach((a) => console.log(`  - ${a}`));
  } else {
    console.log('  (none)');
  }

  console.log('\nAvailable Prompts:');
  if (prompts.length) {
    prompts.forEach((p) => console.log(`  - ${p}`));
  } else {
    console.log('  (none)');
  }
}

function printHelp() {
  console.log(`
Usage: npx skills [command] [options]

Commands:
  install [dir]   Install all skills, agents, and prompts to [dir]
                  (default: ~/.skills)
  list            List available skills, agents, and prompts
  help            Show this help message

Examples:
  npx skills
  npx skills install
  npx skills install ./my-skills
  npx skills list
`);
}

function main(args) {
  const [command, ...rest] = args;

  switch (command) {
    case 'install':
    case undefined:
      install(rest[0]);
      break;
    case 'list':
      list();
      break;
    case 'help':
    case '--help':
    case '-h':
      printHelp();
      break;
    default:
      console.error(`Unknown command: ${command}`);
      printHelp();
      process.exit(1);
  }
}

main(process.argv.slice(2));
