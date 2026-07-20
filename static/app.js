/**
 * F&O Stock Scanner - Frontend Application
 * Real-time search, export, and data management
 */

const API_BASE = '/api';
const ROWS_PER_PAGE = 50;

let allData = [];
let filteredData = [];
let currentPage = 1;
let isLoading = false;

// ===== DOM Elements =====

const authOverlay = document.getElementById('auth-overlay');
const loginBtn = document.getElementById('login-btn');
const mainContent = document.getElementById('main-content');
const searchInput = document.getElementById('search-input');
const refreshBtn = document.getElementById('refresh-btn');
const exportBtn = document.getElementById('export-btn');
const tableBody = document.getElementById('table-body');
const statusText = document.getElementById('status-text');
const rowCount = document.getElementById('row-count');
const prevBtn = document.getElementById('prev-btn');
const nextBtn = document.getElementById('next-btn');
const pageInfo = document.getElementById('page-info');
const toastContainer = document.getElementById('toast-container');

// ===== INITIALIZATION =====

async function init() {
    console.log('Initializing F&O Stock Scanner...');
    
    // Check authentication
    await checkAuthentication();
    
    // Load cached data
    await loadCachedData();
    
    // Attach event listeners
    attachEventListeners();
    
    console.log('Initialization complete');
}

// ===== AUTHENTICATION =====

async function checkAuthentication() {
    try {
        const response = await fetch(`${API_BASE}/auth-status`);
        const data = await response.json();
        
        if (!data.authenticated) {
            showAuthOverlay(data.auth_url);
        } else {
            hideAuthOverlay();
        }
    } catch (error) {
        console.error('Auth check error:', error);
        showAuthOverlay(null);
    }
}

function showAuthOverlay(authUrl) {
    authOverlay.classList.remove('hidden');
    mainContent.style.opacity = '0.5';
    mainContent.style.pointerEvents = 'none';
    
    // बटन क्लिक पर /auth/login पर डायरेक्ट रीडायरेक्ट करें
    if (loginBtn) {
        loginBtn.onclick = () => {
            window.location.href = '/auth/login';
        };
    }
}

function hideAuthOverlay() {
    authOverlay.classList.add('hidden');
    mainContent.style.opacity = '1';
    mainContent.style.pointerEvents = 'auto';
}

// ===== DATA LOADING =====

async function loadCachedData() {
    try {
        statusText.textContent = 'Loading cached data...';
        
        const response = await fetch(`${API_BASE}/data`);
        if (!response.ok) throw new Error('Failed to load data');
        
        const result = await response.json();
        allData = result.data || [];
        filteredData = [...allData];
        
        currentPage = 1;
        renderTable();
        updateRowCount();
        statusText.textContent = `Last updated: ${new Date(result.timestamp).toLocaleTimeString()}`;
        
        console.log(`Loaded ${allData.length} records`);
    } catch (error) {
        console.error('Error loading cached data:', error);
        statusText.textContent = 'Ready to refresh';
        showToast('No cached data. Click Refresh to load.', 'info');
    }
}

// ===== REFRESH DATA =====

