// SPDX-License-Identifier: MIT
// Copyright (c) 2025 dr.max

const $ = (s) => document.querySelector(s);

// Agent icon mapping - using monochrome/simplified versions for better UI integration
function getAgentIcon(agentId) {
  const iconMap = {
    "supervisor": "👑",
    "logging-monitor": "📊", 
    "coding": "🔧",
    "linting": "✅",
    "testing": "🧪",
    "github": "🐙",
    // Fallback for unknown agents
    "default": "🤖"
  };
  return iconMap[agentId] || iconMap.default;
}

const state = {
  chats: [],
  activeChatId: null,
  chatCounter: 0,
  agents: [], // Will be loaded from API
  activeAgentId: null, // Will be set to first available agent
  leftWidth: 260,
  rightWidth: 260,
  serviceStatus: {}, // Store service health status
  agentCardCollapsed: false, // Store agent card collapse state
  isTyping: false, // Track if agent is currently responding
  chatScrollPositions: {}, // Store scroll position for each chat
  configData: null, // Store configuration data
};

// Load configuration from API
async function loadConfiguration() {
  try {
    const response = await fetch("/api/config");
    const data = await response.json();
    state.configData = data;
    renderConfiguration();
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error("Failed to load configuration:", error);
    // Show error state in settings
    renderConfigurationError();
  }
}

// Render configuration data in settings panel
function renderConfiguration() {
  if (!state.configData) {
    return;
  }

  // Render global settings
  renderGlobalSettings();
  
  // Render default queries
  renderDefaultQueries();
  
  // Render agents dropdown
  renderAgentsDropdown();
}

// Render global settings section
function renderGlobalSettings() {
  const container = $("#global-settings");
  if (!container) return;

  if (!state.configData || !state.configData.settings) {
    container.innerHTML = "<div class=\"no-config\">No global settings configured</div>";
    return;
  }

  const settings = state.configData.settings;
  if (Object.keys(settings).length === 0) {
    container.innerHTML = "<div class=\"no-config\">No global settings configured</div>";
    return;
  }

  const settingsHtml = Object.entries(settings).map(([key, value]) => {
    const displayValue = formatConfigValue(value);
    return `
      <div class="config-item">
        <span class="config-key">${formatConfigKey(key)}</span>
        <span class="config-value">${displayValue}</span>
      </div>
    `;
  }).join("");

  container.innerHTML = settingsHtml;
}

// Render default queries section
function renderDefaultQueries() {
  const container = $("#default-queries-config");
  if (!container) return;

  if (!state.configData || !state.configData.default_queries) {
    container.innerHTML = "<div class=\"no-config\">No default queries configured</div>";
    return;
  }

  const queries = state.configData.default_queries;
  if (queries.length === 0) {
    container.innerHTML = "<div class=\"no-config\">No default queries configured</div>";
    return;
  }

  const queriesHtml = queries.map(query => `
    <div class="config-item">
      <span class="config-key">Query</span>
      <span class="config-value">"${query}"</span>
    </div>
  `).join("");

  container.innerHTML = queriesHtml;
}

// Render agents dropdown
function renderAgentsDropdown() {
  const selector = $("#agent-selector");
  if (!selector) return;

  if (!state.configData || !state.configData.agents) {
    selector.innerHTML = "<option value=\"\">No agents available</option>";
    return;
  }

  // Clear existing options except the first one
  selector.innerHTML = "<option value=\"\">Choose an agent...</option>";
  
  // Add agent options
  state.configData.agents.forEach(agent => {
    const option = document.createElement("option");
    option.value = agent.id;
    option.textContent = `${getAgentIcon(agent.id)} ${agent.name}`;
    selector.appendChild(option);
  });
}

// Handle agent selection
function handleAgentSelection(agentId) {
  const container = $("#agent-config");
  if (!container) return;

  if (!agentId) {
    container.innerHTML = "<div class=\"no-agent-selected\">Select an agent from the dropdown above to view its configuration</div>";
    return;
  }

  const agent = state.configData.agents.find(a => a.id === agentId);
  if (!agent) {
    container.innerHTML = "<div class=\"no-agent-selected\">Agent not found</div>";
    return;
  }

  const agentHtml = renderAgentConfiguration(agent);
  container.innerHTML = agentHtml;
}

// Render individual agent configuration
function renderAgentConfiguration(agent) {
  const sections = [];

  // Basic info section
  const basicInfo = [
    { key: "Name", value: agent.name },
    { key: "Description", value: agent.description },
    { key: "Enabled", value: agent.enabled ? "Yes" : "No" },
    { key: "Model", value: agent.model },
    { key: "Temperature", value: agent.temperature },
    { key: "Max Tokens", value: agent.max_tokens },
    { key: "Port", value: agent.port },
  ];

  const basicInfoHtml = basicInfo.map(item => `
    <div class="config-item">
      <span class="config-key">${item.key}</span>
      <span class="config-value">${item.value}</span>
    </div>
  `).join("");

  sections.push(`
    <div class="config-section">
      <h4>Basic Information</h4>
      <div class="agent-basic-info">
        ${basicInfoHtml}
      </div>
    </div>
  `);

  // Capabilities section
  if (agent.capabilities && agent.capabilities.length > 0) {
    const capabilitiesHtml = agent.capabilities.map(cap => 
      `<span class="capability-tag">${cap}</span>`
    ).join("");
    
    sections.push(`
      <div class="config-section">
        <h4>Capabilities</h4>
        <div class="agent-capabilities-list">
          ${capabilitiesHtml}
        </div>
      </div>
    `);
  }

  // Tags section
  if (agent.tags && agent.tags.length > 0) {
    const tagsHtml = agent.tags.map(tag => 
      `<span class="tag-item">${tag}</span>`
    ).join("");
    
    sections.push(`
      <div class="config-section">
        <h4>Tags</h4>
        <div class="agent-tags-list">
          ${tagsHtml}
        </div>
      </div>
    `);
  }

  // Memory configuration
  if (agent.memory) {
    const memoryHtml = Object.entries(agent.memory).map(([key, value]) => `
      <div class="config-item">
        <span class="config-key">${formatConfigKey(key)}</span>
        <span class="config-value">${formatConfigValue(value)}</span>
      </div>
    `).join("");

    sections.push(`
      <div class="config-section">
        <h4>Memory Configuration</h4>
        <div class="nested-config">
          ${memoryHtml}
        </div>
      </div>
    `);
  }

  // Settings configuration
  if (agent.settings) {
    const settingsHtml = Object.entries(agent.settings).map(([key, value]) => `
      <div class="config-item">
        <span class="config-key">${formatConfigKey(key)}</span>
        <span class="config-value">${formatConfigValue(value)}</span>
      </div>
    `).join("");

    sections.push(`
      <div class="config-section">
        <h4>Agent Settings</h4>
        <div class="nested-config">
          ${settingsHtml}
        </div>
      </div>
    `);
  }

  return `
    <div class="agent-config-details">
      ${sections.join("")}
    </div>
  `;
}

