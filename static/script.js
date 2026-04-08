// DOM Elements
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const extractBtn = document.getElementById('extractBtn');
const imagePreview = document.getElementById('imagePreview');
const pdfLoading = document.getElementById('pdfLoading');
const pdfName = document.getElementById('pdfName');
const boundingBoxes = document.getElementById('boundingBoxes');
const docTypeBadge = document.getElementById('docTypeBadge');
const mainLayout = document.getElementById('mainLayout');
const blocksList = document.getElementById('blocksList');
const markdownContent = document.getElementById('markdownContent');
const fullTextContent = document.getElementById('fullTextContent');
const jsonContent = document.getElementById('jsonContent');
const processingTimeEl = document.getElementById('processingTime');
const loading = document.getElementById('loading');
const loadingText = document.getElementById('loadingText');
const error = document.getElementById('error');
const errorMessage = document.getElementById('errorMessage');
const closeError = document.getElementById('closeError');

let selectedFile = null;
let lastResult = null;
let isPdf = false;
let originalImageWidth = 0;
let originalImageHeight = 0;
let currentHighlight = null;
let groupedBlocks = [];

// Event Listeners
uploadArea.addEventListener('click', () => fileInput.click());
uploadArea.addEventListener('dragover', (e) => { e.preventDefault(); uploadArea.classList.add('dragover'); });
uploadArea.addEventListener('dragleave', () => { uploadArea.classList.remove('dragover'); });
uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) handleFileSelect(e.dataTransfer.files[0]);
});
fileInput.addEventListener('change', (e) => { if (e.target.files.length > 0) handleFileSelect(e.target.files[0]); });
extractBtn.addEventListener('click', extractText);
closeError.addEventListener('click', () => error.style.display = 'none');

function handleFileSelect(file) {
    const allowedImageTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/bmp', 'image/tiff', 'image/webp'];
    const isPdfFile = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
    
    if (!allowedImageTypes.includes(file.type) && !isPdfFile) {
        showError('Invalid file type. Please select an image or PDF file.');
        return;
    }

    isPdf = isPdfFile;
    selectedFile = file;
    extractBtn.disabled = false;
    mainLayout.style.display = 'none';
    docTypeBadge.style.display = 'none';
    imagePreview.style.display = 'none';
    pdfLoading.style.display = 'none';
    pdfName.style.display = 'none';
    clearHighlight();

    if (!isPdf) {
        const reader = new FileReader();
        reader.onload = (e) => {
            imagePreview.src = e.target.result;
            imagePreview.style.display = 'block';
            imagePreview.onload = () => {
                originalImageWidth = imagePreview.naturalWidth;
                originalImageHeight = imagePreview.naturalHeight;
            };
        };
        reader.readAsDataURL(file);
    } else {
        pdfLoading.style.display = 'block';
        const formData = new FormData();
        formData.append('file', file);
        
        fetch('/api/preview', { method: 'POST', body: formData })
            .then(res => {
                if (!res.ok) throw new Error('Preview failed');
                return res.json();
            })
            .then(data => {
                if (data.success && data.preview) {
                    imagePreview.src = data.preview;
                    imagePreview.style.display = 'block';
                    pdfLoading.style.display = 'none';
                    imagePreview.onload = () => {
                        originalImageWidth = imagePreview.naturalWidth;
                        originalImageHeight = imagePreview.naturalHeight;
                    };
                    pdfName.textContent = `📄 ${file.name} (${data.page_count} page${data.page_count > 1 ? 's' : ''})`;
                    pdfName.style.display = 'inline-block';
                }
            })
            .catch(err => {
                console.error('Preview error:', err);
                pdfLoading.style.display = 'none';
                pdfName.textContent = `📄 ${file.name} (preview unavailable)`;
                pdfName.style.display = 'inline-block';
            });
    }
    document.getElementById('previewSection').style.display = 'block';
}

async function extractText() {
    if (!selectedFile) return;

    loading.style.display = 'block';
    loadingText.textContent = '⏳ Processing...';
    mainLayout.style.display = 'none';
    error.style.display = 'none';
    extractBtn.disabled = true;
    extractBtn.textContent = 'Processing...';

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('preprocess', true);

    try {
        const response = await fetch('/api/ocr/finance', { method: 'POST', body: formData });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'OCR processing failed');
        }
        const data = await response.json();
        if (!data.success) throw new Error(data.error || 'Failed to extract text');

        lastResult = data;
        loading.style.display = 'none';
        mainLayout.style.display = 'grid';
        displayResults(data);
    } catch (err) {
        loading.style.display = 'none';
        showError(err.message);
    } finally {
        extractBtn.disabled = false;
        extractBtn.textContent = 'Extract Data';
    }
}

