const $ = (s) => document.querySelector(s);

const state = {
  chats: [],
  activeChatId: null,
  chatCounter: 0,
  agents: [
    { 
      id: "agent-1", 
      name: "Vectras Agent", 
      description: "Default Vectras agent with query capabilities and backend health monitoring",
      model: "gpt-4o-mini",
      temperature: 0.2,
      systemPrompt: "You are a helpful assistant for the Vectras platform.",
      capabilities: ["Chat", "Backend Health Check", "System Status"],
      endpoint: "/query"
    },
    { 
      id: "agent-2", 
      name: "Code Assistant", 
      description: "Specialized agent for code review, debugging, and programming assistance",
      model: "gpt-4o-mini",
      temperature: 0.1,
      systemPrompt: "You are an expert programming assistant. Help with code review, debugging, and best practices.",
      capabilities: ["Code Review", "Debugging", "Best Practices", "Documentation"],
      endpoint: "/query",
      disabled: true
    },
    { 
      id: "agent-3", 
      name: "Data Analyst", 
      description: "Agent specialized in data analysis, visualization, and reporting",
      model: "gpt-4o-mini",
      temperature: 0.3,
      systemPrompt: "You are a data analysis expert. Help with data interpretation, visualization suggestions, and reporting.",
      capabilities: ["Data Analysis", "Visualization", "Reporting", "Statistics"],
      endpoint: "/query",
      disabled: true
    }
  ],
  activeAgentId: "agent-1",
  leftWidth: 260,
  rightWidth: 260,
};

function renderAgents() {
  const list = $("#agent-list");
  list.innerHTML = "";
  state.agents.forEach((a) => {
    const li = document.createElement("li");
    li.innerHTML = `
      <div style="font-weight: 600;">${a.name}</div>
      ${a.disabled ? "<div style=\"font-size: 12px; color: var(--muted);\">Coming Soon</div>" : ""}
    `;
    li.classList.toggle("active", a.id === state.activeAgentId);
    if (a.disabled) {
      li.style.opacity = "0.6";
      li.style.cursor = "not-allowed";
    } else {
      li.onclick = () => selectAgent(a.id);
    }
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
  
  const capabilitiesBadges = agent.capabilities.map(cap => 
    `<span class="capability-badge">${cap}</span>`
  ).join("");
  
  card.innerHTML = `
    <div class="agent-header">
      <strong>${agent.name}</strong>
      ${agent.disabled ? "<span class=\"status-badge disabled\">Disabled</span>" : "<span class=\"status-badge active\">Active</span>"}
    </div>
    <div class="agent-description">${agent.description}</div>
    <div class="agent-config">
      <div class="config-row"><span>Model:</span> <code>${agent.model}</code></div>
      <div class="config-row"><span>Temperature:</span> <code>${agent.temperature}</code></div>
      <div class="config-row"><span>Endpoint:</span> <code>${agent.endpoint}</code></div>
    </div>
    <div class="agent-capabilities">
      <div class="capabilities-label">Capabilities:</div>
      <div class="capabilities-list">${capabilitiesBadges}</div>
    </div>
  `;
}

function renderChats() {
  const list = $("#chat-list");
  list.innerHTML = "";
  state.chats.forEach((c) => {
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
  const agent = state.agents.find(a => a.id === state.activeAgentId);
  const agentName = agent ? agent.name : "Agent";
  state.chatCounter++;
  
  const newChat = {
    id: `chat-${Date.now()}`,
    title: `${agentName} Chat ${state.chatCounter}`,
    agentId: state.activeAgentId,
    messages: [],
    createdAt: new Date().toISOString()
  };
  
  state.chats.unshift(newChat);
  state.activeChatId = newChat.id;
  return newChat;
}

function ensureActiveChat() {
  if (state.chats.length === 0) {
    createNewChat();
  } else if (!state.activeChatId || !state.chats.find(c => c.id === state.activeChatId)) {
    // Select the first chat if no active chat or active chat doesn't exist
    state.activeChatId = state.chats[0].id;
  }
}

function getActiveChat() {
  return state.chats.find(c => c.id === state.activeChatId) || state.chats[0];
}

function renderMessages() {
  ensureActiveChat();
  const chat = getActiveChat();
  const container = $("#chat");
  container.innerHTML = "";
  
  if (chat && chat.messages) {
    chat.messages.forEach((m) => {
      const div = document.createElement("div");
      div.className = `msg ${m.role}`;
      div.textContent = m.content;
      container.appendChild(div);
    });
  }
  
  // Auto-scroll to bottom with smooth behavior
  setTimeout(() => {
    container.scrollTop = container.scrollHeight;
  }, 10);
}

async function sendMessage(text) {
  ensureActiveChat();
  const chat = getActiveChat();
  chat.messages.push({ role: "user", content: text });
  renderMessages();
  renderChats(); // Update chat list to show new message count

  try {
    const protocol = window.location.protocol;
    const host = window.location.hostname;
    const agentPort = (new URLSearchParams(window.location.search)).get("agent_port") || "8123";
    const url = `${protocol}//${host}:${agentPort}/query`;
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: text }),
    });
    const data = await res.json();
    const reply = typeof data.response === "string" ? data.response : (data.response?.summary || JSON.stringify(data.response));
    chat.messages.push({ role: "assistant", content: reply });
  } catch (e) {
    chat.messages.push({ role: "assistant", content: `Error: ${e.message}` });
  }
  renderMessages();
  renderChats(); // Update chat list again
}