// Format configuration key for display
function formatConfigKey(key) {
  return key.split("_").map(word => 
    word.charAt(0).toUpperCase() + word.slice(1)
  ).join(" ");
}

// Format configuration value for display
function formatConfigValue(value) {
  if (value === null || value === undefined) {
    return "null";
  }
  
  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }
  
  if (typeof value === "number") {
    return value.toString();
  }
  
  if (typeof value === "string") {
    return `"${value}"`;
  }
  
  if (Array.isArray(value)) {
    if (value.length === 0) {
      return "[]";
    }
    if (typeof value[0] === "string") {
      return `[${value.map(v => `"${v}"`).join(", ")}]`;
    }
    return `[${value.join(", ")}]`;
  }
  
  if (typeof value === "object") {
    return JSON.stringify(value, null, 2);
  }
  
  return String(value);
}

// Render configuration error state
function renderConfigurationError() {
  const containers = ["#global-settings", "#default-queries-config", "#agent-config"];
  containers.forEach(selector => {
    const container = $(selector);
    if (container) {
      container.innerHTML = "<div class=\"loading-indicator\">Failed to load configuration. Please try again.</div>";
    }
  });
}

// Load agents from the API
async function loadAgents() {
  try {
    const response = await fetch("/api/agents");
    const data = await response.json();

    if (data.agents && data.agents.length > 0) {
      state.agents = data.agents;
      // Set GitHub agent as active if none selected, fallback to first agent
      if (!state.activeAgentId) {
        const githubAgent = state.agents.find(agent => agent.id === "github");
        state.activeAgentId = githubAgent ? githubAgent.id : state.agents[0].id;
      }
    } else {
      // Fallback to a default agent if none loaded
      state.agents = [
        {
          id: "github",
          name: "GitHub Agent",
          description: "GitHub operations agent",
          capabilities: ["Branch Management", "PR Creation", "Repository Operations"],
          tags: ["github"],
          endpoint: "/query",
          port: 8128,
        },
      ];
      state.activeAgentId = "github";
    }

    renderAgents();
    renderAgentCard();
  } catch (error) {
    // Use fallback agent
    state.agents = [
      {
        id: "github",
        name: "GitHub Agent",
        description: "GitHub operations agent",
        capabilities: ["Branch Management", "PR Creation", "Repository Operations"],
        tags: ["github"],
        endpoint: "/query",
        port: 8128,
      },
    ];
    state.activeAgentId = "github";
    renderAgents();
    renderAgentCard();
  }
}

function renderAgents() {
  const list = $("#agent-list");
  list.innerHTML = "";
  state.agents.forEach((a) => {
    const li = document.createElement("li");

    // Create tag badges
    const tagBadges = a.tags
      ? a.tags.map((tag) => `<span class="tag-badge">${tag}</span>`).join(" ")
      : "";

    // Get agent icon
    const agentIcon = getAgentIcon(a.id);

    li.innerHTML = `
      <div class="agent-item">
        <div class="agent-name">${agentIcon} ${a.name}</div>
        <div class="agent-tags">${tagBadges}</div>
        <div class="agent-desc">${a.description}</div>
      </div>
    `;
    li.classList.toggle("active", a.id === state.activeAgentId);
    li.onclick = () => selectAgent(a.id);
    list.appendChild(li);
  });
}

function renderAgentCard() {
  const card = $("#agent-card");
  const agent = state.agents.find((a) => a.id === state.activeAgentId);
  if (!agent) {
    card.classList.add("hidden");
    return;
  }
  card.classList.remove("hidden");

  // Get agent icon
  const agentIcon = getAgentIcon(agent.id);

  // Update the header with agent name and status
  const agentName = $("#agent-name");
  const agentStatus = $("#agent-status");
  if (agentName) agentName.textContent = `${agentIcon} ${agent.name}`;
  if (agentStatus) agentStatus.textContent = "Active";

  // Update the content area
  const content = $("#agent-card-content");
  if (!content) return;

  const capabilitiesBadges = agent.capabilities
    ? agent.capabilities
      .map((cap) => `<span class="capability-badge">${cap}</span>`)
      .join("")
    : "";

  const tagBadges = agent.tags
    ? agent.tags.map((tag) => `<span class="tag-badge">${tag}</span>`).join("")
    : "";

  content.innerHTML = `
    <div class="agent-description">${agent.description}</div>
    <div class="agent-config">
      <div class="config-row"><span>Port:</span> <code>${agent.port}</code></div>
      <div class="config-row"><span>Endpoint:</span> <code>${agent.endpoint}</code></div>
      <div class="config-row"><span>Agent ID:</span> <code>${agent.id}</code></div>
    </div>
    ${
  tagBadges
    ? `<div class="agent-tags-section">
      <div class="tags-label">Tags:</div>
      <div class="tags-list">${tagBadges}</div>
    </div>`
    : ""
}
    ${
  capabilitiesBadges
    ? `<div class="agent-capabilities">
      <div class="capabilities-label">Capabilities:</div>
      <div class="capabilities-list">${capabilitiesBadges}</div>
    </div>`
    : ""
}
  `;
}

function renderChats() {
  const list = $("#chat-list");
  list.innerHTML = "";

  // Filter chats for the current agent
  const agentChats = state.chats.filter(
    (chat) => chat.agentId === state.activeAgentId,
  );

  agentChats.forEach((c) => {
    const li = document.createElement("li");
    li.classList.toggle("active", c.id === state.activeChatId);

    const chatItem = document.createElement("div");
    chatItem.className = "chat-item";

    const chatContent = document.createElement("div");
    chatContent.className = "chat-content";

    const chatTitle = document.createElement("div");
    chatTitle.className = "chat-title";
    chatTitle.textContent = c.title;
    chatTitle.addEventListener("dblclick", () => editChatTitle(c.id));

    const chatMeta = document.createElement("div");
    chatMeta.className = "chat-meta";
    chatMeta.textContent = `${c.messages.length} messages`;

    const deleteButton = document.createElement("button");
    deleteButton.className = "chat-delete";
    deleteButton.innerHTML = "🗑️";
    deleteButton.title = "Delete chat";
    deleteButton.addEventListener("click", (e) => {
      e.stopPropagation(); // Prevent chat selection
      deleteChat(c.id);
    });

    chatContent.appendChild(chatTitle);
    chatContent.appendChild(chatMeta);
    chatItem.appendChild(chatContent);
    chatItem.appendChild(deleteButton);
    li.appendChild(chatItem);

    li.onclick = () => selectChat(c.id);
    list.appendChild(li);
  });
}

