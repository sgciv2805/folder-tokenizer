// DOM Elements
const folderPathInput = document.getElementById('folderPath');
const browseBtn = document.getElementById('browseBtn');
const analyzeBtn = document.getElementById('analyzeBtn');
const modelSelect = document.getElementById('modelSelect');
const useCustomModelCheckbox = document.getElementById('useCustomModel');
const customModelInput = document.getElementById('customModel');
const loadingSection = document.getElementById('loadingSection');
const errorSection = document.getElementById('errorSection');
const resultsSection = document.getElementById('resultsSection');
const errorText = document.getElementById('errorText');

// Handle custom model checkbox
useCustomModelCheckbox.addEventListener('change', (e) => {
    customModelInput.disabled = !e.target.checked;
    if (e.target.checked) {
        customModelInput.focus();
    }
});

// Handle browse button click
browseBtn.addEventListener('click', async () => {
    browseBtn.disabled = true;
    browseBtn.textContent = '...';
    
    try {
        const response = await fetch('/api/browse');
        const result = await response.json();
        
        if (result.path && !result.cancelled) {
            folderPathInput.value = result.path;
        }
    } catch (error) {
        console.error('Browse failed:', error);
    } finally {
        browseBtn.disabled = false;
        browseBtn.textContent = '📁 Browse';
    }
});

// Handle analyze button click
analyzeBtn.addEventListener('click', async () => {
    const folderPath = folderPathInput.value.trim();
    
    if (!folderPath) {
        showError('Please enter a folder path');
        return;
    }

    const model = useCustomModelCheckbox.checked && customModelInput.value
        ? customModelInput.value.trim()
        : modelSelect.value;

    await analyzeFolder(folderPath, model);
});

// Allow Enter key in input
folderPathInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        analyzeBtn.click();
    }
});

// Analyze folder function
async function analyzeFolder(folderPath, model) {
    // Hide previous results/errors
    hideAllSections();
    loadingSection.style.display = 'block';
    analyzeBtn.disabled = true;

    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ folderPath, model }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Analysis failed');
        }

        const result = await response.json();
        displayResults(result);
    } catch (error) {
        showError(error.message);
    } finally {
        loadingSection.style.display = 'none';
        analyzeBtn.disabled = false;
    }
}

// Display results
function displayResults(result) {
    hideAllSections();
    resultsSection.style.display = 'block';

    // Update summary metrics
    document.getElementById('totalTokens').textContent = formatNumber(result.total_tokens);
    document.getElementById('totalChars').textContent = formatNumber(result.total_chars);
    document.getElementById('successfulFiles').textContent = formatNumber(result.successful_files);
    document.getElementById('failedFiles').textContent = formatNumber(result.failed_files);

    // Display breakdown by type
    if (result.by_type && Object.keys(result.by_type).length > 0) {
        displayTypeBreakdown(result.by_type);
    }

    // Display file results in tables
    displayAllFiles(result.file_results);
    displayFailedFiles(result.file_results);
    displayTopFiles(result.file_results);

    // Set up tab switching
    setupTabs();
}

// Display type breakdown
function displayTypeBreakdown(byType) {
    const section = document.getElementById('byTypeSection');
    const container = document.getElementById('typeBreakdown');
    
    container.innerHTML = '';
    
    // Sort by tokens
    const sortedTypes = Object.entries(byType).sort((a, b) => b[1].tokens - a[1].tokens);
    
    sortedTypes.forEach(([type, stats]) => {
        const row = document.createElement('div');
        row.className = 'type-row';
        row.innerHTML = `
            <div>
                <span class="type-name">${capitalize(type)}</span>
            </div>
            <div class="type-stats">
                ${stats.files} files • ${formatNumber(stats.tokens)} tokens • ${formatNumber(stats.chars)} chars
            </div>
        `;
        container.appendChild(row);
    });
    
    section.style.display = 'block';
}

// Display all files
function displayAllFiles(fileResults) {
    const tbody = document.querySelector('#allFilesTable tbody');
    tbody.innerHTML = '';
    
    fileResults.forEach(file => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${getFileName(file.path)}</td>
            <td>${file.file_type}</td>
            <td>${formatNumber(file.tokens)}</td>
            <td>${formatNumber(file.chars)}</td>
            <td>${file.success ? '✅' : '❌'}</td>
        `;
        tbody.appendChild(row);
    });
}

// Display failed files
function displayFailedFiles(fileResults) {
    const tbody = document.querySelector('#failedFilesTable tbody');
    tbody.innerHTML = '';
    
    const failedFiles = fileResults.filter(f => !f.success);
    
    if (failedFiles.length === 0) {
        const row = document.createElement('tr');
        row.innerHTML = '<td colspan="3" style="text-align: center; color: #4caf50;">No failed files! 🎉</td>';
        tbody.appendChild(row);
        return;
    }
    
    failedFiles.forEach(file => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${getFileName(file.path)}</td>
            <td>${file.file_type}</td>
            <td>${file.error || 'Unknown error'}</td>
        `;
        tbody.appendChild(row);
    });
}

// Display top files
function displayTopFiles(fileResults) {
    const tbody = document.querySelector('#topFilesTable tbody');
    tbody.innerHTML = '';
    
    const successfulFiles = fileResults.filter(f => f.success);
    const topFiles = successfulFiles.sort((a, b) => b.tokens - a.tokens).slice(0, 50);
    
    topFiles.forEach(file => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${getFileName(file.path)}</td>
            <td>${file.file_type}</td>
            <td>${formatNumber(file.tokens)}</td>
            <td>${formatNumber(file.chars)}</td>
        `;
        tbody.appendChild(row);
    });
}

// Set up tab switching
function setupTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabPanels = document.querySelectorAll('.tab-panel');
    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.dataset.tab;
            
            // Remove active class from all buttons and panels
            tabBtns.forEach(b => b.classList.remove('active'));
            tabPanels.forEach(p => p.classList.remove('active'));
            
            // Add active class to clicked button and corresponding panel
            btn.classList.add('active');
            document.getElementById(`${targetTab}FilesTab`).classList.add('active');
        });
    });
}

// Utility functions
function showError(message) {
    hideAllSections();
    errorSection.style.display = 'block';
    errorText.textContent = message;
}

function hideAllSections() {
    loadingSection.style.display = 'none';
    errorSection.style.display = 'none';
    resultsSection.style.display = 'none';
}

function formatNumber(num) {
    return num.toLocaleString();
}

function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function getFileName(path) {
    return path.split('/').pop() || path;
}
