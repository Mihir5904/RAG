document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const loader = document.getElementById('upload-loader');
    const uploadStatus = document.getElementById('upload-status');
    const docsList = document.getElementById('docs-list');
    
    const chatForm = document.getElementById('chat-form');
    const queryInput = document.getElementById('query-input');
    const chatContainer = document.getElementById('chat-container');
    
    const inspectorPanel = document.getElementById('inspector-panel');
    const inspectorContent = document.getElementById('inspector-content');
    const closeInspectorBtn = document.getElementById('close-inspector');

    let currentContexts = null;

    // Load existing documents on startup
    fetchDocuments();

    // -- File Upload Logic --
    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length) {
            handleFileUpload(e.target.files[0]);
        }
    });

    async function handleFileUpload(file) {
        if (file.type !== 'application/pdf') {
            alert('Please upload a valid PDF file.');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        loader.classList.remove('hidden');
        uploadStatus.textContent = 'Processing document...';

        try {
            const res = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            
            if (res.ok) {
                uploadStatus.textContent = `Success: ${data.chunks_processed} chunks added.`;
                setTimeout(() => loader.classList.add('hidden'), 3000);
                fetchDocuments(); // refresh list
            } else {
                throw new Error(data.detail || 'Upload failed');
            }
        } catch (err) {
            console.error(err);
            uploadStatus.textContent = `Error: ${err.message}`;
            setTimeout(() => loader.classList.add('hidden'), 4000);
        }
        
        // Reset file input
        fileInput.value = '';
    }

    // -- Document Management Logic --
    async function fetchDocuments() {
        try {
            const res = await fetch('/api/documents');
            const data = await res.json();
            if (res.ok) {
                renderDocuments(data.documents);
            }
        } catch (err) {
            console.error('Fetch docs error:', err);
        }
    }

    function renderDocuments(documents) {
        docsList.innerHTML = '';
        if (documents.length === 0) {
            docsList.innerHTML = '<li class="doc-item" style="justify-content:center; color: var(--text-secondary);">No documents yet</li>';
            return;
        }

        documents.forEach(doc => {
            const li = document.createElement('li');
            li.className = 'doc-item';
            li.innerHTML = `
                <span class="doc-name" title="${doc}"><i class="fas fa-file-pdf" style="margin-right: 8px; color: #ef4444;"></i>${doc}</span>
                <button class="delete-btn" data-doc="${doc}" title="Delete Context">
                    <i class="fas fa-trash"></i>
                </button>
            `;
            docsList.appendChild(li);
        });

        // Add delete listeners
        document.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const docName = e.currentTarget.getAttribute('data-doc');
                await deleteDocument(docName);
            });
        });
    }

    async function deleteDocument(docName) {
        if (!confirm(`Are you sure you want to delete ${docName}?`)) return;
        
        try {
            const res = await fetch(`/api/documents/${encodeURIComponent(docName)}`, {
                method: 'DELETE'
            });
            if (res.ok) {
                fetchDocuments();
            } else {
                alert('Failed to delete document');
            }
        } catch (err) {
            console.error(err);
        }
    }

    // -- Chat Logic --
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const query = queryInput.value.trim();
        if (!query) return;

        // Append user message
        appendMessage('user', query);
        queryInput.value = '';
        currentContexts = null; // reset contexts
        inspectorPanel.classList.add('hidden');

        // Append loading assistant message
        const loaderId = 'loader-' + Date.now();
        appendMessage('assistant', '<div class="spinner" style="width: 20px; height: 20px;"></div>', loaderId);

        try {
            const res = await fetch('/api/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ question: query, top_k: 3 })
            });
            const data = await res.json();

            // Replace loader with response
            const loaderEl = document.getElementById(loaderId);
            if (loaderEl) loaderEl.remove();

            if (res.ok) {
                currentContexts = data.contexts;
                let htmlContent = marked.parse(data.answer);
                
                // Add sources button if contexts exist
                if (currentContexts && currentContexts.length > 0) {
                    htmlContent += `
                        <div style="margin-top: 10px;">
                            <button class="view-sources-btn" onclick="window.toggleInspector()">
                                <i class="fas fa-language"></i> View EN/ZH Contexts
                            </button>
                        </div>
                    `;
                    populateInspector(currentContexts);
                }
                
                appendMessage('assistant', htmlContent);
            } else {
                throw new Error(data.detail || 'Query failed');
            }
        } catch (err) {
            console.error(err);
            const loaderEl = document.getElementById(loaderId);
            if (loaderEl) loaderEl.remove();
            appendMessage('assistant', `<span style="color: #ef4444;">Error: ${err.message}</span>`);
        }
    });

    function appendMessage(role, content, id = null) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `chat-message ${role}`;
        if (id) msgDiv.id = id;

        const icon = role === 'user' ? 'fa-user' : 'fa-robot';
        
        msgDiv.innerHTML = `
            <div class="avatar"><i class="fas ${icon}"></i></div>
            <div class="message-content">
                ${content}
            </div>
        `;
        
        chatContainer.appendChild(msgDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    // -- Inspector Logic --
    window.toggleInspector = () => {
        inspectorPanel.classList.toggle('hidden');
    };

    closeInspectorBtn.addEventListener('click', () => {
        inspectorPanel.classList.add('hidden');
    });

    function populateInspector(contexts) {
        inspectorContent.innerHTML = '';
        contexts.forEach((ctx, i) => {
            const block = document.createElement('div');
            block.className = 'context-block';
            block.innerHTML = `
                <h5>Chunk ${i + 1} - ${ctx.file_name}</h5>
                <div class="context-text">${ctx.en_text}</div>
                <div class="context-text zh-text">${ctx.zh_text}</div>
            `;
            inspectorContent.appendChild(block);
        });
    }
});