function createNewChat() {
  const agent = state.agents.find((a) => a.id === state.activeAgentId);
  const agentName = agent ? agent.name : "Agent";
  state.chatCounter++;

  const newChat = {
    id: `chat-${Date.now()}`,
    title: `${agentName} Chat ${state.chatCounter}`,
    agentId: state.activeAgentId,
    messages: [],
    createdAt: new Date().toISOString(),
  };

  state.chats.unshift(newChat);
  state.activeChatId = newChat.id;
  return newChat;
}

function ensureActiveChat() {
  // Filter chats for current agent
  const agentChats = state.chats.filter(
    (chat) => chat.agentId === state.activeAgentId,
  );

  if (agentChats.length === 0) {
    createNewChat();
  } else if (
    !state.activeChatId ||
    !agentChats.find((c) => c.id === state.activeChatId)
  ) {
    // Select the first chat for this agent if no active chat or active chat doesn't belong to this agent
    state.activeChatId = agentChats[0].id;
  }
}

function getActiveChat() {
  // Get the active chat, ensuring it belongs to the current agent
  const agentChats = state.chats.filter(
    (chat) => chat.agentId === state.activeAgentId,
  );
  return agentChats.find((c) => c.id === state.activeChatId) || agentChats[0];
}

function processMessageContent(content, responseType = null) {
  // If responseType is provided, use it directly instead of auto-detection
  if (responseType) {
    switch (responseType.toLowerCase()) {
    case "markdown":
      return renderMarkdown(content);
    case "json":
      try {
        const parsed = JSON.parse(content);
        const formatted = JSON.stringify(parsed, null, 2);
        return `<div class="code-block">
            <div class="code-block-header">JSON</div>
            <pre class="language-json"><code class="language-json">${escapeHtml(formatted)}</code></pre>
          </div>`;
      } catch (e) {
        // Fall back to text if JSON parsing fails
        return escapeHtml(content);
      }
    case "python":
      return `<div class="code-block">
          <div class="code-block-header">PYTHON</div>
          <pre class="language-python"><code class="language-python">${escapeHtml(content)}</code></pre>
        </div>`;
    case "yaml":
      return `<div class="code-block">
          <div class="code-block-header">YAML</div>
          <pre class="language-yaml"><code class="language-yaml">${escapeHtml(content)}</code></pre>
        </div>`;
    case "text":
    default:
      return escapeHtml(content);
    }
  }

  // Fallback to auto-detection if no responseType is provided
  const codeBlockRegex = /```(\w+)?\n?([\s\S]*?)```/g;
  let processedContent = escapeHtml(content);

  // Replace code blocks with syntax-highlighted versions
  processedContent = processedContent.replace(
    codeBlockRegex,
    (match, language, code) => {
      const lang = language || detectLanguage(code.trim());
      const langClass = lang ? `language-${lang}` : "";
      const langLabel = lang ? lang.toUpperCase() : "CODE";

      return `<div class="code-block">
      <div class="code-block-header">${langLabel}</div>
      <pre class="${langClass}"><code class="${langClass}">${code.trim()}</code></pre>
    </div>`;
    },
  );

  // Handle inline code
  processedContent = processedContent.replace(/`([^`]+)`/g, "<code>$1</code>");

  // Auto-detect JSON responses (common in API responses)
  if (isLikelyJSON(content)) {
    try {
      const parsed = JSON.parse(content);
      const formatted = JSON.stringify(parsed, null, 2);
      return `<div class="code-block">
        <div class="code-block-header">JSON</div>
        <pre class="language-json"><code class="language-json">${escapeHtml(formatted)}</code></pre>
      </div>`;
    } catch (e) {
      // Not valid JSON, continue with normal processing
    }
  }

  // Auto-detect YAML responses
  if (isLikelyYAML(content)) {
    return `<div class="code-block">
      <div class="code-block-header">YAML</div>
      <pre class="language-yaml"><code class="language-yaml">${escapeHtml(content)}</code></pre>
    </div>`;
  }

  // Auto-detect Python code responses
  if (isLikelyPython(content)) {
    return `<div class="code-block">
      <div class="code-block-header">PYTHON</div>
      <pre class="language-python"><code class="language-python">${escapeHtml(content)}</code></pre>
    </div>`;
  }

  // Auto-detect and render Markdown content
  if (isLikelyMarkdown(content)) {
    return renderMarkdown(content);
  }

  return processedContent;
}

function detectLanguage(code) {
  // Simple language detection based on common patterns
  if (
    code.includes("def ") ||
    code.includes("import ") ||
    code.includes("from ") ||
    code.includes("print(")
  ) {
    return "python";
  }
  if (
    code.includes("function ") ||
    code.includes("const ") ||
    code.includes("let ") ||
    code.includes("var ")
  ) {
    return "javascript";
  }
  if (
    code.includes("SELECT ") ||
    code.includes("INSERT ") ||
    code.includes("UPDATE ") ||
    code.includes("DELETE ")
  ) {
    return "sql";
  }
  if (
    code.includes("#!/bin/") ||
    code.includes("echo ") ||
    code.includes("grep ")
  ) {
    return "bash";
  }
  if (code.trim().startsWith("{") && code.trim().endsWith("}")) {
    return "json";
  }
  if (code.includes("---") || (code.includes(": ") && code.includes("  "))) {
    return "yaml";
  }
  if (
    code.includes("# ") ||
    code.includes("## ") ||
    code.includes("### ") ||
    code.includes("- ") ||
    code.includes("* ")
  ) {
    return "markdown";
  }
  return "";
}

function isLikelyJSON(content) {
  const trimmed = content.trim();
  return (
    (trimmed.startsWith("{") && trimmed.endsWith("}")) ||
    (trimmed.startsWith("[") && trimmed.endsWith("]"))
  );
}

function isLikelyYAML(content) {
  const lines = content.trim().split("\n");
  return (
    lines.some((line) => /^\s*\w+:\s*/.test(line)) || content.includes("---")
  );
}

function isLikelyPython(content) {
  const pythonKeywords = [
    "def ",
    "class ",
    "import ",
    "from ",
    "if __name__",
    "print(",
    "return ",
  ];
  
  // More specific Python detection - look for actual Python code patterns
  const pythonPatterns = [
    /^def\s+\w+\s*\(/, // Function definition
    /^class\s+\w+/, // Class definition
    /^import\s+/, // Import statement
    /^from\s+\w+\s+import/, // From import statement
    /if\s+__name__\s*==\s*["']__main__["']/, // Main guard
    /print\s*\(/, // Print function
    /return\s+/, // Return statement
    /^\s*#.*$/m, // Python comments
    /^\s*[a-zA-Z_]\w*\s*=\s*/, // Variable assignment
  ];
  
  // Check if content has multiple Python patterns or starts with Python code
  const patternMatches = pythonPatterns.filter((pattern) => pattern.test(content)).length;
  const keywordMatches = pythonKeywords.filter((keyword) => content.includes(keyword)).length;
  
  // Require more specific patterns for Python detection
  return patternMatches >= 2 || (keywordMatches >= 3 && content.trim().startsWith("def "));
}

function isLikelyMarkdown(content) {
  const markdownPatterns = [
    /^#{1,6}\s+/m, // Headers
    /^\s*[-*+]\s+/m, // Unordered lists
    /^\s*\d+\.\s+/m, // Ordered lists
    /\*\*[^*]+\*\*/, // Bold text
    /\*[^*]+\*/, // Italic text
    /`[^`]+`/, // Inline code
    /\[.+\]\(.+\)/, // Links
    /^\s*>/m, // Blockquotes
  ];

  // Check if content has multiple markdown patterns
  const matchCount = markdownPatterns.filter((pattern) =>
    pattern.test(content),
  ).length;
  
  // Special case for GitHub agent status format
  if (content.includes("GitHub Agent Status:") && content.includes("- ") && content.includes(":")) {
    return true;
  }
  
  return (
    matchCount >= 2 ||
    content.includes("###") ||
    (content.includes("**") && content.includes("- "))
  );
}

