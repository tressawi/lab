#!/usr/bin/env node

/**
 * Installation script for Claude Enterprise Agents
 *
 * This script:
 * 1. Copies agent definitions to ~/.claude/agents/
 * 2. Copies skills to ~/.claude/skills/
 * 3. Configures MCP servers in Claude Code settings
 * 4. Copies CLAUDE.md to the user's home directory
 */

import fs from 'fs/promises';
import path from 'path';
import os from 'os';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const packageRoot = path.resolve(__dirname, '..');

const CLAUDE_DIR = path.join(os.homedir(), '.claude');
const AGENTS_DIR = path.join(CLAUDE_DIR, 'agents');
const SKILLS_DIR = path.join(CLAUDE_DIR, 'skills');
const SETTINGS_FILE = path.join(CLAUDE_DIR, 'settings.json');

async function ensureDir(dir) {
  await fs.mkdir(dir, { recursive: true });
}

async function copyDir(src, dest) {
  await ensureDir(dest);
  const entries = await fs.readdir(src, { withFileTypes: true });

  for (const entry of entries) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);

    if (entry.isDirectory()) {
      await copyDir(srcPath, destPath);
    } else {
      await fs.copyFile(srcPath, destPath);
      console.log(`  Copied: ${destPath}`);
    }
  }
}

async function readJsonFile(filePath) {
  try {
    const content = await fs.readFile(filePath, 'utf-8');
    return JSON.parse(content);
  } catch {
    return {};
  }
}

async function writeJsonFile(filePath, data) {
  await fs.writeFile(filePath, JSON.stringify(data, null, 2));
}

async function configureMcpServers() {
  const settings = await readJsonFile(SETTINGS_FILE);

  // Initialize mcpServers if not present
  if (!settings.mcpServers) {
    settings.mcpServers = {};
  }

  // Add our MCP servers
  const mcpServers = {
    'architecture-standards': {
      command: 'node',
      args: [path.join(packageRoot, 'mcp-servers/architecture-standards/index.js')],
      env: {
        // Users should set these in their environment
        CONFLUENCE_URL: '${CONFLUENCE_URL}',
        CONFLUENCE_USERNAME: '${CONFLUENCE_USERNAME}',
        CONFLUENCE_API_TOKEN: '${CONFLUENCE_API_TOKEN}',
        CONFLUENCE_SPACE_KEY: '${CONFLUENCE_SPACE_KEY}',
        SHAREPOINT_TENANT_ID: '${SHAREPOINT_TENANT_ID}',
        SHAREPOINT_CLIENT_ID: '${SHAREPOINT_CLIENT_ID}',
        SHAREPOINT_CLIENT_SECRET: '${SHAREPOINT_CLIENT_SECRET}',
        SHAREPOINT_SITE_URL: '${SHAREPOINT_SITE_URL}',
      },
    },
    'cicd-integration': {
      command: 'node',
      args: [path.join(packageRoot, 'mcp-servers/cicd-integration/index.js')],
      env: {
        JENKINS_URL: '${JENKINS_URL}',
        JENKINS_USERNAME: '${JENKINS_USERNAME}',
        JENKINS_API_TOKEN: '${JENKINS_API_TOKEN}',
        ARTIFACTORY_URL: '${ARTIFACTORY_URL}',
        ARTIFACTORY_USERNAME: '${ARTIFACTORY_USERNAME}',
        ARTIFACTORY_API_KEY: '${ARTIFACTORY_API_KEY}',
        ARTIFACTORY_DEFAULT_REPO: '${ARTIFACTORY_DEFAULT_REPO}',
      },
    },
    'approval-gateway': {
      command: 'node',
      args: [path.join(packageRoot, 'mcp-servers/approval-gateway/index.js')],
      env: {
        APPROVAL_STORE_PATH: '${APPROVAL_STORE_PATH:-./approvals}',
        AUDIT_LOG_PATH: '${AUDIT_LOG_PATH:-./audit.log}',
      },
    },
  };

  // Merge with existing settings (don't overwrite user customizations)
  for (const [name, config] of Object.entries(mcpServers)) {
    if (!settings.mcpServers[name]) {
      settings.mcpServers[name] = config;
      console.log(`  Added MCP server: ${name}`);
    } else {
      console.log(`  Skipped MCP server (already configured): ${name}`);
    }
  }

  await writeJsonFile(SETTINGS_FILE, settings);
}

async function main() {
  console.log('Installing Claude Enterprise Agents...\n');

  // 1. Copy agents
  console.log('Installing agents to ~/.claude/agents/');
  const agentsSrc = path.join(packageRoot, '.claude/agents');
  await copyDir(agentsSrc, AGENTS_DIR);

  // 2. Copy skills
  console.log('\nInstalling skills to ~/.claude/skills/');
  const skillsSrc = path.join(packageRoot, '.claude/skills');
  await copyDir(skillsSrc, SKILLS_DIR);

  // 3. Configure MCP servers
  console.log('\nConfiguring MCP servers in ~/.claude/settings.json');
  await configureMcpServers();

  // 4. Copy CLAUDE.md (only if not exists)
  const claudeMdDest = path.join(CLAUDE_DIR, 'CLAUDE.md');
  try {
    await fs.access(claudeMdDest);
    console.log('\nSkipped CLAUDE.md (already exists)');
  } catch {
    const claudeMdSrc = path.join(packageRoot, 'CLAUDE.md');
    await fs.copyFile(claudeMdSrc, claudeMdDest);
    console.log('\nInstalled CLAUDE.md to ~/.claude/');
  }

  console.log(`
Installation complete!

Available commands:
  /dev       - Development tasks (features, bugfixes, refactoring)
  /test      - Test generation and execution
  /cyber     - Security scanning
  /cicd      - Build and deployment
  /pipeline  - Full SDLC pipeline

Before using, configure these environment variables:

Confluence/SharePoint (for architecture-standards):
  CONFLUENCE_URL, CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN, CONFLUENCE_SPACE_KEY
  SHAREPOINT_TENANT_ID, SHAREPOINT_CLIENT_ID, SHAREPOINT_CLIENT_SECRET, SHAREPOINT_SITE_URL

Jenkins/Artifactory (for cicd-integration):
  JENKINS_URL, JENKINS_USERNAME, JENKINS_API_TOKEN
  ARTIFACTORY_URL, ARTIFACTORY_USERNAME, ARTIFACTORY_API_KEY

Restart Claude Code to load the new configuration.
`);
}

main().catch(error => {
  console.error('Installation failed:', error.message);
  process.exit(1);
});
