const chatForm = document.getElementById('chat-form');
const chatInput = document.getElementById('chat-input');
const chatHistory = document.getElementById('chat-history');
const welcomeScreen = document.getElementById('welcome-screen');
const loadingTemplate = document.getElementById('loading-template');
const sendButton = document.getElementById('send-button');

// FastAPI Backend URL
const API_URL = 'http://localhost:8000/ask';

// Auto-scroll to bottom of chat
function scrollToBottom() {
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

// Format source link nicely
function getDomain(url) {
    try {
        const domain = new URL(url).hostname;
        return domain.replace('www.', '');
    } catch {
        return 'Link';
    }
}

// Add a user message to the UI
function addUserMessage(text) {
    if (welcomeScreen) {
        welcomeScreen.style.display = 'none';
    }
    
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message user';
    msgDiv.innerHTML = `
        <div class="avatar user-avatar">
            <svg viewBox="0 0 24 24" fill="none"><path d="M20 21V19C20 17.9391 19.5786 16.9217 18.8284 16.1716C18.0783 15.4214 17.0609 15 16 15H8C6.93913 15 5.92172 15.4214 5.17157 16.1716C4.42143 16.9217 4 17.9391 4 19V21" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M12 11C14.2091 11 16 9.20914 16 7C16 4.79086 14.2091 3 12 3C9.79086 3 8 4.79086 8 7C8 9.20914 9.79086 11 12 11Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </div>
        <div class="message-content">
            <div class="msg-text">${escapeHTML(text)}</div>
        </div>
    `;
    chatHistory.appendChild(msgDiv);
    scrollToBottom();
}

// Add a bot message to the UI
function addBotMessage(data) {
    const isRefusal = !data.last_updated;
    
    const msgDiv = document.createElement('div');
    msgDiv.className = `message bot ${isRefusal ? 'refusal' : ''}`;
    
    let sourceHtml = '';
    if (data.source) {
        const sourceText = isRefusal ? 'AMFI Portal' : 'Official Factsheet';
        sourceHtml = `
            <div class="msg-meta">
                <span class="meta-label">Sources:</span>
                <a href="${data.source}" target="_blank" rel="noopener noreferrer" class="source-pill">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
                        <path d="M10 6H6C4.89543 6 4 6.89543 4 8V18C4 19.1046 4.89543 20 6 20H16C17.1046 20 18 19.1046 18 18V14M14 4H20M20 4V10M20 4L10 14" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                    ${sourceText}
                </a>
            </div>
            ${data.last_updated ? `
            <div class="msg-meta" style="margin-top: 8px;">
                <span class="meta-label">Last updated: ${escapeHTML(data.last_updated)}</span>
                <span class="verified-fact">VERIFIED FACT</span>
            </div>` : ''}
        `;
    }

    msgDiv.innerHTML = `
        <div class="avatar bot-avatar">
            <svg viewBox="0 0 24 24" fill="none">
                <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
                <path d="M2 17L12 22L22 17" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
                <path d="M2 12L12 17L22 12" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
            </svg>
        </div>
        <div class="message-content bot-panel">
            <div class="msg-text">${escapeHTML(data.answer)}</div>
            ${sourceHtml}
        </div>
    `;
    
    chatHistory.appendChild(msgDiv);
    scrollToBottom();
}

// Add loading indicator
function showLoading() {
    const loader = loadingTemplate.content.cloneNode(true);
    chatHistory.appendChild(loader);
    scrollToBottom();
}

// Remove loading indicator
function hideLoading() {
    const loaders = document.querySelectorAll('.message.loading');
    loaders.forEach(l => l.remove());
}

// Utility to escape HTML to prevent XSS
function escapeHTML(str) {
    if (!str) return '';
    return str.replace(/[&<>'"]/g, tag => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
    }[tag] || tag));
}

// Submit a query to the backend
async function handleQuery(query) {
    if (!query.trim()) return;
    
    // UI Updates
    chatInput.value = '';
    sendButton.disabled = true;
    addUserMessage(query);
    showLoading();
    
    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query: query })
        });
        
        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }
        
        const data = await response.json();
        hideLoading();
        addBotMessage(data);
        
    } catch (error) {
        console.error('Error fetching data:', error);
        hideLoading();
        addBotMessage({
            answer: "Sorry, I am currently unable to reach the server. Please ensure the backend API is running.",
            source: null,
            last_updated: null
        });
    } finally {
        sendButton.disabled = false;
        chatInput.focus();
    }
}

// Form submit event handler
chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    handleQuery(chatInput.value);
});

// Example chips global click handler
window.submitExample = function(query) {
    handleQuery(query);
};

// Focus input on load
window.addEventListener('load', () => {
    chatInput.focus();
});
