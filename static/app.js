/**
 * F&O Stock Scanner - Frontend Application
 */

const API_BASE = '/api';
const ROWS_PER_PAGE = 50;

let allData = [];
let filteredData = [];
let currentPage = 1;
let isLoading = false;

// DOM Elements
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

async function init() {
    await checkAuthentication();
    await loadCachedData();
    attachEventListeners();
}

async function checkAuthentication() {
    try {
        const response = await fetch(`${API_BASE}/auth-status`);
        const data = await response.json();
        
        if (!data.authenticated) {
            showAuthOverlay();
        } else {
            hideAuthOverlay();
        }
    } catch (error) {
        console.error('Auth check error:', error);
        showAuthOverlay();
    }
}

function showAuthOverlay(authUrl) {
    if (authOverlay) authOverlay.classList.remove('hidden');
    if (mainContent) {
        mainContent.style.opacity = '0.2';
        mainContent.style.pointerEvents = 'none';
    }
    
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
        if (result.timestamp) {
            statusText.textContent = `Last updated: ${new Date(result.timestamp).toLocaleTimeString()}`;
        } else {
            statusText.textContent = 'Ready to refresh';
        }
    } catch (error) {
        statusText.textContent = 'Ready to refresh';
    }
}

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
        
        if (response.status === 401) {
            showAuthOverlay();
            throw new Error('Please login via Fyers first');
        }
        
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
    } catch (error) {
        statusText.textContent = `✗ Error: ${error.message}`;
        showToast(`Error: ${error.message}`, 'error');
    } finally {
        isLoading = false;
        refreshBtn.disabled = false;
        refreshBtn.textContent = '🔄 Refresh';
    }
}

function filterData(searchTerm) {
    const term = searchTerm.trim().toUpperCase();
    if (term === '') {
        filteredData = [...allData];
    } else {
        filteredData = allData.filter(row => row.nse_symbol.includes(term));
    }
    currentPage = 1;
    renderTable();
    updateRowCount();
}

function renderTable() {
    if (filteredData.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="5" style="text-align:center; padding: 30px;">
                    ${allData.length === 0 ? 'No data available. Click Refresh to load.' : 'No results found.'}
                </td>
            </tr>
        `;
        updatePagination();
        return;
    }
    
    const startIdx = (currentPage - 1) * ROWS_PER_PAGE;
    const pageData = filteredData.slice(startIdx, startIdx + ROWS_PER_PAGE);
    
    tableBody.innerHTML = pageData.map(row => `
        <tr>
            <td class="col-symbol"><strong>${row.nse_symbol}</strong></td>
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
    const totalPages = Math.ceil(filteredData.length / ROWS_PER_PAGE) || 1;
    pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
    prevBtn.disabled = currentPage <= 1;
    nextBtn.disabled = currentPage >= totalPages;
}

function formatPrice(price) {
    if (!price || price === '-') return '-';
    const num = parseFloat(price);
    return isNaN(num) ? '-' : `<strong>₹${num.toFixed(2)}</strong>`;
}

async function exportToExcel() {
    if (allData.length === 0) {
        showToast('No data to export. Click Refresh first.', 'warning');
        return;
    }
    exportBtn.disabled = true;
    try {
        const response = await fetch(`${API_BASE}/export`);
        if (!response.ok) throw new Error('Export failed');
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `FO_Scanner_${new Date().toISOString().split('T')[0]}.xlsx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        showToast('✓ Exported successfully', 'success');
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    } finally {
        exportBtn.disabled = false;
    }
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    toastContainer.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

function attachEventListeners() {
    if (searchInput) searchInput.addEventListener('input', (e) => filterData(e.target.value));
    if (refreshBtn) refreshBtn.addEventListener('click', refreshData);
    if (exportBtn) exportBtn.addEventListener('click', exportToExcel);
    if (prevBtn) prevBtn.addEventListener('click', () => { if (currentPage > 1) { currentPage--; renderTable(); } });
    if (nextBtn) nextBtn.addEventListener('click', () => { 
        const totalPages = Math.ceil(filteredData.length / ROWS_PER_PAGE);
        if (currentPage < totalPages) { currentPage++; renderTable(); }
    });
}

document.addEventListener('DOMContentLoaded', init);
