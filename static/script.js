// DOM Elements
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const extractBtn = document.getElementById('extractBtn');
const previewSection = document.getElementById('previewSection');
const imagePreview = document.getElementById('imagePreview');
const pdfLoading = document.getElementById('pdfLoading');
const pdfName = document.getElementById('pdfName');
const previewWrapper = document.getElementById('previewWrapper');
const highlightOverlay = document.getElementById('highlightOverlay');
const docTypeBadge = document.getElementById('docTypeBadge');
const resultsSection = document.getElementById('resultsSection');
const financeDataGrid = document.getElementById('financeDataGrid');
const validationErrors = document.getElementById('validationErrors');
const fullText = document.getElementById('fullText');
const processingTime = document.getElementById('processingTime');
const loading = document.getElementById('loading');
const loadingText = document.getElementById('loadingText');
const error = document.getElementById('error');
const errorMessage = document.getElementById('errorMessage');
const closeError = document.getElementById('closeError');
const copyBtn = document.getElementById('copyBtn');
const downloadJsonBtn = document.getElementById('downloadJsonBtn');

let selectedFile = null;
let lastResult = null;
let isPdf = false;
let originalImageWidth = 0;
let originalImageHeight = 0;
let currentHighlight = null;

// Event Listeners
uploadArea.addEventListener('click', () => fileInput.click());

uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('dragover');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) {
        handleFileSelect(e.dataTransfer.files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFileSelect(e.target.files[0]);
    }
});

extractBtn.addEventListener('click', extractText);
closeError.addEventListener('click', () => error.style.display = 'none');
copyBtn.addEventListener('click', copyToClipboard);
downloadJsonBtn.addEventListener('click', downloadJson);