function renderMarkdown(content) {
  // Simple markdown to HTML conversion
  let html = escapeHtml(content);

  // Headers
  html = html.replace(/^### (.+)$/gm, "<h3>$1</h3>");
  html = html.replace(/^## (.+)$/gm, "<h2>$1</h2>");
  html = html.replace(/^# (.+)$/gm, "<h1>$1</h1>");

  // Bold and italic
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");

  // Code blocks (already handled separately)
  // Inline code
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");

  // Lists
  html = html.replace(/^(\s*)[-*+]\s+(.+)$/gm, "$1• $2");
  html = html.replace(/^(\s*)\d+\.\s+(.+)$/gm, "$1$2");

  // Line breaks
  html = html.replace(/\n\n/g, "</p><p>");
  html = html.replace(/\n/g, "<br>");

  // Wrap in paragraphs
  if (
    !html.includes("<h1>") &&
    !html.includes("<h2>") &&
    !html.includes("<h3>")
  ) {
    html = "<p>" + html + "</p>";
  }

  return html;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// Utility function to scroll chat to bottom
function scrollToBottom() {
  const container = $("#chat");
  if (container) {
    // Use scrollIntoView for smoother scrolling
    container.scrollTop = container.scrollHeight;
    
    // Also focus on input for immediate interaction
    const input = $("#input");
    if (input) {
      input.focus();
    }
  }
}

// Save current scroll position for the active chat
function saveScrollPosition() {
  const container = $("#chat");
  const chat = getActiveChat();
  if (container && chat) {
    const scrollTop = container.scrollTop;
    state.chatScrollPositions[chat.id] = scrollTop;
  }
}

// Restore scroll position for the active chat
function restoreScrollPosition() {
  const container = $("#chat");
  const chat = getActiveChat();
  if (container && chat && state.chatScrollPositions[chat.id] !== undefined) {
    const savedPosition = state.chatScrollPositions[chat.id];
    container.scrollTop = savedPosition;
  } else {
    // If no saved position, scroll to bottom
    scrollToBottom();
  }
}

function renderMessages(forceScrollToBottom = false) {
  ensureActiveChat();
  const chat = getActiveChat();
  const container = $("#chat");
  container.innerHTML = "";

  if (chat && chat.messages) {
    chat.messages.forEach((m, index) => {
      const div = document.createElement("div");
      div.className = `msg ${m.role}`;

      // Process the content for syntax highlighting
      const processedContent = processMessageContent(m.content, m.responseType);
      
      // Add repeat button for user messages only
      if (m.role === "user") {
        div.innerHTML = `
          <div class="msg-content">
            ${processedContent}
          </div>
          <button class="repeat-btn" title="Repeat this message" onclick="repeatMessage(${index})">
            🔄
          </button>
        `;
      } else {
        div.innerHTML = processedContent;
      }

      container.appendChild(div);
    });
  }

  // Restore scroll position after DOM is fully rendered, unless we want to force scroll to bottom
  setTimeout(() => {
    if (forceScrollToBottom) {
      scrollToBottom();
    } else {
      restoreScrollPosition();
    }
  }, 50);

  // Apply syntax highlighting after a brief delay
  setTimeout(() => {
    // eslint-disable-next-line no-undef
    if (typeof Prism !== "undefined") {
      // eslint-disable-next-line no-undef
      Prism.highlightAllUnder(container);
    }
  }, 10);

  // Show typing indicator if agent is responding
  if (state.isTyping) {
    const chat = getActiveChat();
    const targetAgentId = chat.agentId || state.activeAgentId;
    const targetAgent = state.agents.find((a) => a.id === targetAgentId);
    const agentName = targetAgent ? targetAgent.name : "Agent";
    const agentIcon = getAgentIcon(targetAgentId);
    
    const typingDiv = document.createElement("div");
    typingDiv.className = "msg assistant typing-indicator";
    typingDiv.innerHTML = `
      <div class="msg-content">
        <span>${agentIcon} ${agentName} is responding</span>
        <div class="typing-dots">
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
        </div>
      </div>
    `;
    container.appendChild(typingDiv);
    
    // Always scroll to show typing indicator
    scrollToBottom();
  }
}

async function sendMessage(text) {
  ensureActiveChat();
  const chat = getActiveChat();
  
  // Determine which agent this conversation belongs to
  let targetAgentId = state.activeAgentId; // Default to currently selected agent
  
  // If this is a new conversation or we can determine the agent from context
  if (chat.messages.length === 0) {
    // New conversation - use the currently selected agent
    targetAgentId = state.activeAgentId;
    chat.agentId = targetAgentId; // Store which agent this chat belongs to
  } else {
    // Existing conversation - use the agent this chat belongs to
    targetAgentId = chat.agentId || state.activeAgentId;
  }
  
  chat.messages.push({ 
    role: "user", 
    content: text,
    timestamp: new Date().toISOString()
  });
  renderMessages(true); // Force scroll to bottom
  renderChats(); // Update chat list to show new message count

  // Show typing indicator
  state.isTyping = true;
  renderMessages(true); // Force scroll to bottom

  try {
    // Get the target agent's port
    const targetAgent = state.agents.find((a) => a.id === targetAgentId);
    const agentPort = targetAgent ? targetAgent.port : 8123;

    const protocol = window.location.protocol;
    const host = window.location.hostname;
    const url = `${protocol}//${host}:${agentPort}/query`;

    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: text }),
    });
    const data = await res.json();

    // Handle different response formats from different agents
    let reply;
    let responseType = "text"; // default
    
    if (typeof data.response === "string") {
      reply = data.response;
      // Use response_type from metadata if available, otherwise from direct field, otherwise auto-detect
      responseType = data.metadata?.response_type || data.response_type || "text";
    } else if (data.response?.summary) {
      reply = data.response.summary;
      responseType = "text";
    } else if (data.response) {
      reply = JSON.stringify(data.response, null, 2);
      responseType = "json";
    } else {
      reply = "No response received";
      responseType = "text";
    }

    chat.messages.push({
      role: "assistant",
      content: reply,
      responseType: responseType, // Store the response type
      agent: targetAgent ? targetAgent.name : "Unknown Agent",
      timestamp: new Date().toISOString()
    });
  } catch (e) {
    chat.messages.push({ 
      role: "assistant", 
      content: `Error: ${e.message}`,
      timestamp: new Date().toISOString()
    });
  } finally {
    // Hide typing indicator
    state.isTyping = false;
  }
  
  renderMessages(true); // Force scroll to bottom
  renderChats(); // Update chat list again
}

