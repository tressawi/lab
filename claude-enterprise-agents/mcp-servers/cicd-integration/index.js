#!/usr/bin/env node

/**
 * CI/CD Integration MCP Server
 *
 * Provides Jenkins build triggering and Artifactory artifact management
 * for enterprise CI/CD pipelines.
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import crypto from 'crypto';
import fs from 'fs/promises';
import path from 'path';

// Configuration from environment
const config = {
  jenkins: {
    baseUrl: process.env.JENKINS_URL || 'https://jenkins.example.com',
    username: process.env.JENKINS_USERNAME || '',
    apiToken: process.env.JENKINS_API_TOKEN || '',
    pollIntervalMs: parseInt(process.env.JENKINS_POLL_INTERVAL_MS || '5000'),
    timeoutMs: parseInt(process.env.JENKINS_TIMEOUT_MS || '600000'), // 10 min
  },
  artifactory: {
    baseUrl: process.env.ARTIFACTORY_URL || 'https://artifactory.example.com',
    username: process.env.ARTIFACTORY_USERNAME || '',
    apiKey: process.env.ARTIFACTORY_API_KEY || '',
    defaultRepo: process.env.ARTIFACTORY_DEFAULT_REPO || 'libs-release-local',
  },
};

// Jenkins API client
class JenkinsClient {
  constructor() {
    this.auth = Buffer.from(
      `${config.jenkins.username}:${config.jenkins.apiToken}`
    ).toString('base64');
  }

  async fetch(endpoint, options = {}) {
    const response = await fetch(`${config.jenkins.baseUrl}${endpoint}`, {
      ...options,
      headers: {
        'Authorization': `Basic ${this.auth}`,
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      throw new Error(`Jenkins API error: ${response.status} ${response.statusText}`);
    }

    const contentType = response.headers.get('content-type');
    if (contentType?.includes('application/json')) {
      return response.json();
    }
    return response.text();
  }

  async triggerBuild(jobName, parameters = {}) {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(parameters)) {
      params.append(key, value);
    }

    const endpoint = Object.keys(parameters).length > 0
      ? `/job/${encodeURIComponent(jobName)}/buildWithParameters?${params}`
      : `/job/${encodeURIComponent(jobName)}/build`;

    const response = await fetch(`${config.jenkins.baseUrl}${endpoint}`, {
      method: 'POST',
      headers: {
        'Authorization': `Basic ${this.auth}`,
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to trigger build: ${response.status}`);
    }

    // Get queue item location from response header
    const queueLocation = response.headers.get('location');
    return queueLocation;
  }

  async waitForBuild(queueLocation) {
    const startTime = Date.now();

    // Wait for build to start (get build number from queue)
    let buildUrl = null;
    while (!buildUrl && Date.now() - startTime < config.jenkins.timeoutMs) {
      await new Promise(r => setTimeout(r, config.jenkins.pollIntervalMs));

      try {
        const queueItem = await this.fetch(`${queueLocation}api/json`);
        if (queueItem.executable) {
          buildUrl = queueItem.executable.url;
        }
      } catch (e) {
        // Queue item may not be ready yet
      }
    }

    if (!buildUrl) {
      throw new Error('Build did not start within timeout');
    }

    // Wait for build to complete
    let buildInfo = null;
    while (Date.now() - startTime < config.jenkins.timeoutMs) {
      await new Promise(r => setTimeout(r, config.jenkins.pollIntervalMs));

      buildInfo = await this.fetch(`${buildUrl}api/json`);
      if (!buildInfo.building) {
        break;
      }
    }

    if (buildInfo.building) {
      throw new Error('Build did not complete within timeout');
    }

    return {
      buildNumber: buildInfo.number,
      result: buildInfo.result,
      duration: buildInfo.duration,
      url: buildInfo.url,
      consoleUrl: `${buildInfo.url}console`,
      artifacts: buildInfo.artifacts || [],
    };
  }

  async getBuildStatus(jobName, buildNumber) {
    const buildInfo = await this.fetch(
      `/job/${encodeURIComponent(jobName)}/${buildNumber}/api/json`
    );

    return {
      buildNumber: buildInfo.number,
      result: buildInfo.result,
      building: buildInfo.building,
      duration: buildInfo.duration,
      url: buildInfo.url,
      consoleUrl: `${buildInfo.url}console`,
    };
  }
}

// Artifactory API client
class ArtifactoryClient {
  constructor() {
    this.auth = Buffer.from(
      `${config.artifactory.username}:${config.artifactory.apiKey}`
    ).toString('base64');
  }

  async computeChecksums(filePath) {
    const content = await fs.readFile(filePath);

    return {
      sha256: crypto.createHash('sha256').update(content).digest('hex'),
      md5: crypto.createHash('md5').update(content).digest('hex'),
      size: content.length,
    };
  }

  async uploadArtifact(localPath, repository, targetPath, properties = {}) {
    const checksums = await this.computeChecksums(localPath);
    const content = await fs.readFile(localPath);
    const fileName = path.basename(localPath);

    const fullTargetPath = targetPath
      ? `${targetPath}/${fileName}`
      : fileName;

    // Build properties string
    const propsString = Object.entries(properties)
      .map(([k, v]) => `${k}=${v}`)
      .join(';');

    const url = propsString
      ? `${config.artifactory.baseUrl}/${repository}/${fullTargetPath};${propsString}`
      : `${config.artifactory.baseUrl}/${repository}/${fullTargetPath}`;

    const response = await fetch(url, {
      method: 'PUT',
      headers: {
        'Authorization': `Basic ${this.auth}`,
        'Content-Type': 'application/octet-stream',
        'X-Checksum-Sha256': checksums.sha256,
        'X-Checksum-Md5': checksums.md5,
      },
      body: content,
    });

    if (!response.ok) {
      throw new Error(`Artifactory upload failed: ${response.status}`);
    }

    return {
      repository,
      path: fullTargetPath,
      sha256: checksums.sha256,
      md5: checksums.md5,
      size: checksums.size,
      downloadUrl: `${config.artifactory.baseUrl}/${repository}/${fullTargetPath}`,
    };
  }

  async getArtifactInfo(repository, artifactPath) {
    const response = await fetch(
      `${config.artifactory.baseUrl}/api/storage/${repository}/${artifactPath}`,
      {
        headers: {
          'Authorization': `Basic ${this.auth}`,
        },
      }
    );

    if (!response.ok) {
      throw new Error(`Failed to get artifact info: ${response.status}`);
    }

    return response.json();
  }
}

const jenkins = new JenkinsClient();
const artifactory = new ArtifactoryClient();

// Create the MCP server
const server = new Server(
  {
    name: 'cicd-integration',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// List available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: 'trigger_jenkins_build',
        description: 'Trigger a Jenkins build job and wait for completion',
        inputSchema: {
          type: 'object',
          properties: {
            job_name: {
              type: 'string',
              description: 'Name of the Jenkins job to trigger',
            },
            parameters: {
              type: 'object',
              description: 'Optional build parameters as key-value pairs',
              additionalProperties: { type: 'string' },
            },
            wait: {
              type: 'boolean',
              description: 'Whether to wait for build completion (default: true)',
              default: true,
            },
          },
          required: ['job_name'],
        },
      },
      {
        name: 'get_build_status',
        description: 'Get the status of a Jenkins build',
        inputSchema: {
          type: 'object',
          properties: {
            job_name: {
              type: 'string',
              description: 'Name of the Jenkins job',
            },
            build_number: {
              type: 'number',
              description: 'Build number to check',
            },
          },
          required: ['job_name', 'build_number'],
        },
      },
      {
        name: 'upload_artifact',
        description: 'Upload an artifact to Artifactory with checksum verification',
        inputSchema: {
          type: 'object',
          properties: {
            local_path: {
              type: 'string',
              description: 'Local path to the artifact file',
            },
            repository: {
              type: 'string',
              description: 'Artifactory repository name (default: libs-release-local)',
            },
            target_path: {
              type: 'string',
              description: 'Target path within the repository',
            },
            version: {
              type: 'string',
              description: 'Version string for the artifact',
            },
            properties: {
              type: 'object',
              description: 'Additional properties to attach to the artifact',
              additionalProperties: { type: 'string' },
            },
          },
          required: ['local_path'],
        },
      },
      {
        name: 'get_artifact_info',
        description: 'Get information about an artifact in Artifactory',
        inputSchema: {
          type: 'object',
          properties: {
            repository: {
              type: 'string',
              description: 'Artifactory repository name',
            },
            artifact_path: {
              type: 'string',
              description: 'Path to the artifact within the repository',
            },
          },
          required: ['repository', 'artifact_path'],
        },
      },
      {
        name: 'deploy_to_environment',
        description: 'Deploy an artifact to a target environment (requires approval for staging/prod)',
        inputSchema: {
          type: 'object',
          properties: {
            environment: {
              type: 'string',
              enum: ['dev', 'staging', 'prod'],
              description: 'Target environment',
            },
            artifact_version: {
              type: 'string',
              description: 'Version of the artifact to deploy',
            },
            artifact_sha256: {
              type: 'string',
              description: 'SHA-256 checksum for verification',
            },
          },
          required: ['environment', 'artifact_version'],
        },
      },
      {
        name: 'rollback_deployment',
        description: 'Rollback to a previous artifact version',
        inputSchema: {
          type: 'object',
          properties: {
            environment: {
              type: 'string',
              enum: ['dev', 'staging', 'prod'],
              description: 'Target environment',
            },
            target_version: {
              type: 'string',
              description: 'Version to rollback to',
            },
            reason: {
              type: 'string',
              description: 'Reason for rollback',
            },
          },
          required: ['environment', 'target_version', 'reason'],
        },
      },
    ],
  };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case 'trigger_jenkins_build': {
        const queueLocation = await jenkins.triggerBuild(
          args.job_name,
          args.parameters || {}
        );

        if (args.wait !== false) {
          const result = await jenkins.waitForBuild(queueLocation);
          return {
            content: [{
              type: 'text',
              text: `## Build Completed

- **Job**: ${args.job_name}
- **Build Number**: ${result.buildNumber}
- **Result**: ${result.result}
- **Duration**: ${(result.duration / 1000).toFixed(1)}s
- **Console**: ${result.consoleUrl}
- **Artifacts**: ${result.artifacts.length} artifact(s)

${result.result === 'SUCCESS' ? 'Build succeeded.' : 'Build failed. Check console for details.'}`,
            }],
          };
        }

        return {
          content: [{
            type: 'text',
            text: `Build triggered. Queue location: ${queueLocation}`,
          }],
        };
      }

      case 'get_build_status': {
        const status = await jenkins.getBuildStatus(args.job_name, args.build_number);
        return {
          content: [{
            type: 'text',
            text: `## Build Status

- **Job**: ${args.job_name}
- **Build Number**: ${status.buildNumber}
- **Result**: ${status.building ? 'IN PROGRESS' : status.result}
- **Duration**: ${status.duration ? (status.duration / 1000).toFixed(1) + 's' : 'N/A'}
- **Console**: ${status.consoleUrl}`,
          }],
        };
      }

      case 'upload_artifact': {
        const props = { ...(args.properties || {}) };
        if (args.version) {
          props.version = args.version;
        }

        const result = await artifactory.uploadArtifact(
          args.local_path,
          args.repository || config.artifactory.defaultRepo,
          args.target_path || '',
          props
        );

        return {
          content: [{
            type: 'text',
            text: `## Artifact Uploaded

- **Repository**: ${result.repository}
- **Path**: ${result.path}
- **Size**: ${result.size} bytes
- **SHA-256**: ${result.sha256}
- **MD5**: ${result.md5}
- **Download URL**: ${result.downloadUrl}

Artifact uploaded successfully with checksum verification.`,
          }],
        };
      }

      case 'get_artifact_info': {
        const info = await artifactory.getArtifactInfo(args.repository, args.artifact_path);
        return {
          content: [{
            type: 'text',
            text: `## Artifact Info

- **Repository**: ${info.repo}
- **Path**: ${info.path}
- **Size**: ${info.size} bytes
- **Created**: ${info.created}
- **Modified**: ${info.lastModified}
- **SHA-256**: ${info.checksums?.sha256 || 'N/A'}
- **Download URL**: ${info.downloadUri}`,
          }],
        };
      }

      case 'deploy_to_environment': {
        // Check approval requirements
        const approvalRequired = {
          dev: 0,
          staging: 1,
          prod: 2, // Dual approval
        };

        const required = approvalRequired[args.environment];

        return {
          content: [{
            type: 'text',
            text: `## Deployment Request

- **Environment**: ${args.environment}
- **Artifact Version**: ${args.artifact_version}
- **SHA-256**: ${args.artifact_sha256 || 'Not provided'}

**Approval Required**: ${required === 0 ? 'None (auto-deploy)' : required === 1 ? 'Single approval' : 'Dual approval (two different approvers)'}

${required > 0 ? 'Please use the approval-gateway MCP server to obtain required approvals before deployment.' : 'Proceeding with deployment...'}`,
          }],
        };
      }

      case 'rollback_deployment': {
        return {
          content: [{
            type: 'text',
            text: `## Rollback Request

- **Environment**: ${args.environment}
- **Target Version**: ${args.target_version}
- **Reason**: ${args.reason}

Rollback requires approval. Please use the approval-gateway MCP server to obtain approval before proceeding.`,
          }],
        };
      }

      default:
        return {
          content: [{ type: 'text', text: `Unknown tool: ${name}` }],
          isError: true,
        };
    }
  } catch (error) {
    return {
      content: [{ type: 'text', text: `Error: ${error.message}` }],
      isError: true,
    };
  }
});

// Start the server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('CI/CD Integration MCP Server running');
}

main().catch(console.error);
