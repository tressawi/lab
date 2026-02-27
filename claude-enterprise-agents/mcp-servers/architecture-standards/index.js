#!/usr/bin/env node

/**
 * Architecture Standards MCP Server
 *
 * Provides access to enterprise architecture, security, and coding standards
 * from Confluence and SharePoint documentation systems.
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ListResourcesRequestSchema,
  ReadResourceRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';

// Configuration from environment
const config = {
  confluence: {
    baseUrl: process.env.CONFLUENCE_URL || 'https://confluence.example.com',
    username: process.env.CONFLUENCE_USERNAME || '',
    apiToken: process.env.CONFLUENCE_API_TOKEN || '',
    spaceKey: process.env.CONFLUENCE_SPACE_KEY || 'ARCH',
  },
  sharepoint: {
    tenantId: process.env.SHAREPOINT_TENANT_ID || '',
    clientId: process.env.SHAREPOINT_CLIENT_ID || '',
    clientSecret: process.env.SHAREPOINT_CLIENT_SECRET || '',
    siteUrl: process.env.SHAREPOINT_SITE_URL || '',
  },
  cache: {
    ttlMs: parseInt(process.env.CACHE_TTL_MS || '3600000'), // 1 hour default
  }
};

// Simple in-memory cache
const cache = new Map();

function getCached(key) {
  const entry = cache.get(key);
  if (entry && Date.now() - entry.timestamp < config.cache.ttlMs) {
    return entry.data;
  }
  cache.delete(key);
  return null;
}

function setCache(key, data) {
  cache.set(key, { data, timestamp: Date.now() });
}

// Confluence API client
async function fetchFromConfluence(endpoint) {
  const cacheKey = `confluence:${endpoint}`;
  const cached = getCached(cacheKey);
  if (cached) return cached;

  const auth = Buffer.from(`${config.confluence.username}:${config.confluence.apiToken}`).toString('base64');

  try {
    const response = await fetch(`${config.confluence.baseUrl}/wiki/rest/api${endpoint}`, {
      headers: {
        'Authorization': `Basic ${auth}`,
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Confluence API error: ${response.status}`);
    }

    const data = await response.json();
    setCache(cacheKey, data);
    return data;
  } catch (error) {
    console.error('Confluence fetch error:', error.message);
    return null;
  }
}

// SharePoint Graph API client
async function fetchFromSharePoint(endpoint) {
  const cacheKey = `sharepoint:${endpoint}`;
  const cached = getCached(cacheKey);
  if (cached) return cached;

  // Get access token (simplified - in production use proper OAuth flow)
  try {
    const tokenResponse = await fetch(
      `https://login.microsoftonline.com/${config.sharepoint.tenantId}/oauth2/v2.0/token`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
          client_id: config.sharepoint.clientId,
          client_secret: config.sharepoint.clientSecret,
          scope: 'https://graph.microsoft.com/.default',
          grant_type: 'client_credentials',
        }),
      }
    );

    const tokenData = await tokenResponse.json();

    const response = await fetch(`https://graph.microsoft.com/v1.0${endpoint}`, {
      headers: {
        'Authorization': `Bearer ${tokenData.access_token}`,
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`SharePoint API error: ${response.status}`);
    }

    const data = await response.json();
    setCache(cacheKey, data);
    return data;
  } catch (error) {
    console.error('SharePoint fetch error:', error.message);
    return null;
  }
}

// Search standards across both systems
async function searchStandards(query, category = null) {
  const results = [];

  // Search Confluence
  const cql = category
    ? `space = "${config.confluence.spaceKey}" AND label = "${category}" AND text ~ "${query}"`
    : `space = "${config.confluence.spaceKey}" AND text ~ "${query}"`;

  const confluenceResults = await fetchFromConfluence(
    `/content/search?cql=${encodeURIComponent(cql)}&limit=10`
  );

  if (confluenceResults?.results) {
    for (const page of confluenceResults.results) {
      results.push({
        source: 'confluence',
        title: page.title,
        url: `${config.confluence.baseUrl}/wiki${page._links.webui}`,
        excerpt: page.excerpt || '',
        category: category || 'general',
      });
    }
  }

  // Search SharePoint
  const sharepointResults = await fetchFromSharePoint(
    `/sites/${config.sharepoint.siteUrl}/drive/root/search(q='${encodeURIComponent(query)}')`
  );

  if (sharepointResults?.value) {
    for (const item of sharepointResults.value) {
      results.push({
        source: 'sharepoint',
        title: item.name,
        url: item.webUrl,
        excerpt: item.description || '',
        category: category || 'general',
      });
    }
  }

  return results;
}

// Get specific standard by category
async function getStandardsByCategory(category) {
  const categoryLabels = {
    architecture: ['architecture', 'patterns', 'design'],
    security: ['security', 'owasp', 'compliance'],
    coding: ['coding', 'style', 'conventions'],
    testing: ['testing', 'qa', 'coverage'],
    deployment: ['deployment', 'cicd', 'infrastructure'],
  };

  const labels = categoryLabels[category] || [category];
  const results = [];

  for (const label of labels) {
    const searchResults = await searchStandards('', label);
    results.push(...searchResults);
  }

  return results;
}

// Create the MCP server
const server = new Server(
  {
    name: 'architecture-standards',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
      resources: {},
    },
  }
);

// List available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: 'get_architecture_patterns',
        description: 'Get architecture patterns and design guidelines (microservices, API design, data models)',
        inputSchema: {
          type: 'object',
          properties: {
            topic: {
              type: 'string',
              description: 'Specific topic to search for (e.g., "microservices", "api design", "event-driven")',
            },
          },
        },
      },
      {
        name: 'get_security_standards',
        description: 'Get security standards and compliance requirements (OWASP, encryption, authentication)',
        inputSchema: {
          type: 'object',
          properties: {
            topic: {
              type: 'string',
              description: 'Specific security topic (e.g., "authentication", "encryption", "owasp")',
            },
          },
        },
      },
      {
        name: 'get_coding_standards',
        description: 'Get coding standards and style guides for specific languages',
        inputSchema: {
          type: 'object',
          properties: {
            language: {
              type: 'string',
              description: 'Programming language (e.g., "python", "typescript", "java")',
            },
          },
        },
      },
      {
        name: 'get_testing_standards',
        description: 'Get testing standards and coverage requirements',
        inputSchema: {
          type: 'object',
          properties: {
            topic: {
              type: 'string',
              description: 'Testing topic (e.g., "unit testing", "integration testing", "coverage")',
            },
          },
        },
      },
      {
        name: 'get_component_library',
        description: 'Get list of pre-approved reusable components',
        inputSchema: {
          type: 'object',
          properties: {
            category: {
              type: 'string',
              description: 'Component category (e.g., "security", "validation", "http", "logging")',
            },
          },
        },
      },
      {
        name: 'search_standards',
        description: 'Full-text search across all standards documentation',
        inputSchema: {
          type: 'object',
          properties: {
            query: {
              type: 'string',
              description: 'Search query',
            },
            category: {
              type: 'string',
              description: 'Optional category filter (architecture, security, coding, testing, deployment)',
            },
          },
          required: ['query'],
        },
      },
    ],
  };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    let results;

    switch (name) {
      case 'get_architecture_patterns':
        results = await getStandardsByCategory('architecture');
        if (args?.topic) {
          results = results.filter(r =>
            r.title.toLowerCase().includes(args.topic.toLowerCase()) ||
            r.excerpt.toLowerCase().includes(args.topic.toLowerCase())
          );
        }
        break;

      case 'get_security_standards':
        results = await getStandardsByCategory('security');
        if (args?.topic) {
          results = results.filter(r =>
            r.title.toLowerCase().includes(args.topic.toLowerCase()) ||
            r.excerpt.toLowerCase().includes(args.topic.toLowerCase())
          );
        }
        break;

      case 'get_coding_standards':
        results = await searchStandards(args?.language || 'coding standards', 'coding');
        break;

      case 'get_testing_standards':
        results = await getStandardsByCategory('testing');
        if (args?.topic) {
          results = results.filter(r =>
            r.title.toLowerCase().includes(args.topic.toLowerCase())
          );
        }
        break;

      case 'get_component_library':
        results = await searchStandards(
          args?.category ? `component ${args.category}` : 'reusable component',
          'components'
        );
        break;

      case 'search_standards':
        results = await searchStandards(args.query, args?.category);
        break;

      default:
        return {
          content: [{ type: 'text', text: `Unknown tool: ${name}` }],
          isError: true,
        };
    }

    // Format results
    if (!results || results.length === 0) {
      return {
        content: [{
          type: 'text',
          text: `No standards found for this query. Please check if the documentation exists or try a different search term.`,
        }],
      };
    }

    const formatted = results.map(r =>
      `### ${r.title}\n- **Source**: ${r.source}\n- **URL**: ${r.url}\n- **Category**: ${r.category}\n${r.excerpt ? `- **Excerpt**: ${r.excerpt}` : ''}`
    ).join('\n\n');

    return {
      content: [{
        type: 'text',
        text: `## Standards Found (${results.length} results)\n\n${formatted}`,
      }],
    };

  } catch (error) {
    return {
      content: [{ type: 'text', text: `Error: ${error.message}` }],
      isError: true,
    };
  }
});

// List available resources
server.setRequestHandler(ListResourcesRequestSchema, async () => {
  return {
    resources: [
      {
        uri: 'standards://architecture/overview',
        name: 'Architecture Standards Overview',
        mimeType: 'text/markdown',
      },
      {
        uri: 'standards://security/overview',
        name: 'Security Standards Overview',
        mimeType: 'text/markdown',
      },
      {
        uri: 'standards://coding/overview',
        name: 'Coding Standards Overview',
        mimeType: 'text/markdown',
      },
      {
        uri: 'standards://testing/overview',
        name: 'Testing Standards Overview',
        mimeType: 'text/markdown',
      },
    ],
  };
});

// Read resources
server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
  const { uri } = request.params;
  const [, category] = uri.match(/standards:\/\/(\w+)\//) || [];

  if (!category) {
    return {
      contents: [{
        uri,
        mimeType: 'text/plain',
        text: 'Invalid resource URI',
      }],
    };
  }

  const standards = await getStandardsByCategory(category);
  const text = standards.map(s => `- [${s.title}](${s.url})`).join('\n');

  return {
    contents: [{
      uri,
      mimeType: 'text/markdown',
      text: `# ${category.charAt(0).toUpperCase() + category.slice(1)} Standards\n\n${text || 'No standards found.'}`,
    }],
  };
});

// Start the server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('Architecture Standards MCP Server running');
}

main().catch(console.error);