// Function to repeat a message by its index
// eslint-disable-next-line no-unused-vars
async function repeatMessage(messageIndex) {
  const chat = getActiveChat();
  if (chat && chat.messages && chat.messages[messageIndex]) {
    const message = chat.messages[messageIndex];
    if (message.role === "user") {
      await sendMessage(message.content);
    }
  }
}



function selectAgent(id) {
  // Save current scroll position before switching
  saveScrollPosition();
  
  state.activeAgentId = id;

  // Filter chats for this agent or create a new chat if none exist
  const agentChats = state.chats.filter((chat) => chat.agentId === id);

  if (agentChats.length > 0) {
    // Switch to the most recent chat for this agent
    const mostRecentChat = agentChats.sort(
      (a, b) => new Date(b.createdAt) - new Date(a.createdAt),
    )[0];
    state.activeChatId = mostRecentChat.id;
  } else {
    // Create a new chat for this agent
    createNewChat();
  }

  renderAgentCard();
  renderAgents(); // Re-render to update active styling
  renderChats(); // Update chat list to show agent-specific chats
  renderMessages(); // Load messages for the selected chat
  saveState();

  // Focus on input for immediate interaction
  setTimeout(() => {
    const input = $("#input");
    if (input) {
      input.focus();
    }
  }, 50);
}

function selectChat(chatId) {
  // Save current scroll position before switching
  saveScrollPosition();
  
  state.activeChatId = chatId;
  renderMessages();
  renderChats(); // Update active styling

  // Focus on input for immediate interaction
  setTimeout(() => {
    const input = $("#input");
    if (input) {
      input.focus();
    }
  }, 25);
}

function editChatTitle(chatId) {
  const chat = state.chats.find((c) => c.id === chatId);
  if (!chat) return;

  const newTitle = prompt("Enter new chat title:", chat.title);
  if (newTitle && newTitle.trim()) {
    chat.title = newTitle.trim();
    renderChats();
    saveState(); // Save immediately after rename
  }
}

function deleteChat(chatId) {
  const chat = state.chats.find((c) => c.id === chatId);
  if (!chat) return;

  const confirmMessage = `Delete "${chat.title}"?\n\nThis will permanently remove the chat and all ${chat.messages.length} messages. This cannot be undone.`;
  if (confirm(confirmMessage)) {
    // Remove the chat from the array
    state.chats = state.chats.filter((c) => c.id !== chatId);

    // If this was the active chat, select another one or create new
    if (state.activeChatId === chatId) {
      if (state.chats.length > 0) {
        state.activeChatId = state.chats[0].id;
      } else {
        state.activeChatId = null;
        createNewChat(); // Create a new chat if no chats remain
      }
    }

    renderChats();
    renderMessages();
    saveState(); // Save immediately after deletion
  }
}