function handleFileSelect(file) {
    const allowedImageTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/bmp', 'image/tiff', 'image/webp'];
    const isPdfFile = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
    
    if (!allowedImageTypes.includes(file.type) && !isPdfFile) {
        showError('Invalid file type. Please select an image or PDF file.');
        return;
    }

    // Set global variable
    isPdf = isPdfFile;
    
    selectedFile = file;
    extractBtn.disabled = false;
    resultsSection.style.display = 'none';
    docTypeBadge.style.display = 'none';
    imagePreview.style.display = 'none';
    pdfLoading.style.display = 'none';
    pdfName.style.display = 'none';

    // Clear previous highlight
    clearHighlight();

    if (!isPdf) {
        // For images, show directly with FileReader
        const reader = new FileReader();
        reader.onload = (e) => {
            imagePreview.src = e.target.result;
            imagePreview.style.display = 'block';
            
            // Store original dimensions after image loads
            imagePreview.onload = () => {
                originalImageWidth = imagePreview.naturalWidth;
                originalImageHeight = imagePreview.naturalHeight;
                console.log(`Image loaded: ${originalImageWidth}x${originalImageHeight}`);
            };
        };
        reader.readAsDataURL(file);
    } else {
        // For PDF, fetch preview from server
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
                    
                    // Store preview dimensions after image loads
                    imagePreview.onload = () => {
                        originalImageWidth = imagePreview.naturalWidth;
                        originalImageHeight = imagePreview.naturalHeight;
                        console.log(`PDF preview loaded: ${originalImageWidth}x${originalImageHeight}`);
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
    
    previewSection.style.display = 'block';
}

async function extractText() {
    if (!selectedFile) return;

    // Reset state
    loading.style.display = 'block';
    loadingText.textContent = '⏳ Processing...';
    resultsSection.style.display = 'none';
    error.style.display = 'none';
    extractBtn.disabled = true;
    extractBtn.textContent = 'Processing...';
    clearHighlight();

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('preprocess', true);

    try {
        const response = await fetch('/api/ocr/finance', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'OCR processing failed');
        }

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Failed to extract text');
        }

        lastResult = data;
        
        // Hide loading, show results
        loading.style.display = 'none';
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
    resultsSection.style.display = 'block';

    // Update document type badge
    const isFinance = data.doc_type && data.doc_type !== 'unknown';
    if (isFinance) {
        docTypeBadge.style.display = 'inline-block';
        docTypeBadge.textContent = `${getDocTypeEmoji(data.doc_type)} ${formatDocType(data.doc_type)} (${data.classification_confidence}%)`;
        docTypeBadge.className = `doc-badge doc-${data.doc_type}`;
    } else {
        docTypeBadge.style.display = 'none';
    }

    // Show processing time
    if (data.processing_time) {
        processingTime.textContent = `⏱ ${data.processing_time}s`;
    }

    // Show validation errors if any
    const hasErrors = data.validation_errors && Object.keys(data.validation_errors).length > 0;
    if (hasErrors) {
        validationErrors.style.display = 'block';
        validationErrors.innerHTML = `
            <h4>⚠️ Validation Warnings</h4>
            <ul>
                ${Object.entries(data.validation_errors).flatMap(([field, errors]) => 
                    errors.map(err => `<li><strong>${field}:</strong> ${err}</li>`)
                ).join('')}
            </ul>
        `;
    } else {
        validationErrors.style.display = 'none';
    }

    // Display finance data grid
    const financeData = data.data || {};
    const fields = getFieldsForDocType(data.doc_type, financeData);
    
    if (fields.length > 0) {
        financeDataGrid.style.display = 'grid';
        financeDataGrid.innerHTML = fields
            .filter(f => f.value !== null && f.value !== undefined && f.value !== '')
            .map(f => `
                <div class="finance-data-card">
                    <div class="finance-data-icon">${f.icon}</div>
                    <div class="finance-data-content">
                        <div class="finance-data-label">${f.label}</div>
                        <div class="finance-data-value">${f.value}</div>
                    </div>
                </div>
            `).join('');
    } else {
        financeDataGrid.style.display = 'none';
    }

    // Display results in all 3 views
    const fullTextContent = data.data?.full_text || '';
    const words = data.data?.words || [];
    
    // Store OCR dimensions for proper scaling
    const ocrWidth = data.data?.ocr_width || originalImageWidth;
    const ocrHeight = data.data?.ocr_height || originalImageHeight;
    
    // Full text view
    const fullTextElement = document.getElementById('fullTextContent');
    fullTextElement.textContent = fullTextContent || 'No text detected';
    
    // Markdown view (convert text to markdown format)
    const markdownElement = document.getElementById('markdownContent');
    markdownElement.innerHTML = convertToMarkdown(fullTextContent);
    
    // Blocks view (clickable words)
    const blocksContainer = document.getElementById('blocksContainer');
    if (words.length > 0) {
        blocksContainer.innerHTML = words.map((word, idx) => 
            `<span class="word-block" 
                    data-word-idx="${idx}" 
                    onclick="highlightWordBlock(${idx})"
                    title="Click to highlight">
                ${escapeHtml(word.text)}
             </span>`
        ).join(' ');
    } else {
        blocksContainer.innerHTML = '<p style="color: var(--text-light); text-align: center;">No text detected</p>';
    }

    // Draw bounding boxes on preview (use OCR dimensions for scaling)
    // Wait for image to fully load and layout to complete
    setTimeout(() => {
        drawBoundingBoxes(words, ocrWidth, ocrHeight);
    }, 200);

    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Draw all bounding boxes on image preview
function drawBoundingBoxes(words, ocrWidth, ocrHeight) {
    try {
        const container = document.getElementById('boundingBoxes');
        container.innerHTML = '';
        
        if (!words || words.length === 0) {
            console.log('No words to draw');
            return;
        }
        
        if (!ocrWidth || !ocrHeight) {
            console.warn('OCR dimensions not available');
            return;
        }
        
        // Get the actual displayed image element dimensions
        const img = imagePreview;
        const displayedWidth = img.clientWidth;
        const displayedHeight = img.clientHeight;
        
        if (!displayedWidth || !displayedHeight) {
            console.warn('Image not rendered yet');
            return;
        }
        
        // CRITICAL: Set overlay to exactly match image dimensions
        container.style.width = `${displayedWidth}px`;
        container.style.height = `${displayedHeight}px`;
        container.style.left = '0';
        container.style.top = '0';
        
        // Calculate scale from OCR image to displayed image
        const scaleX = displayedWidth / ocrWidth;
        const scaleY = displayedHeight / ocrHeight;
        
        console.log(`Drawing ${words.length} boxes. OCR: ${ocrWidth}x${ocrHeight}, Displayed: ${displayedWidth}x${displayedHeight}, Scale: ${scaleX.toFixed(3)}x${scaleY.toFixed(3)}`);
        
        // Draw first word's box to verify
        if (words.length > 0) {
            const firstWord = words[0];
            console.log(`First word "${firstWord.text}" - OCR bbox: (${firstWord.bbox.x}, ${firstWord.bbox.y}, ${firstWord.bbox.width}x${firstWord.bbox.height})`);
        }
        
        words.forEach((word, idx) => {
            try {
                const bbox = word.bbox;
                const box = document.createElement('div');
                box.className = 'ocr-box';
                box.dataset.wordIdx = idx;
                
                // Position and size scaled to displayed coordinates
                const left = bbox.x * scaleX;
                const top = bbox.y * scaleY;
                const width = bbox.width * scaleX;
                const height = bbox.height * scaleY;
                
                box.style.left = `${left}px`;
                box.style.top = `${top}px`;
                box.style.width = `${width}px`;
                box.style.height = `${height}px`;
                
                box.title = `${word.text} (${Math.round(word.confidence * 100)}%)`;
                box.onclick = () => highlightWordBlock(idx);
                
                container.appendChild(box);
            } catch (err) {
                console.error(`Error drawing box for word ${idx}:`, err);
            }
        });
        
        console.log(`Successfully drew ${container.children.length} boxes`);
    } catch (err) {
        console.error('Error in drawBoundingBoxes:', err);
    }
}

// Highlight word block (both in Blocks tab and on preview)
window.highlightWordBlock = function(wordIdx) {
    if (!lastResult || !lastResult.data?.words || !lastResult.data.words[wordIdx]) return;
    
    const word = lastResult.data.words[wordIdx];
    
    // Highlight in Blocks tab
    document.querySelectorAll('.word-block').forEach(block => block.classList.remove('active'));
    const clickedBlock = document.querySelector(`[data-word-idx="${wordIdx}"]`);
    if (clickedBlock) clickedBlock.classList.add('active');
    
    // Highlight on preview
    document.querySelectorAll('.ocr-box').forEach(box => box.classList.remove('highlighted'));
    const targetBox = document.querySelector(`.ocr-box[data-word-idx="${wordIdx}"]`);
    if (targetBox) {
        targetBox.classList.add('highlighted');
    }
    
    currentHighlight = wordIdx;
};

// Tab switching
window.switchTab = function(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    
    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    
    const tabMap = {
        'blocks': 'blocksView',
        'markdown': 'markdownView',
        'fulltext': 'fullTextView'
    };
    
    const target = document.getElementById(tabMap[tabName]);
    if (target) target.classList.add('active');
};

// Convert text to markdown with structure detection
function convertToMarkdown(text) {
    if (!text) return '<p>No text detected</p>';
    
    const lines = text.split('\n');
    let markdown = '';
    let inList = false;
    let inParagraph = false;
    let prevLineEmpty = true;
    
    for (let i = 0; i < lines.length; i++) {
        let line = lines[i].trim();
        
        // Skip empty lines
        if (line === '') {
            if (inParagraph) {
                markdown += '</p>';
                inParagraph = false;
            }
            if (inList) {
                markdown += '</ul>';
                inList = false;
            }
            prevLineEmpty = true;
            continue;
        }
        
        // Detect headers (short, uppercase, ends with colon or standalone)
        if (line.length < 80 && isHeader(line, lines, i)) {
            if (inParagraph) {
                markdown += '</p>';
                inParagraph = false;
            }
            if (inList) {
                markdown += '</ul>';
                inList = false;
            }
            
            // Determine header level
            const level = getHeaderLevel(line);
            const tagName = level === 1 ? 'h2' : level === 2 ? 'h3' : 'h4';
            markdown += `<${tagName}>${escapeHtml(line)}</${tagName}>`;
            prevLineEmpty = true;
            continue;
        }
        
        // Detect list items (starts with -, •, *, or number)
        if (/^[\-•*]|\d+[\.\)]/.test(line)) {
            if (inParagraph) {
                markdown += '</p>';
                inParagraph = false;
            }
            if (!inList) {
                markdown += '<ul>';
                inList = true;
            }
            const itemText = line.replace(/^[\-•*]|\d+[\.\)]\s*/, '');
            markdown += `<li>${escapeHtml(itemText)}</li>`;
            prevLineEmpty = false;
            continue;
        }
        
        // Regular text - paragraph
        if (!inParagraph) {
            markdown += '<p>';
            inParagraph = true;
        } else {
            markdown += ' ';
        }
        markdown += escapeHtml(line);
        prevLineEmpty = false;
    }
    
    // Close any open tags
    if (inParagraph) markdown += '</p>';
    if (inList) markdown += '</ul>';
    
    return markdown || '<p>No text detected</p>';
}