async function refreshData() {
    if (isLoading) return;
    
    isLoading = true;
    refreshBtn.disabled = true;
    refreshBtn.textContent = '⏳ Refreshing...';
    statusText.textContent = 'Refreshing data from Fyers...';
    
    try {
        const response = await fetch(`${API_BASE}/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Refresh failed');
        }
        
        const result = await response.json();
        allData = result.data || [];
        filteredData = [...allData];
        currentPage = 1;
        
        renderTable();
        updateRowCount();
        statusText.textContent = `✓ Updated: ${new Date().toLocaleTimeString()} (${result.count} records)`;
        showToast(`✓ Refreshed ${result.count} stocks`, 'success');
        
        console.log(`Refresh complete: ${result.count} records`);
    } catch (error) {
        console.error('Refresh error:', error);
        statusText.textContent = `✗ Error: ${error.message}`;
        showToast(`Error: ${error.message}`, 'error');
    } finally {
        isLoading = false;
        refreshBtn.disabled = false;
        refreshBtn.textContent = '🔄 Refresh';
    }
}

// ===== SEARCH & FILTER =====

function filterData(searchTerm) {
    const term = searchTerm.trim().toUpperCase();
    
    if (term === '') {
        filteredData = [...allData];
    } else {
        filteredData = allData.filter(row => 
            row.nse_symbol.includes(term)
        );
    }
    
    currentPage = 1;
    renderTable();
    updateRowCount();
}

// ===== TABLE RENDERING =====

function renderTable() {
    if (filteredData.length === 0) {
        tableBody.innerHTML = `
            <tr class="no-results-row">
                <td colspan="5" class="no-results">
                    ${allData.length === 0 ? 'No data available. Click Refresh to load.' : 'No results found.'}
                </td>
            </tr>
        `;
        updatePagination();
        return;
    }
    
    // Paginate
    const startIdx = (currentPage - 1) * ROWS_PER_PAGE;
    const endIdx = startIdx + ROWS_PER_PAGE;
    const pageData = filteredData.slice(startIdx, endIdx);
    
    // Render rows
    tableBody.innerHTML = pageData.map(row => `
        <tr class="data-row">
            <td class="col-symbol"><strong>${escapeHtml(row.nse_symbol)}</strong></td>
            <td class="col-price">${formatPrice(row.spot)}</td>
            <td class="col-price">${formatPrice(row.future1)}</td>
            <td class="col-price">${formatPrice(row.future2)}</td>
            <td class="col-price">${formatPrice(row.future3)}</td>
        </tr>
    `).join('');
    
    updatePagination();
}

function updateRowCount() {
    rowCount.textContent = `Showing ${filteredData.length} of ${allData.length} records`;
}

function updatePagination() {
    const totalPages = Math.ceil(filteredData.length / ROWS_PER_PAGE);
    pageInfo.textContent = `Page ${currentPage} of ${totalPages || 1}`;
    
    prevBtn.disabled = currentPage <= 1;
    nextBtn.disabled = currentPage >= totalPages;
}

function formatPrice(price) {
    if (price === '-' || price === 0 || !price) return '-';
    const num = parseFloat(price);
    if (isNaN(num)) return '-';
    return `<strong>${num.toFixed(2)}</strong>`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ===== EXPORT TO EXCEL =====

async function exportToExcel() {
    if (allData.length === 0) {
        showToast('No data to export. Click Refresh first.', 'warning');
        return;
    }
    
    exportBtn.disabled = true;
    exportBtn.textContent = '⏳ Exporting...';
    
    try {
        const response = await fetch(`${API_BASE}/export`);
        
        if (!response.ok) throw new Error('Export failed');
        
        // Create blob and trigger download
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `FO_Scanner_${new Date().toISOString().split('T')[0]}.xlsx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        showToast(`✓ Exported ${allData.length} records`, 'success');
        console.log('Excel export successful');
    } catch (error) {
        console.error('Export error:', error);
        showToast(`Error: ${error.message}`, 'error');
    } finally {
        exportBtn.disabled = false;
        exportBtn.textContent = '📥 Export Excel';
    }
}

// ===== TOAST NOTIFICATIONS =====

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    
    toastContainer.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease-in-out';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ===== EVENT LISTENERS =====

function attachEventListeners() {
    // Search
    searchInput.addEventListener('input', (e) => {
        filterData(e.target.value);
    });
    
    // Refresh
    refreshBtn.addEventListener('click', refreshData);
    
    // Export
    exportBtn.addEventListener('click', exportToExcel);
    
    // Pagination
    prevBtn.addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            renderTable();
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    });
    
    nextBtn.addEventListener('click', () => {
        const totalPages = Math.ceil(filteredData.length / ROWS_PER_PAGE);
        if (currentPage < totalPages) {
            currentPage++;
            renderTable();
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    });
    
    // Search input focus
    searchInput.addEventListener('focus', () => {
        searchInput.style.borderColor = 'var(--accent-primary)';
    });
    
    searchInput.addEventListener('blur', () => {
        searchInput.style.borderColor = 'var(--border-color)';
    });
}

// ===== KEYBOARD SHORTCUTS =====

document.addEventListener('keydown', (e) => {
    // Ctrl+F or Cmd+F for search
    if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
        e.preventDefault();
        searchInput.focus();
        searchInput.select();
    }
    
    // Ctrl+R or Cmd+R for refresh (overrides browser default)
    if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
        e.preventDefault();
        if (!isLoading) refreshData();
    }
});

// ===== AUTO-FOCUS SEARCH ON LOAD =====

window.addEventListener('load', () => {
    searchInput.focus();
});

// ===== INITIALIZATION ON DOM READY =====

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

console.log('F&O Stock Scanner frontend loaded');