function bindEvents() {
  $("#composer").addEventListener("submit", (e) => {
    e.preventDefault();
    const input = $("#input");
    const value = input.value.trim();
    if (!value) return;
    input.value = "";
    sendMessage(value);
  });

  // Recent messages functionality
  const recentBtn = $("#recent-btn");
  const recentPanel = $("#recent-panel");
  const recentClose = $("#recent-close");

  if (recentBtn) {
    recentBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      showRecentMessages();
    });
  }

  if (recentClose) {
    recentClose.addEventListener("click", (e) => {
      e.stopPropagation();
      hideRecentMessages();
    });
  }

  // Click outside to dismiss recent panel
  document.addEventListener("click", (e) => {
    if (recentPanel && recentPanel.getAttribute("aria-hidden") !== "true") {
      if (!recentPanel.contains(e.target) && !recentBtn.contains(e.target)) {
        hideRecentMessages();
      }
    }
  });

  // Prevent clicks inside recent panel from closing it
  if (recentPanel) {
    recentPanel.addEventListener("click", (e) => {
      e.stopPropagation();
    });
  }

  // Close recent panel with Escape key
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && recentPanel && recentPanel.getAttribute("aria-hidden") !== "true") {
      hideRecentMessages();
    }
  });

  // Add scroll event listener to save scroll positions
  const chatContainer = $("#chat");
  if (chatContainer) {
    chatContainer.addEventListener("scroll", () => {
      // Debounce scroll events to avoid too many saves
      clearTimeout(chatContainer.scrollTimeout);
      chatContainer.scrollTimeout = setTimeout(() => {
        saveScrollPosition();
      }, 100);
    });
  }

  // Hamburger menu
  const burger = $("#hamburger");
  const burgerMenu = $("#hamburger-menu");
  if (burger && burgerMenu) {
    burger.addEventListener("click", () => {
      const isHidden = burgerMenu.getAttribute("aria-hidden") !== "false";
      burgerMenu.setAttribute("aria-hidden", isHidden ? "false" : "true");
    });
    // Close menu when clicking outside
    document.addEventListener("click", (e) => {
      if (!burger.contains(e.target) && !burgerMenu.contains(e.target)) {
        burgerMenu.setAttribute("aria-hidden", "true");
      }
    });
  }

  // Menu actions
  const menuNew = $("#menu-new");
  const menuClear = $("#menu-clear");
  const menuSettings = $("#menu-settings");
  if (menuNew) {
    menuNew.addEventListener("click", () => {
      createNewChat();
      renderChats();
      renderMessages();
      saveState();
      // Remove focus from the button before hiding the menu
      menuNew.blur();
      burgerMenu.setAttribute("aria-hidden", "true");
      // Ensure scroll to bottom for new chat
      setTimeout(() => {
        scrollToBottom();
      }, 25);
    });
  }

  // New chat button in left pane
  const newChatBtn = $("#new-chat-btn");
  if (newChatBtn) {
    newChatBtn.addEventListener("click", () => {
      createNewChat();
      renderChats();
      renderMessages();
      saveState();
      // Ensure scroll to bottom for new chat
      setTimeout(() => {
        scrollToBottom();
      }, 25);
    });
  }
  if (menuClear) {
    menuClear.addEventListener("click", () => {
      if (confirm("Clear all chats? This cannot be undone.")) {
        state.chats = [];
        state.activeChatId = null;
        state.chatCounter = 0;
        renderChats();
        renderMessages();
        saveState();
      }
      // Remove focus from the button before hiding the menu
      menuClear.blur();
      burgerMenu.setAttribute("aria-hidden", "true");
    });
  }

  // System Status Panel (gear wheel button)
  const settingsBtn = $("#settings");
  const systemStatusPanel = $("#system-status-panel");
  const systemStatusClose = $("#system-status-close");
  
  function closeSystemStatusPanel() {
    if (systemStatusPanel) {
      systemStatusPanel.setAttribute("aria-hidden", "true");
    }
  }
  
  if (settingsBtn && systemStatusPanel) {
    settingsBtn.addEventListener("click", (e) => {
      e.stopPropagation(); // Prevent event bubbling
      const isHidden = systemStatusPanel.getAttribute("aria-hidden") !== "false";
      systemStatusPanel.setAttribute("aria-hidden", isHidden ? "false" : "true");

      // Check service health when opening system status
      if (isHidden) {
        checkAllServices();
      }
    });
  }
  
  if (systemStatusClose) {
    systemStatusClose.addEventListener("click", (e) => {
      e.stopPropagation(); // Prevent event bubbling
      closeSystemStatusPanel();
    });
  }
  
  // Click outside to dismiss system status panel
  document.addEventListener("click", (e) => {
    if (systemStatusPanel && systemStatusPanel.getAttribute("aria-hidden") !== "true") {
      // Check if click is outside the system status panel
      if (!systemStatusPanel.contains(e.target) && !settingsBtn.contains(e.target)) {
        closeSystemStatusPanel();
      }
    }
  });
  
  // Prevent clicks inside system status panel from closing it
  if (systemStatusPanel) {
    systemStatusPanel.addEventListener("click", (e) => {
      e.stopPropagation();
    });
  }
  
  // Close system status panel with Escape key
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && systemStatusPanel && systemStatusPanel.getAttribute("aria-hidden") !== "true") {
      closeSystemStatusPanel();
    }
  });

  // Vectras Settings Panel (hamburger menu)
  const vectrasSettingsPanel = $("#vectras-settings-panel");
  const vectrasSettingsClose = $("#vectras-settings-close");
  
  function closeVectrasSettingsPanel() {
    if (vectrasSettingsPanel) {
      vectrasSettingsPanel.setAttribute("aria-hidden", "true");
      // Reset inline styles
      vectrasSettingsPanel.style.transform = "";
      vectrasSettingsPanel.style.display = "";
      vectrasSettingsPanel.style.visibility = "";
      vectrasSettingsPanel.style.opacity = "";
    }
  }
  
  if (vectrasSettingsClose) {
    vectrasSettingsClose.addEventListener("click", (e) => {
      e.stopPropagation(); // Prevent event bubbling
      closeVectrasSettingsPanel();
    });
  }
  
  // Click outside to dismiss vectras settings panel
  document.addEventListener("click", (e) => {
    if (vectrasSettingsPanel && vectrasSettingsPanel.getAttribute("aria-hidden") !== "true") {
      // Check if click is outside the vectras settings panel and not on the menu settings button
      if (!vectrasSettingsPanel.contains(e.target) && e.target !== menuSettings) {
        closeVectrasSettingsPanel();
      }
    }
  });
  
  // Prevent clicks inside vectras settings panel from closing it
  if (vectrasSettingsPanel) {
    vectrasSettingsPanel.addEventListener("click", (e) => {
      e.stopPropagation();
    });
  }
  
  // Close vectras settings panel with Escape key
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && vectrasSettingsPanel && vectrasSettingsPanel.getAttribute("aria-hidden") !== "true") {
      closeVectrasSettingsPanel();
    }
  });

  // Menu settings button
  if (menuSettings) {
    menuSettings.addEventListener("click", () => {
      if (vectrasSettingsPanel) {
        vectrasSettingsPanel.setAttribute("aria-hidden", "false");
        // Force the panel to be visible
        vectrasSettingsPanel.style.transform = "translateX(0)";
        vectrasSettingsPanel.style.display = "flex";
        vectrasSettingsPanel.style.visibility = "visible";
        vectrasSettingsPanel.style.opacity = "1";
        
        loadConfiguration(); // Load configuration when opening via menu
        checkAllServices(); // Check health when opening via menu
      }
      // Remove focus from the button before hiding the menu
      menuSettings.blur();
      burgerMenu.setAttribute("aria-hidden", "true");
    });
  }

  // Agent selector in settings
  const agentSelector = $("#agent-selector");
  if (agentSelector) {
    agentSelector.addEventListener("change", (e) => {
      handleAgentSelection(e.target.value);
    });
  }

  // System status toggle in settings
  const systemStatusToggle = $("#toggle-system-status");
  const systemStatusContent = $("#system-status-content");
  if (systemStatusToggle && systemStatusContent) {
    systemStatusToggle.addEventListener("click", () => {
      const isExpanded = systemStatusToggle.getAttribute("aria-expanded") === "true";
      systemStatusToggle.setAttribute("aria-expanded", !isExpanded);
      systemStatusToggle.textContent = isExpanded ? "⌄" : "⌃";
      systemStatusContent.classList.toggle("collapsed", isExpanded);
    });
  }

  // Agent card collapse functionality
  const agentCardToggle = $("#agent-card-toggle");
  const agentCardContent = $("#agent-card-content");

  if (agentCardToggle && agentCardContent) {
    // Apply saved state on initialization
    agentCardContent.classList.toggle("collapsed", state.agentCardCollapsed);
    agentCardToggle.setAttribute("aria-expanded", String(!state.agentCardCollapsed));
    agentCardToggle.textContent = state.agentCardCollapsed ? "⌄" : "⌃";
    agentCardToggle.title = state.agentCardCollapsed ? "Expand agent details" : "Collapse agent details";

    agentCardToggle.addEventListener("click", () => {
      state.agentCardCollapsed = !state.agentCardCollapsed;
      agentCardContent.classList.toggle("collapsed", state.agentCardCollapsed);
      agentCardToggle.setAttribute("aria-expanded", String(!state.agentCardCollapsed));
      agentCardToggle.textContent = state.agentCardCollapsed ? "⌄" : "⌃";
      agentCardToggle.title = state.agentCardCollapsed ? "Expand agent details" : "Collapse agent details";
      saveState(); // Save the collapse state
    });
  }

  // Collapsible panes
  const leftToggle = $("#left-toggle");
  const rightToggle = $("#right-toggle");
  const layout = $("#layout");
  const leftHandle = $("#left-handle");
  const rightHandle = $("#right-handle");
  let leftOpen = true;
  let rightOpen = true;

  function updateColumns() {
    const left = leftOpen ? `${state.leftWidth}px` : "0px";
    const right = rightOpen ? `${state.rightWidth}px` : "0px";
    layout.style.gridTemplateColumns = `${left} 1fr ${right}`;
    if (leftToggle) leftToggle.setAttribute("aria-expanded", String(leftOpen));
    if (rightToggle)
      rightToggle.setAttribute("aria-expanded", String(rightOpen));
    if (leftHandle) leftHandle.classList.toggle("visible", !leftOpen);
    if (rightHandle) rightHandle.classList.toggle("visible", !rightOpen);

    // Update resize handles
    const leftResize = $("#left-resize");
    const rightResize = $("#right-resize");
    if (leftResize)
      leftResize.style.left = leftOpen ? `${state.leftWidth}px` : "0px";
    if (rightResize)
      rightResize.style.right = rightOpen ? `${state.rightWidth}px` : "0px";
  }

  if (leftToggle) {
    leftToggle.addEventListener("click", () => {
      leftOpen = !leftOpen;
      updateColumns();
    });
  }
  if (rightToggle) {
    rightToggle.addEventListener("click", () => {
      rightOpen = !rightOpen;
      updateColumns();
    });
  }
  if (leftHandle) {
    leftHandle.addEventListener("click", () => {
      leftOpen = true;
      updateColumns();
    });
  }
  if (rightHandle) {
    rightHandle.addEventListener("click", () => {
      rightOpen = true;
      updateColumns();
    });
  }

  // Resize functionality
  const leftResize = $("#left-resize");
  const rightResize = $("#right-resize");

  function setupResize(handle, isLeft) {
    if (!handle) return;
    let isResizing = false;

    handle.addEventListener("mousedown", (e) => {
      isResizing = true;
      document.body.style.cursor = "col-resize";
      e.preventDefault();
    });

    document.addEventListener("mousemove", (e) => {
      if (!isResizing) return;

      if (isLeft) {
        const newWidth = Math.max(150, Math.min(500, e.clientX));
        state.leftWidth = newWidth;
      } else {
        const newWidth = Math.max(
          150,
          Math.min(500, window.innerWidth - e.clientX),
        );
        state.rightWidth = newWidth;
      }
      updateColumns();
    });

    document.addEventListener("mouseup", () => {
      if (isResizing) {
        isResizing = false;
        document.body.style.cursor = "";
      }
    });
  }

  setupResize(leftResize, true);
  setupResize(rightResize, false);

  updateColumns();
}