// Detect if a line is a header
function isHeader(line, lines, index) {
    // Short lines are more likely to be headers
    if (line.length > 100) return false;
    
    // All caps with some length
    if (line.length > 3 && line === line.toUpperCase() && /[A-Z]/.test(line)) {
        // Check if it's not just a single word
        const words = line.split(/\s+/);
        if (words.length >= 1 && words.length <= 10) {
            return true;
        }
    }
    
    // Ends with colon (like "Invoice Number:")
    if (line.endsWith(':') && line.length < 50) {
        return true;
    }
    
    // Followed by empty line and then content (header pattern)
    if (index + 2 < lines.length && lines[index + 1].trim() === '') {
        return true;
    }
    
    return false;
}

// Get header level based on content
function getHeaderLevel(line) {
    const words = line.split(/\s+/);
    
    // Main headers (1-3 words, very short)
    if (words.length <= 3 && line.length < 30) return 1;
    
    // Subheaders (3-6 words)
    if (words.length <= 6) return 2;
    
    // Minor headers
    return 3;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function getFieldsForDocType(docType, data) {
    switch(docType) {
        case 'invoice':
            return [
                { icon: '🏢', label: 'Vendor', value: data.vendor_name },
                { icon: '📄', label: 'Invoice #', value: data.invoice_number },
                { icon: '📅', label: 'Date', value: data.invoice_date },
                { icon: '💰', label: 'Total', value: data.total ? formatCurrency(data.total, data.currency) : null },
                { icon: '📊', label: 'Subtotal', value: data.subtotal ? formatCurrency(data.subtotal, data.currency) : null },
                { icon: '🧾', label: 'Tax', value: data.tax ? formatCurrency(data.tax, data.currency) : null },
                { icon: '👤', label: 'Bill To', value: data.bill_to },
            ];
        case 'receipt':
            return [
                { icon: '🏪', label: 'Merchant', value: data.merchant_name },
                { icon: '📄', label: 'Receipt #', value: data.receipt_number },
                { icon: '📅', label: 'Date', value: data.date },
                { icon: '💰', label: 'Total', value: data.total ? formatCurrency(data.total, data.currency) : null },
                { icon: '💳', label: 'Payment', value: data.payment_method },
            ];
        case 'payment_slip':
            return [
                { icon: '🏦', label: 'Bank', value: data.bank_name },
                { icon: '📅', label: 'Date', value: data.transfer_date },
                { icon: '👤', label: 'From', value: data.payer_name },
                { icon: '👥', label: 'To', value: data.payee_name },
                { icon: '💰', label: 'Amount', value: data.amount ? formatCurrency(data.amount, data.currency) : null },
            ];
        case 'tax_invoice':
            return [
                { icon: '📄', label: 'Faktur #', value: data.faktur_number },
                { icon: '🏢', label: 'NPWP', value: data.npwp_seller },
                { icon: '👤', label: 'Buyer', value: data.buyer_name },
                { icon: '💰', label: 'DPP', value: data.dpp ? formatCurrency(data.dpp, data.currency) : null },
                { icon: '🧾', label: 'PPN', value: data.ppn_amount ? formatCurrency(data.ppn_amount, data.currency) : null },
            ];
        case 'reimbursement':
            return [
                { icon: '👤', label: 'Employee', value: data.employee_name },
                { icon: '🆔', label: 'Employee ID', value: data.employee_id },
                { icon: '📂', label: 'Type', value: data.expense_type ? formatDocType(data.expense_type) : null },
                { icon: '💰', label: 'Amount', value: data.amount ? formatCurrency(data.amount, data.currency) : null },
            ];
        default:
            return [];
    }
}

function clearHighlight() {
    document.querySelectorAll('.word-block').forEach(block => block.classList.remove('active'));
    document.querySelectorAll('.ocr-box').forEach(box => box.classList.remove('highlighted'));
    currentHighlight = null;
}

function getDocTypeEmoji(docType) {
    const emojis = {
        'invoice': '📄',
        'receipt': '🧾',
        'payment_slip': '🏦',
        'tax_invoice': '📋',
        'reimbursement': '💼'
    };
    return emojis[docType] || '📄';
}

function formatDocType(docType) {
    return docType.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function formatCurrency(amount, currency) {
    const formatted = new Intl.NumberFormat('en-US', { 
        minimumFractionDigits: 2, 
        maximumFractionDigits: 2 
    }).format(amount);
    
    const symbols = { 'USD': '$', 'EUR': '€', 'GBP': '£', 'IDR': 'Rp ', 'JPY': '¥' };
    return (symbols[currency] || '') + formatted;
}

function showError(message) {
    errorMessage.textContent = message;
    error.style.display = 'block';
}

function copyToClipboard() {
    if (!lastResult) return;
    const text = lastResult.data?.full_text || lastResult.full_text || '';
    navigator.clipboard.writeText(text).then(() => {
        const originalText = copyBtn.textContent;
        copyBtn.textContent = '✓ Copied!';
        setTimeout(() => { copyBtn.textContent = '📋 Copy'; }, 2000);
    });
}

function downloadJson() {
    if (!lastResult) return;
    const blob = new Blob([JSON.stringify(lastResult, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ocr_${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
