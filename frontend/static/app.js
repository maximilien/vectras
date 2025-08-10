// SPDX-License-Identifier: MIT
// Copyright (c) 2025 dr.max

const $ = (s) => document.querySelector(s);

const state = {
  chats: [],
  activeChatId: null,
  chatCounter: 0,
  agents: [], // Will be loaded from API
  activeAgentId: null, // Will be set to first available agent
  leftWidth: 260,
  rightWidth: 260,
  serviceStatus: {}, // Store service health status
};

// Load agents from the API
async function loadAgents() {
  try {
    const response = await fetch("/api/agents");
    const data = await response.json();

    if (data.agents && data.agents.length > 0) {
      state.agents = data.agents;
      // Set first agent as active if none selected
      if (!state.activeAgentId) {
        state.activeAgentId = state.agents[0].id;
      }
    } else {
      // Fallback to a default agent if none loaded
      state.agents = [
        {
          id: "supervisor",
          name: "Supervisor Agent",
          description: "Main coordinator agent",
          capabilities: ["Chat", "System Status"],
          tags: ["supervisor"],
          endpoint: "/query",
          port: 8123,
        },
      ];
      state.activeAgentId = "supervisor";
    }

    renderAgents();
    renderAgentCard();
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error("Failed to load agents:", error);
    // Use fallback agent
    state.agents = [
      {
        id: "supervisor",
        name: "Supervisor Agent",
        description: "Main coordinator agent",
        capabilities: ["Chat", "System Status"],
        tags: ["supervisor"],
        endpoint: "/query",
        port: 8123,
      },
    ];
    state.activeAgentId = "supervisor";
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

    li.innerHTML = `
      <div class="agent-item">
        <div class="agent-name">${a.name}</div>
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

  const capabilitiesBadges = agent.capabilities
    ? agent.capabilities
      .map((cap) => `<span class="capability-badge">${cap}</span>`)
      .join("")
    : "";

  const tagBadges = agent.tags
    ? agent.tags.map((tag) => `<span class="tag-badge">${tag}</span>`).join("")
    : "";

  card.innerHTML = `
    <div class="agent-header">
      <strong>${agent.name}</strong>
      <span class="status-badge active">Active</span>
    </div>
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

function processMessageContent(content) {
  // Detect and format different types of code content
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
  return pythonKeywords.some((keyword) => content.includes(keyword));
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

function renderMessages() {
  ensureActiveChat();
  const chat = getActiveChat();
  const container = $("#chat");
  container.innerHTML = "";

  if (chat && chat.messages) {
    chat.messages.forEach((m, index) => {
      const div = document.createElement("div");
      div.className = `msg ${m.role}`;

      // Process the content for syntax highlighting
      const processedContent = processMessageContent(m.content);
      
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

  // Auto-scroll to bottom with smooth behavior
  setTimeout(() => {
    container.scrollTop = container.scrollHeight;

    // Apply syntax highlighting to any code blocks
    // eslint-disable-next-line no-undef
    if (typeof Prism !== "undefined") {
      // eslint-disable-next-line no-undef
      Prism.highlightAllUnder(container);
    }
  }, 10);
}

async function sendMessage(text) {
  ensureActiveChat();
  const chat = getActiveChat();
  chat.messages.push({ role: "user", content: text });
  renderMessages();
  renderChats(); // Update chat list to show new message count

  try {
    // Get the selected agent's port
    const activeAgent = state.agents.find((a) => a.id === state.activeAgentId);
    const agentPort = activeAgent ? activeAgent.port : 8123;

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
    if (typeof data.response === "string") {
      reply = data.response;
    } else if (data.response?.summary) {
      reply = data.response.summary;
    } else if (data.response) {
      reply = JSON.stringify(data.response, null, 2);
    } else {
      reply = "No response received";
    }

    chat.messages.push({
      role: "assistant",
      content: reply,
      agent: activeAgent ? activeAgent.name : "Unknown Agent",
    });
  } catch (e) {
    chat.messages.push({ role: "assistant", content: `Error: ${e.message}` });
  }
  renderMessages();
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

  // Auto-scroll to bottom and focus on input for immediate interaction
  setTimeout(() => {
    const container = $("#chat");
    if (container) {
      container.scrollTop = container.scrollHeight;
    }

    // Focus on the input field for immediate typing
    const input = $("#input");
    if (input) {
      input.focus();
    }
  }, 100); // Small delay to ensure rendering is complete
}

function selectChat(chatId) {
  state.activeChatId = chatId;
  renderMessages();
  renderChats(); // Update active styling

  // Auto-scroll to bottom and focus on input
  setTimeout(() => {
    const container = $("#chat");
    if (container) {
      container.scrollTop = container.scrollHeight;
    }

    const input = $("#input");
    if (input) {
      input.focus();
    }
  }, 50);
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
      burgerMenu.setAttribute("aria-hidden", "true");
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
      burgerMenu.setAttribute("aria-hidden", "true");
    });
  }

  // Settings panel
  const settingsBtn = $("#settings");
  const settingsPanel = $("#settings-panel");
  const settingsClose = $("#settings-close");
  if (settingsBtn && settingsPanel) {
    settingsBtn.addEventListener("click", () => {
      const isHidden = settingsPanel.getAttribute("aria-hidden") !== "false";
      settingsPanel.setAttribute("aria-hidden", isHidden ? "false" : "true");

      // Check service health when opening settings
      if (isHidden) {
        checkAllServices();
      }
    });
  }
  if (settingsClose) {
    settingsClose.addEventListener("click", () =>
      settingsPanel.setAttribute("aria-hidden", "true"),
    );
  }

  // Menu settings button
  if (menuSettings) {
    menuSettings.addEventListener("click", () => {
      const settingsPanel = $("#settings-panel");
      if (settingsPanel) {
        settingsPanel.setAttribute("aria-hidden", "false");
        checkAllServices(); // Check health when opening via menu
      }
      burgerMenu.setAttribute("aria-hidden", "true");
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
    { name: "ui", port: 8120, displayName: "UI" },
    { name: "api", port: 8121, displayName: "API" },
    { name: "mcp", port: 8122, displayName: "MCP" },
    { name: "supervisor", port: 8123, displayName: "Supervisor" },
    { name: "log-monitor", port: 8124, displayName: "Log Monitor" },
    { name: "code-fixer", port: 8125, displayName: "Code Fixer" },
    { name: "linting", port: 8127, displayName: "Linting" },
    { name: "testing", port: 8126, displayName: "Testing" },
    { name: "github", port: 8128, displayName: "GitHub" },
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
  const statusElement = document.querySelector(
    `[data-service="${serviceName}"]`,
  );
  if (statusElement) {
    statusElement.textContent = `${emoji} ${status.charAt(0).toUpperCase() + status.slice(1)}`;
    statusElement.className = `service-status ${status}`;
  }
}

function updateSystemInfo(results) {
  const totalServices = results.length;
  const healthyCount = results.filter((r) => r.status === "healthy").length;
  const lastCheck = new Date().toLocaleTimeString();

  const totalElement = document.getElementById("total-services");
  const healthyElement = document.getElementById("healthy-count");
  const lastCheckElement = document.getElementById("last-check");

  if (totalElement) totalElement.textContent = totalServices;
  if (healthyElement) healthyElement.textContent = healthyCount;
  if (lastCheckElement) lastCheckElement.textContent = lastCheck;
}

function bindStatusEvents() {
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
}

init();