async function init() {
  // Load any saved state from localStorage
  loadState();

  // Set application title from URL params or default
  setApplicationTitle();

  // Load agents from API first
  await loadAgents();

  // Load default queries from config
  await loadDefaultQueries();

  renderChats();
  renderMessages();
  bindEvents();
  bindStatusEvents(); // Bind status panel events

  // Save state periodically
  setInterval(saveState, 5000); // Save every 5 seconds
}

function setApplicationTitle() {
  // Use injected title from server, URL params, or default
  const title =
    window.APP_TITLE ||
    new URLSearchParams(window.location.search).get("title") ||
    "Vectras AI Assistant";
  const brandElement = document.querySelector(".brand");
  if (brandElement) {
    brandElement.textContent = title;
  }
  // Also set the page title
  document.title = title;
}

function saveState() {
  const stateToSave = {
    chats: state.chats,
    activeChatId: state.activeChatId,
    chatCounter: state.chatCounter,
    activeAgentId: state.activeAgentId,
    agentCardCollapsed: state.agentCardCollapsed,
    chatScrollPositions: state.chatScrollPositions, // Save scroll positions
  };
  localStorage.setItem("vectras-state", JSON.stringify(stateToSave));
}

function loadState() {
  try {
    const saved = localStorage.getItem("vectras-state");
    if (saved) {
      const parsedState = JSON.parse(saved);
      state.chats = parsedState.chats || [];
      state.activeChatId = parsedState.activeChatId || null;
      state.chatCounter = parsedState.chatCounter || 0;
      state.activeAgentId = parsedState.activeAgentId || "agent-1";
      state.agentCardCollapsed = parsedState.agentCardCollapsed || false;
      state.chatScrollPositions = parsedState.chatScrollPositions || {}; // Load scroll positions
    }
  } catch (e) {
    // console.warn("Failed to load saved state:", e);
  }
}

