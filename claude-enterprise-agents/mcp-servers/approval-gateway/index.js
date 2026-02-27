#!/usr/bin/env node

/**
 * Approval Gateway MCP Server
 *
 * Provides human-in-the-loop approval workflow for enterprise SDLC pipelines.
 * Supports single approval for staging and dual approval for production.
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import fs from 'fs/promises';
import path from 'path';
import crypto from 'crypto';

// Configuration from environment
const config = {
  storePath: process.env.APPROVAL_STORE_PATH || './approvals',
  auditLogPath: process.env.AUDIT_LOG_PATH || './audit.log',
  // Integration with external systems (optional)
  servicenow: {
    url: process.env.SERVICENOW_URL || '',
    username: process.env.SERVICENOW_USERNAME || '',
    password: process.env.SERVICENOW_PASSWORD || '',
  },
  jira: {
    url: process.env.JIRA_URL || '',
    username: process.env.JIRA_USERNAME || '',
    apiToken: process.env.JIRA_API_TOKEN || '',
  },
};

// Approval types
const ApprovalType = {
  DESIGN_REVIEW: 'design_review',
  CODE_REVIEW: 'code_review',
  TEST_REVIEW: 'test_review',
  SECURITY_REVIEW: 'security_review',
  DEPLOYMENT_STAGING: 'deployment_staging',
  DEPLOYMENT_PROD: 'deployment_prod',
  ROLLBACK: 'rollback',
};

// Approval requirements
const ApprovalRequirements = {
  [ApprovalType.DESIGN_REVIEW]: { count: 1, description: 'Design document review' },
  [ApprovalType.CODE_REVIEW]: { count: 1, description: 'Code review' },
  [ApprovalType.TEST_REVIEW]: { count: 1, description: 'Test review' },
  [ApprovalType.SECURITY_REVIEW]: { count: 1, description: 'Security scan review' },
  [ApprovalType.DEPLOYMENT_STAGING]: { count: 1, description: 'Staging deployment' },
  [ApprovalType.DEPLOYMENT_PROD]: { count: 2, description: 'Production deployment (dual approval)' },
  [ApprovalType.ROLLBACK]: { count: 1, description: 'Rollback approval' },
};

// Ensure store directory exists
async function ensureStorePath() {
  await fs.mkdir(config.storePath, { recursive: true });
}

// Generate unique request ID
function generateRequestId() {
  return `apr-${Date.now()}-${crypto.randomBytes(4).toString('hex')}`;
}

// Read approval request from store
async function readApprovalRequest(requestId) {
  const filePath = path.join(config.storePath, `${requestId}.json`);
  try {
    const content = await fs.readFile(filePath, 'utf-8');
    return JSON.parse(content);
  } catch {
    return null;
  }
}

// Write approval request to store
async function writeApprovalRequest(request) {
  await ensureStorePath();
  const filePath = path.join(config.storePath, `${request.id}.json`);
  await fs.writeFile(filePath, JSON.stringify(request, null, 2));
}

// Append to audit log
async function auditLog(entry) {
  const logEntry = {
    timestamp: new Date().toISOString(),
    ...entry,
  };
  await fs.appendFile(
    config.auditLogPath,
    JSON.stringify(logEntry) + '\n'
  );
}

// Create the MCP server
const server = new Server(
  {
    name: 'approval-gateway',
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
        name: 'request_approval',
        description: 'Create an approval request and wait for approval',
        inputSchema: {
          type: 'object',
          properties: {
            type: {
              type: 'string',
              enum: Object.values(ApprovalType),
              description: 'Type of approval needed',
            },
            title: {
              type: 'string',
              description: 'Title of the approval request',
            },
            description: {
              type: 'string',
              description: 'Detailed description of what needs approval',
            },
            context: {
              type: 'object',
              description: 'Additional context (files changed, pipeline ID, etc.)',
            },
            pipeline_id: {
              type: 'string',
              description: 'Pipeline ID for correlation',
            },
          },
          required: ['type', 'title', 'description'],
        },
      },
      {
        name: 'request_dual_approval',
        description: 'Create a dual approval request for production deployments',
        inputSchema: {
          type: 'object',
          properties: {
            title: {
              type: 'string',
              description: 'Title of the approval request',
            },
            description: {
              type: 'string',
              description: 'Detailed description of the production deployment',
            },
            artifact_version: {
              type: 'string',
              description: 'Version being deployed',
            },
            artifact_sha256: {
              type: 'string',
              description: 'SHA-256 checksum of the artifact',
            },
            pipeline_id: {
              type: 'string',
              description: 'Pipeline ID for correlation',
            },
          },
          required: ['title', 'description', 'artifact_version'],
        },
      },
      {
        name: 'check_approval_status',
        description: 'Check the status of an approval request',
        inputSchema: {
          type: 'object',
          properties: {
            request_id: {
              type: 'string',
              description: 'The approval request ID',
            },
          },
          required: ['request_id'],
        },
      },
      {
        name: 'approve_request',
        description: 'Approve a pending request (for use by approvers)',
        inputSchema: {
          type: 'object',
          properties: {
            request_id: {
              type: 'string',
              description: 'The approval request ID',
            },
            approver: {
              type: 'string',
              description: 'Name/ID of the approver',
            },
            comment: {
              type: 'string',
              description: 'Optional comment',
            },
          },
          required: ['request_id', 'approver'],
        },
      },
      {
        name: 'reject_request',
        description: 'Reject a pending request (for use by approvers)',
        inputSchema: {
          type: 'object',
          properties: {
            request_id: {
              type: 'string',
              description: 'The approval request ID',
            },
            approver: {
              type: 'string',
              description: 'Name/ID of the rejector',
            },
            reason: {
              type: 'string',
              description: 'Reason for rejection',
            },
          },
          required: ['request_id', 'approver', 'reason'],
        },
      },
      {
        name: 'get_approval_history',
        description: 'Get approval history for a pipeline or time range',
        inputSchema: {
          type: 'object',
          properties: {
            pipeline_id: {
              type: 'string',
              description: 'Filter by pipeline ID',
            },
            type: {
              type: 'string',
              enum: Object.values(ApprovalType),
              description: 'Filter by approval type',
            },
            limit: {
              type: 'number',
              description: 'Maximum number of records to return',
              default: 20,
            },
          },
        },
      },
      {
        name: 'list_pending_approvals',
        description: 'List all pending approval requests',
        inputSchema: {
          type: 'object',
          properties: {
            type: {
              type: 'string',
              enum: Object.values(ApprovalType),
              description: 'Filter by approval type',
            },
          },
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
      case 'request_approval': {
        const requirements = ApprovalRequirements[args.type];
        if (!requirements) {
          throw new Error(`Unknown approval type: ${args.type}`);
        }

        const approvalRequest = {
          id: generateRequestId(),
          type: args.type,
          title: args.title,
          description: args.description,
          context: args.context || {},
          pipeline_id: args.pipeline_id,
          required_count: requirements.count,
          approvals: [],
          status: 'pending',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };

        await writeApprovalRequest(approvalRequest);

        await auditLog({
          action: 'approval_requested',
          request_id: approvalRequest.id,
          type: args.type,
          title: args.title,
          pipeline_id: args.pipeline_id,
        });

        return {
          content: [{
            type: 'text',
            text: `## Approval Request Created

- **Request ID**: ${approvalRequest.id}
- **Type**: ${requirements.description}
- **Title**: ${args.title}
- **Required Approvals**: ${requirements.count}
- **Status**: PENDING

### Description
${args.description}

### Next Steps
This request requires ${requirements.count} approval(s) before proceeding.
Use \`check_approval_status\` with request ID \`${approvalRequest.id}\` to check status.`,
          }],
        };
      }

      case 'request_dual_approval': {
        const approvalRequest = {
          id: generateRequestId(),
          type: ApprovalType.DEPLOYMENT_PROD,
          title: args.title,
          description: args.description,
          context: {
            artifact_version: args.artifact_version,
            artifact_sha256: args.artifact_sha256,
          },
          pipeline_id: args.pipeline_id,
          required_count: 2,
          approvals: [],
          status: 'pending',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };

        await writeApprovalRequest(approvalRequest);

        await auditLog({
          action: 'dual_approval_requested',
          request_id: approvalRequest.id,
          artifact_version: args.artifact_version,
          pipeline_id: args.pipeline_id,
        });

        return {
          content: [{
            type: 'text',
            text: `## Dual Approval Request Created (Production Deployment)

- **Request ID**: ${approvalRequest.id}
- **Artifact Version**: ${args.artifact_version}
- **SHA-256**: ${args.artifact_sha256 || 'Not provided'}
- **Required Approvals**: 2 (from different approvers)
- **Status**: PENDING

### Description
${args.description}

### IMPORTANT
Production deployment requires approval from **TWO DIFFERENT** approvers.
The pipeline will block until both approvals are obtained.`,
          }],
        };
      }

      case 'check_approval_status': {
        const approvalRequest = await readApprovalRequest(args.request_id);
        if (!approvalRequest) {
          throw new Error(`Approval request not found: ${args.request_id}`);
        }

        const approvalList = approvalRequest.approvals.length > 0
          ? approvalRequest.approvals.map(a =>
              `- ${a.approver} at ${a.timestamp}${a.comment ? ` - "${a.comment}"` : ''}`
            ).join('\n')
          : 'None yet';

        return {
          content: [{
            type: 'text',
            text: `## Approval Status

- **Request ID**: ${approvalRequest.id}
- **Type**: ${ApprovalRequirements[approvalRequest.type]?.description || approvalRequest.type}
- **Title**: ${approvalRequest.title}
- **Status**: ${approvalRequest.status.toUpperCase()}
- **Approvals**: ${approvalRequest.approvals.length}/${approvalRequest.required_count}

### Approvers
${approvalList}

${approvalRequest.status === 'approved' ? '**Ready to proceed.**' : approvalRequest.status === 'rejected' ? `**Rejected**: ${approvalRequest.rejection_reason}` : '**Waiting for approval(s).**'}`,
          }],
        };
      }

      case 'approve_request': {
        const approvalRequest = await readApprovalRequest(args.request_id);
        if (!approvalRequest) {
          throw new Error(`Approval request not found: ${args.request_id}`);
        }

        if (approvalRequest.status !== 'pending') {
          throw new Error(`Request is already ${approvalRequest.status}`);
        }

        // Check for duplicate approver (important for dual approval)
        if (approvalRequest.approvals.some(a => a.approver === args.approver)) {
          throw new Error(`${args.approver} has already approved this request. Dual approval requires TWO DIFFERENT approvers.`);
        }

        approvalRequest.approvals.push({
          approver: args.approver,
          timestamp: new Date().toISOString(),
          comment: args.comment || '',
        });

        // Check if we have enough approvals
        if (approvalRequest.approvals.length >= approvalRequest.required_count) {
          approvalRequest.status = 'approved';
        }

        approvalRequest.updated_at = new Date().toISOString();
        await writeApprovalRequest(approvalRequest);

        await auditLog({
          action: 'approval_given',
          request_id: approvalRequest.id,
          approver: args.approver,
          new_status: approvalRequest.status,
        });

        return {
          content: [{
            type: 'text',
            text: `## Approval Recorded

- **Request ID**: ${approvalRequest.id}
- **Approver**: ${args.approver}
- **Approvals**: ${approvalRequest.approvals.length}/${approvalRequest.required_count}
- **Status**: ${approvalRequest.status.toUpperCase()}

${approvalRequest.status === 'approved' ? '**All required approvals obtained. Ready to proceed.**' : `**Waiting for ${approvalRequest.required_count - approvalRequest.approvals.length} more approval(s).**`}`,
          }],
        };
      }

      case 'reject_request': {
        const approvalRequest = await readApprovalRequest(args.request_id);
        if (!approvalRequest) {
          throw new Error(`Approval request not found: ${args.request_id}`);
        }

        if (approvalRequest.status !== 'pending') {
          throw new Error(`Request is already ${approvalRequest.status}`);
        }

        approvalRequest.status = 'rejected';
        approvalRequest.rejection_reason = args.reason;
        approvalRequest.rejected_by = args.approver;
        approvalRequest.rejected_at = new Date().toISOString();
        approvalRequest.updated_at = new Date().toISOString();

        await writeApprovalRequest(approvalRequest);

        await auditLog({
          action: 'approval_rejected',
          request_id: approvalRequest.id,
          rejector: args.approver,
          reason: args.reason,
        });

        return {
          content: [{
            type: 'text',
            text: `## Request Rejected

- **Request ID**: ${approvalRequest.id}
- **Rejected By**: ${args.approver}
- **Reason**: ${args.reason}
- **Status**: REJECTED

The pipeline should not proceed. Please address the feedback and create a new approval request.`,
          }],
        };
      }

      case 'get_approval_history': {
        // Read all approval files (simplified - in production use a database)
        const files = await fs.readdir(config.storePath).catch(() => []);
        const requests = [];

        for (const file of files.slice(0, args.limit || 20)) {
          if (file.endsWith('.json')) {
            const request = await readApprovalRequest(file.replace('.json', ''));
            if (request) {
              if (args.pipeline_id && request.pipeline_id !== args.pipeline_id) continue;
              if (args.type && request.type !== args.type) continue;
              requests.push(request);
            }
          }
        }

        const formatted = requests.map(r =>
          `- **${r.id}** | ${r.type} | ${r.status.toUpperCase()} | ${r.title}`
        ).join('\n');

        return {
          content: [{
            type: 'text',
            text: `## Approval History (${requests.length} records)\n\n${formatted || 'No approval records found.'}`,
          }],
        };
      }

      case 'list_pending_approvals': {
        const files = await fs.readdir(config.storePath).catch(() => []);
        const pending = [];

        for (const file of files) {
          if (file.endsWith('.json')) {
            const request = await readApprovalRequest(file.replace('.json', ''));
            if (request && request.status === 'pending') {
              if (args.type && request.type !== args.type) continue;
              pending.push(request);
            }
          }
        }

        const formatted = pending.map(r =>
          `### ${r.id}
- **Type**: ${ApprovalRequirements[r.type]?.description || r.type}
- **Title**: ${r.title}
- **Created**: ${r.created_at}
- **Approvals**: ${r.approvals.length}/${r.required_count}`
        ).join('\n\n');

        return {
          content: [{
            type: 'text',
            text: `## Pending Approvals (${pending.length})\n\n${formatted || 'No pending approvals.'}`,
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
  await ensureStorePath();
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('Approval Gateway MCP Server running');
}

main().catch(console.error);