function selectAgent(id) {
  state.activeAgentId = id;
  renderAgentCard();
  renderAgents(); // Re-render to update active styling
}

function selectChat(chatId) {
  state.activeChatId = chatId;
  renderMessages();
  renderChats(); // Update active styling
}

function editChatTitle(chatId) {
  const chat = state.chats.find(c => c.id === chatId);
  if (!chat) return;
  
  const newTitle = prompt("Enter new chat title:", chat.title);
  if (newTitle && newTitle.trim()) {
    chat.title = newTitle.trim();
    renderChats();
    saveState(); // Save immediately after rename
  }
}

function deleteChat(chatId) {
  const chat = state.chats.find(c => c.id === chatId);
  if (!chat) return;
  
  const confirmMessage = `Delete "${chat.title}"?\n\nThis will permanently remove the chat and all ${chat.messages.length} messages. This cannot be undone.`;
  if (confirm(confirmMessage)) {
    // Remove the chat from the array
    state.chats = state.chats.filter(c => c.id !== chatId);
    
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
  if (menuSettings) {
    menuSettings.addEventListener("click", () => {
      const settingsPanel = $("#settings-panel");
      if (settingsPanel) settingsPanel.setAttribute("aria-hidden", "false");
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
    });
  }
  if (settingsClose) {
    settingsClose.addEventListener("click", () => settingsPanel.setAttribute("aria-hidden", "true"));
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
    if (rightToggle) rightToggle.setAttribute("aria-expanded", String(rightOpen));
    if (leftHandle) leftHandle.classList.toggle("visible", !leftOpen);
    if (rightHandle) rightHandle.classList.toggle("visible", !rightOpen);
    
    // Update resize handles
    const leftResize = $("#left-resize");
    const rightResize = $("#right-resize");
    if (leftResize) leftResize.style.left = leftOpen ? `${state.leftWidth}px` : "0px";
    if (rightResize) rightResize.style.right = rightOpen ? `${state.rightWidth}px` : "0px";
  }
  
  if (leftToggle) {
    leftToggle.addEventListener("click", () => { leftOpen = !leftOpen; updateColumns(); });
  }
  if (rightToggle) {
    rightToggle.addEventListener("click", () => { rightOpen = !rightOpen; updateColumns(); });
  }
  if (leftHandle) {
    leftHandle.addEventListener("click", () => { leftOpen = true; updateColumns(); });
  }
  if (rightHandle) {
    rightHandle.addEventListener("click", () => { rightOpen = true; updateColumns(); });
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
        const newWidth = Math.max(150, Math.min(500, window.innerWidth - e.clientX));
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

function init() {
  // Load any saved state from localStorage
  loadState();
  
  // Set application title from URL params or default
  setApplicationTitle();
  
  renderAgents();
  renderAgentCard();
  renderChats();
  renderMessages();
  bindEvents();
  
  // Save state periodically
  setInterval(saveState, 5000); // Save every 5 seconds
}

function setApplicationTitle() {
  // Use injected title from server, URL params, or default
  const title = window.APP_TITLE || 
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
    activeAgentId: state.activeAgentId
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
    console.warn("Failed to load saved state:", e);
  }
}

init();