// Service Health Checking
async function checkServiceHealth(serviceName, port) {
  try {
    // For now, use direct localhost URLs - CORS should be handled by the services
    const response = await fetch(`http://localhost:${port}/health`, {
      method: "GET",
      mode: "cors", // Explicitly request CORS
      timeout: 3000,
    });

    if (response.ok) {
      const data = await response.json();
      return {
        status: "healthy",
        emoji: "✅",
        details: data,
      };
    } else {
      return {
        status: "unhealthy",
        emoji: "❌",
        details: { error: `HTTP ${response.status}` },
      };
    }
  } catch (error) {
    // Check if it's a CORS error specifically
    if (error.name === "TypeError" && error.message.includes("CORS")) {
      return {
        status: "cors_error",
        emoji: "⚠️",
        details: { error: "CORS blocked" },
      };
    }
    return {
      status: "offline",
      emoji: "🔴",
      details: { error: error.message },
    };
  }
}

async function checkAllServices() {
  const services = [
    { name: "ui", port: 8120, displayName: "🖥️ UI" },
    { name: "api", port: 8121, displayName: "🔌 API" },
    { name: "mcp", port: 8122, displayName: "🔗 MCP" },
    { name: "supervisor", port: 8123, displayName: "👑 Supervisor" },
    { name: "logging-monitor", port: 8124, displayName: "📊 Logging Monitor" },
    { name: "coding", port: 8125, displayName: "🔧 Coding Agent" },
    { name: "linting", port: 8127, displayName: "✅ Linting" },
    { name: "testing", port: 8126, displayName: "🧪 Testing" },
    { name: "github", port: 8128, displayName: "🐙 GitHub" },
  ];

  // Set all services to checking status
  services.forEach((service) => {
    updateServiceStatus(service.name, "checking", "⏳");
  });

  // Check each service
  const healthChecks = services.map(async (service) => {
    const health = await checkServiceHealth(service.name, service.port);
    updateServiceStatus(service.name, health.status, health.emoji);
    return { name: service.name, ...health };
  });

  const results = await Promise.all(healthChecks);

  // Update system info
  updateSystemInfo(results);

  // Store results in state
  state.serviceStatus = results.reduce((acc, result) => {
    acc[result.name] = result;
    return acc;
  }, {});
}

function updateServiceStatus(serviceName, status, emoji) {
  // Update status in both panels
  const statusElements = document.querySelectorAll(
    `[data-service="${serviceName}"]`,
  );
  statusElements.forEach(statusElement => {
    if (statusElement) {
      statusElement.textContent = `${emoji} ${status.charAt(0).toUpperCase() + status.slice(1)}`;
      statusElement.className = `service-status ${status}`;
    }
  });
}

function updateSystemInfo(results) {
  const totalServices = results.length;
  const healthyCount = results.filter((r) => r.status === "healthy").length;
  const lastCheck = new Date().toLocaleTimeString();

  // Update system info in both panels
  const totalElements = [
    document.getElementById("total-services"),
    document.getElementById("total-services-status")
  ];
  const healthyElements = [
    document.getElementById("healthy-count"),
    document.getElementById("healthy-count-status")
  ];
  const lastCheckElements = [
    document.getElementById("last-check"),
    document.getElementById("last-check-status")
  ];

  totalElements.forEach(element => {
    if (element) element.textContent = totalServices;
  });
  healthyElements.forEach(element => {
    if (element) element.textContent = healthyCount;
  });
  lastCheckElements.forEach(element => {
    if (element) element.textContent = lastCheck;
  });
}

function bindStatusEvents() {
  // Bind refresh button for Vectras Settings panel
  const refreshBtn = document.getElementById("refresh-status");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", async () => {
      refreshBtn.disabled = true;
      refreshBtn.textContent = "⏳ Checking...";

      await checkAllServices();

      refreshBtn.disabled = false;
      refreshBtn.textContent = "🔄 Refresh Status";
    });
  }

  // Bind refresh button for System Status panel
  const refreshBtnSystem = document.getElementById("refresh-status-system");
  if (refreshBtnSystem) {
    refreshBtnSystem.addEventListener("click", async () => {
      refreshBtnSystem.disabled = true;
      refreshBtnSystem.textContent = "⏳ Checking...";

      await checkAllServices();

      refreshBtnSystem.disabled = false;
      refreshBtnSystem.textContent = "🔄 Refresh Status";
    });
  }
}

// Default queries for all agents (will be loaded from config)
let DEFAULT_QUERIES = [
  "status",
  "latest actions", 
  "up time"
];

// Load default queries from config
async function loadDefaultQueries() {
  try {
    const response = await fetch("/api/config");
    const data = await response.json();
    if (data.default_queries) {
      DEFAULT_QUERIES = data.default_queries;
    }
  } catch (error) {
    // Failed to load default queries from config, using defaults
  }
}

// Recent messages functionality
function showRecentMessages() {
  const recentPanel = $("#recent-panel");
  const recentMessages = $("#recent-messages");
  const defaultQueries = $("#default-queries");
  
  // Get current chat
  const chat = getActiveChat();
  if (!chat) return;
  
  // Clear previous content
  recentMessages.innerHTML = "";
  defaultQueries.innerHTML = "";
  
  // Get recent user messages (last 5)
  const userMessages = chat.messages
    .filter(m => m.role === "user")
    .slice(-5)
    .reverse(); // Show most recent first
  
  // Populate recent messages
  userMessages.forEach((message) => {
    const messageDiv = document.createElement("div");
    messageDiv.className = "recent-message-item";
    messageDiv.innerHTML = `
      <div class="recent-message-text">${escapeHtml(message.content)}</div>
      <div class="recent-message-time">${formatMessageTime(message.timestamp)}</div>
    `;
    
    messageDiv.addEventListener("click", () => {
      selectRecentMessage(message.content);
    });
    
    recentMessages.appendChild(messageDiv);
  });
  
  // Populate default queries
  DEFAULT_QUERIES.forEach(query => {
    const queryDiv = document.createElement("div");
    queryDiv.className = "default-query-item";
    queryDiv.textContent = query;
    
    queryDiv.addEventListener("click", () => {
      selectRecentMessage(query);
    });
    
    defaultQueries.appendChild(queryDiv);
  });
  
  // Show panel
  recentPanel.setAttribute("aria-hidden", "false");
}

function hideRecentMessages() {
  const recentPanel = $("#recent-panel");
  recentPanel.setAttribute("aria-hidden", "true");
}

function selectRecentMessage(message) {
  const input = $("#input");
  if (input) {
    input.value = message;
    input.focus();
  }
  hideRecentMessages();
}

function formatMessageTime(timestamp) {
  if (!timestamp) return "Just now";
  
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);
  
  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  
  return date.toLocaleDateString();
}

init();