function displayResults(data) {
    const isFinance = data.doc_type && data.doc_type !== 'unknown';
    if (isFinance) {
        docTypeBadge.style.display = 'inline-block';
        docTypeBadge.textContent = `${getDocTypeEmoji(data.doc_type)} ${formatDocType(data.doc_type)} (${data.classification_confidence}%)`;
        docTypeBadge.className = `doc-badge doc-${data.doc_type}`;
    } else {
        docTypeBadge.style.display = 'none';
    }

    if (processingTimeEl && data.processing_time) {
        processingTimeEl.textContent = `⏱ ${data.processing_time}s`;
    }

    // Group blocks by vertical position
    groupedBlocks = groupBlocks(data.blocks || []);
    
    // Render blocks list
    renderBlocksList(groupedBlocks);
    
    // Render markdown (simple format)
    if (data.markdown) {
        markdownContent.innerHTML = formatMarkdown(data.markdown);
    } else {
        markdownContent.innerHTML = '<p class="empty">No text detected</p>';
    }
    
    // Render full text
    fullTextContent.textContent = data.full_text || 'No text detected';
    
    // Render JSON
    jsonContent.textContent = JSON.stringify(data.json || data, null, 2);

    // Draw bounding boxes
    setTimeout(() => {
        drawBoundingBoxes(data.blocks || []);
    }, 200);

    mainLayout.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Group blocks by vertical position (same Y = same group)
function groupBlocks(blocks) {
    if (!blocks.length) return [];
    
    // Return each block as its own group (1 word per block)
    return blocks.map((block, idx) => ({
        id: idx,
        texts: [block.text],
        bboxes: [block.bbox],
        page: block.page || 1
    }));
}

// Render blocks list
function renderBlocksList(groups) {
    if (!groups.length) {
        blocksList.innerHTML = '<p style="color: var(--text-light); text-align: center; padding: 2rem;">No blocks detected</p>';
        return;
    }
    
    blocksList.innerHTML = groups.map((group, idx) => `
        <div class="block-card" data-group-idx="${idx}" 
             onclick="highlightGroup(${idx})" 
             onmouseenter="highlightGroup(${idx})" 
             onmouseleave="unhighlightGroup(${idx})">
            <div class="block-label">Block ${idx + 1} • Page ${group.page}</div>
            <div class="block-text">${escapeHtml(group.texts.join(' '))}</div>
        </div>
    `).join('');
}

// Draw bounding boxes
function drawBoundingBoxes(blocks) {
    try {
        boundingBoxes.innerHTML = '';
        if (!blocks.length) return;

        const displayedWidth = imagePreview.clientWidth;
        const displayedHeight = imagePreview.clientHeight;
        if (!displayedWidth || !displayedHeight) return;

        boundingBoxes.style.width = `${displayedWidth}px`;
        boundingBoxes.style.height = `${displayedHeight}px`;

        blocks.forEach((block, idx) => {
            if (!block.bbox) return;
            const box = document.createElement('div');
            box.className = 'ocr-box';
            box.dataset.blockIdx = idx;
            
            const scaleX = displayedWidth / originalImageWidth;
            const scaleY = displayedHeight / originalImageHeight;
            
            box.style.left = `${block.bbox.x * scaleX}px`;
            box.style.top = `${block.bbox.y * scaleY}px`;
            box.style.width = `${block.bbox.width * scaleX}px`;
            box.style.height = `${block.bbox.height * scaleY}px`;
            
            box.onclick = () => {
                const groupIdx = findGroupForBlock(idx);
                if (groupIdx >= 0) highlightGroup(groupIdx);
            };
            
            boundingBoxes.appendChild(box);
        });
    } catch (err) {
        console.error('Error drawing boxes:', err);
    }
}

// Find group for a block index (now 1:1 mapping since each word is its own block)
function findGroupForBlock(blockIdx) {
    return blockIdx;
}

// Highlight block (both block card and bbox)
window.highlightGroup = function(groupIdx) {
    if (!groupedBlocks[groupIdx]) return;

    // Highlight block card
    document.querySelectorAll('.block-card').forEach(card => card.classList.remove('highlighted'));
    const card = document.querySelector(`[data-group-idx="${groupIdx}"]`);
    if (card) card.classList.add('highlighted');

    // Highlight corresponding bounding box (1:1 mapping now)
    document.querySelectorAll('.ocr-box').forEach(box => box.classList.remove('highlighted'));
    const box = document.querySelector(`[data-block-idx="${groupIdx}"]`);
    if (box) box.classList.add('highlighted');

    currentHighlight = groupIdx;
};

// Unhighlight group
window.unhighlightGroup = function(groupIdx) {
    if (currentHighlight === groupIdx) return;
    
    document.querySelectorAll('.block-card').forEach(card => card.classList.remove('highlighted'));
    document.querySelectorAll('.ocr-box').forEach(box => box.classList.remove('highlighted'));
};

function clearHighlight() {
    document.querySelectorAll('.block-card, .ocr-box').forEach(el => el.classList.remove('highlighted'));
    currentHighlight = null;
}

// View switching
window.switchView = function(viewName) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.toggle('active', btn.dataset.view === viewName));
    document.querySelectorAll('.view-content').forEach(c => c.classList.remove('active'));
    const map = { blocks: 'blocksView', markdown: 'markdownView', fulltext: 'fullTextView', json: 'jsonView' };
    const target = document.getElementById(map[viewName]);
    if (target) target.classList.add('active');
};

// Format markdown to HTML
function formatMarkdown(md) {
    if (!md || md === 'No text detected') return '<p class="empty">No text detected</p>';
    
    // Split by lines
    const lines = md.split('\n');
    let html = '';
    
    for (let line of lines) {
        if (!line.trim()) {
            html += '<br>';
            continue;
        }
        
        // Bold text **text**
        line = line.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        
        html += line + '<br>';
    }
    
    return html;
}

function getDocTypeEmoji(type) {
    return { invoice: '📄', receipt: '🧾', payment_slip: '🏦', tax_invoice: '📋', reimbursement: '💼' }[type] || '📄';
}

function formatDocType(t) { 
    return t.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()); 
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showError(msg) { 
    errorMessage.textContent = msg; 
    error.style.display = 'block'; 
}
