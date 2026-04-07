// DOM Elements
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const extractBtn = document.getElementById('extractBtn');
const preprocessCheck = document.getElementById('preprocessCheck');
const detailedCheck = document.getElementById('detailedCheck');
const previewSection = document.getElementById('previewSection');
const imagePreview = document.getElementById('imagePreview');
const resultsSection = document.getElementById('resultsSection');
const simpleResult = document.getElementById('simpleResult');
const detailedResult = document.getElementById('detailedResult');
const stats = document.getElementById('stats');
const loading = document.getElementById('loading');
const error = document.getElementById('error');
const errorMessage = document.getElementById('errorMessage');
const closeError = document.getElementById('closeError');
const copyBtn = document.getElementById('copyBtn');
const downloadTxtBtn = document.getElementById('downloadTxtBtn');
const downloadJsonBtn = document.getElementById('downloadJsonBtn');

let selectedFile = null;
let lastResult = null;

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
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFileSelect(files[0]);
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
downloadTxtBtn.addEventListener('click', downloadTxt);
downloadJsonBtn.addEventListener('click', downloadJson);

// Functions
function handleFileSelect(file) {
    // Validate file type
    const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/bmp', 'image/tiff', 'image/webp'];
    
    if (!allowedTypes.includes(file.type)) {
        showError('Invalid file type. Please select an image file.');
        return;
    }
    
    selectedFile = file;
    extractBtn.disabled = false;
    
    // Show preview
    const reader = new FileReader();
    reader.onload = (e) => {
        imagePreview.src = e.target.result;
        previewSection.style.display = 'block';
    };
    reader.readAsDataURL(file);
    
    // Hide previous results
    resultsSection.style.display = 'none';
}

async function extractText() {
    if (!selectedFile) return;
    
    loading.style.display = 'block';
    resultsSection.style.display = 'none';
    error.style.display = 'none';
    extractBtn.disabled = true;
    
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('preprocess', preprocessCheck.checked);
    
    try {
        const endpoint = detailedCheck.checked ? '/api/ocr/json' : '/api/ocr';
        
        const response = await fetch(endpoint, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'OCR processing failed');
        }
        
        const data = await response.json();
        
        if (data.success) {
            lastResult = data;
            displayResults(data);
        } else {
            throw new Error('Failed to extract text');
        }
    } catch (err) {
        showError(err.message);
    } finally {
        loading.style.display = 'none';
        extractBtn.disabled = false;
    }
}

function displayResults(data) {
    resultsSection.style.display = 'block';
    
    if (detailedCheck.checked && data.data) {
        // Show detailed results
        simpleResult.style.display = 'none';
        detailedResult.style.display = 'block';
        
        const { text, confidence, word_count, words } = data.data;
        
        simpleResult.textContent = text;
        
        // Display stats
        stats.innerHTML = `
            <div class="stat-item">
                <span class="stat-value">${confidence}%</span>
                <span>Avg Confidence</span>
            </div>
            <div class="stat-item">
                <span class="stat-value">${word_count}</span>
                <span>Words Found</span>
            </div>
        `;
        
        // Display word list
        const wordListHtml = words.slice(0, 100).map(word => {
            const confidenceClass = word.confidence >= 80 ? 'confidence-high' : 
                                   word.confidence >= 60 ? 'confidence-medium' : 'confidence-low';
            return `
                <div class="word-item">
                    <span class="word-text">${word.text}</span>
                    <span class="word-confidence ${confidenceClass}">${word.confidence}%</span>
                </div>
            `;
        }).join('');
        
        detailedResult.innerHTML = `
            <h3>Extracted Text</h3>
            <div class="text-result">${text || '<em>No text detected</em>'}</div>
            <h3 style="margin-top: 1.5rem;">Word Details</h3>
            <div class="word-list">${wordListHtml}</div>
            ${words.length > 100 ? `<p style="margin-top: 1rem; color: var(--text-light);">Showing 100 of ${words.length} words</p>` : ''}
        `;
    } else {
        // Show simple results
        simpleResult.style.display = 'block';
        detailedResult.style.display = 'none';
        
        simpleResult.textContent = data.text || 'No text detected';
        
        const wordCount = data.text ? data.text.split(/\s+/).filter(w => w).length : 0;
        stats.innerHTML = `
            <div class="stat-item">
                <span class="stat-value">${wordCount}</span>
                <span>Words</span>
            </div>
            <div class="stat-item">
                <span class="stat-value">${data.text ? data.text.length : 0}</span>
                <span>Characters</span>
            </div>
        `;
    }
    
    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function showError(message) {
    errorMessage.textContent = message;
    error.style.display = 'block';
}

function copyToClipboard() {
    const text = lastResult.data ? lastResult.data.text : lastResult.text;
    
    navigator.clipboard.writeText(text).then(() => {
        const originalText = copyBtn.textContent;
        copyBtn.textContent = '✓ Copied!';
        setTimeout(() => {
            copyBtn.textContent = originalText;
        }, 2000);
    }).catch(() => {
        showError('Failed to copy to clipboard');
    });
}

function downloadTxt() {
    const text = lastResult.data ? lastResult.data.text : lastResult.text;
    const blob = new Blob([text], { type: 'text/plain' });
    downloadFile(blob, 'extracted_text.txt');
}

function downloadJson() {
    const jsonData = lastResult.data || { text: lastResult.text };
    const blob = new Blob([JSON.stringify(jsonData, null, 2)], { type: 'application/json' });
    downloadFile(blob, 'extracted_data.json');
}

function downloadFile(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
