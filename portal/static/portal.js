/**
 * Airport TC Portal - External Party View
 *
 * This script handles the portal functionality for external parties
 * to view transaction details via a secure token.
 */

// Configuration
const API_BASE_URL = window.location.origin + '/api/v1';

// DOM Elements
const elements = {
    loading: document.getElementById('loading'),
    error: document.getElementById('error'),
    errorMessage: document.getElementById('error-message'),
    portal: document.getElementById('portal'),
    userRole: document.getElementById('user-role'),
    propertyAddress: document.getElementById('property-address'),
    transactionStatus: document.getElementById('transaction-status'),
    closingDate: document.getElementById('closing-date'),
    deadlinesCount: document.getElementById('deadlines-count'),
    documentsCount: document.getElementById('documents-count'),
    partiesCount: document.getElementById('parties-count'),
    deadlinesList: document.getElementById('deadlines-list'),
    documentsList: document.getElementById('documents-list'),
    partiesList: document.getElementById('parties-list'),
    timelineList: document.getElementById('timeline-list'),
    purchasePrice: document.getElementById('purchase-price'),
    effectiveDate: document.getElementById('effective-date'),
    closingDateDetail: document.getElementById('closing-date-detail'),
    yourRole: document.getElementById('your-role'),
    lastUpdated: document.getElementById('last-updated'),
};

// State
let portalData = null;

/**
 * Get token from URL query parameter
 */
function getTokenFromUrl() {
    const params = new URLSearchParams(window.location.search);
    return params.get('token');
}

/**
 * Format date for display
 */
function formatDate(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

/**
 * Format currency
 */
function formatCurrency(amount) {
    if (!amount) return '-';
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(amount);
}

/**
 * Calculate days until date
 */
function daysUntil(dateStr) {
    const date = new Date(dateStr);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    date.setHours(0, 0, 0, 0);
    return Math.ceil((date - today) / (1000 * 60 * 60 * 24));
}

/**
 * Get initials from name
 */
function getInitials(name) {
    if (!name) return '?';
    return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
}

/**
 * Show error state
 */
function showError(message) {
    elements.loading.classList.add('hidden');
    elements.portal.classList.add('hidden');
    elements.error.classList.remove('hidden');
    elements.errorMessage.textContent = message;
}

/**
 * Show portal content
 */
function showPortal() {
    elements.loading.classList.add('hidden');
    elements.error.classList.add('hidden');
    elements.portal.classList.remove('hidden');
}

/**
 * Render deadlines
 */
function renderDeadlines(deadlines) {
    if (!deadlines || deadlines.length === 0) {
        elements.deadlinesList.innerHTML = '<div class="empty-state">No upcoming deadlines</div>';
        elements.deadlinesCount.textContent = '0';
        return;
    }

    // Sort by date and filter to upcoming only
    const upcomingDeadlines = deadlines
        .filter(d => d.status !== 'completed')
        .sort((a, b) => new Date(a.due_date) - new Date(b.due_date))
        .slice(0, 5);

    elements.deadlinesCount.textContent = upcomingDeadlines.length;

    elements.deadlinesList.innerHTML = upcomingDeadlines.map(deadline => {
        const days = daysUntil(deadline.due_date);
        let daysClass = 'normal';
        let itemClass = '';

        if (days < 0) {
            daysClass = 'overdue';
            itemClass = 'overdue';
        } else if (days <= 3) {
            daysClass = 'urgent';
            itemClass = 'urgent';
        }

        const daysText = days < 0
            ? `${Math.abs(days)} days overdue`
            : days === 0
                ? 'Today'
                : `${days} days`;

        return `
            <div class="deadline-item ${itemClass}">
                <div>
                    <div class="deadline-name">${escapeHtml(deadline.name || 'Unnamed Deadline')}</div>
                    <div class="deadline-date">${formatDate(deadline.due_date)}</div>
                </div>
                <span class="deadline-days ${daysClass}">${daysText}</span>
            </div>
        `;
    }).join('');
}

/**
 * Render documents
 */
function renderDocuments(documents) {
    if (!documents || documents.length === 0) {
        elements.documentsList.innerHTML = '<div class="empty-state">No documents available</div>';
        elements.documentsCount.textContent = '0';
        return;
    }

    elements.documentsCount.textContent = documents.length;

    elements.documentsList.innerHTML = documents.slice(0, 5).map(doc => {
        let statusClass = 'pending';
        let statusText = 'Pending';

        if (doc.status === 'verified') {
            statusClass = 'verified';
            statusText = 'Verified';
        } else if (doc.status === 'needs_review') {
            statusClass = 'needs-review';
            statusText = 'Needs Review';
        }

        return `
            <div class="document-item">
                <div class="document-name">
                    <span>📄</span>
                    ${escapeHtml(doc.filename || doc.document_type || 'Document')}
                </div>
                <span class="document-status ${statusClass}">${statusText}</span>
            </div>
        `;
    }).join('');
}

/**
 * Render parties
 */
function renderParties(parties) {
    if (!parties || parties.length === 0) {
        elements.partiesList.innerHTML = '<div class="empty-state">No parties listed</div>';
        elements.partiesCount.textContent = '0';
        return;
    }

    elements.partiesCount.textContent = parties.length;

    elements.partiesList.innerHTML = parties.map(party => {
        const initials = getInitials(party.name);
        const role = (party.role || '').replace(/_/g, ' ');

        return `
            <div class="party-item">
                <div class="party-avatar">${initials}</div>
                <div class="party-info">
                    <div class="party-name">${escapeHtml(party.name || 'Unknown')}</div>
                    <div class="party-role">${escapeHtml(role)}</div>
                </div>
                ${party.email ? `<a href="mailto:${party.email}" class="party-contact">${escapeHtml(party.email)}</a>` : ''}
            </div>
        `;
    }).join('');
}

/**
 * Render timeline
 */
function renderTimeline(timeline) {
    if (!timeline || timeline.length === 0) {
        elements.timelineList.innerHTML = '<div class="empty-state">No recent activity</div>';
        return;
    }

    elements.timelineList.innerHTML = timeline.slice(0, 5).map(event => {
        return `
            <div class="timeline-item">
                <div class="timeline-content">
                    <div class="timeline-title">${escapeHtml(event.title || event.description || 'Event')}</div>
                    <div class="timeline-date">${formatDate(event.date || event.timestamp)}</div>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Format property address
 */
function formatAddress(address) {
    if (!address) return 'Property Address Not Available';

    const parts = [];
    if (address.street) parts.push(address.street);
    if (address.unit) parts.push(`Unit ${address.unit}`);
    if (address.city) parts.push(address.city);
    if (address.state) parts.push(address.state);
    if (address.zip_code) parts.push(address.zip_code);

    return parts.join(', ') || 'Property Address Not Available';
}

/**
 * Render portal data
 */
function renderPortalData(data) {
    portalData = data;

    // Header
    elements.userRole.textContent = (data.your_role || '').replace(/_/g, ' ');

    // Property banner
    elements.propertyAddress.textContent = formatAddress(data.property_address);
    elements.transactionStatus.textContent = data.status_label || data.status || 'Active';
    elements.transactionStatus.className = `status-badge ${data.status || 'active'}`;

    if (data.closing_date) {
        const days = daysUntil(data.closing_date);
        elements.closingDate.textContent = `Closing in ${days} days`;
    }

    // Details
    elements.purchasePrice.textContent = formatCurrency(data.purchase_price);
    elements.effectiveDate.textContent = formatDate(data.effective_date);
    elements.closingDateDetail.textContent = formatDate(data.closing_date);
    elements.yourRole.textContent = (data.your_role || '-').replace(/_/g, ' ');

    // Lists
    renderDeadlines(data.deadlines);
    renderDocuments(data.documents);
    renderParties(data.parties);
    renderTimeline(data.timeline);

    // Footer
    if (data.last_updated) {
        elements.lastUpdated.textContent = `Last updated: ${formatDate(data.last_updated)}`;
    } else {
        elements.lastUpdated.textContent = '';
    }

    showPortal();
}

/**
 * Fetch portal data from API
 */
async function fetchPortalData(token) {
    try {
        const response = await fetch(`${API_BASE_URL}/portal/view?token=${encodeURIComponent(token)}`);

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `Error ${response.status}`);
        }

        const data = await response.json();
        renderPortalData(data);

    } catch (error) {
        console.error('Failed to fetch portal data:', error);
        showError(error.message || 'Failed to load transaction details. Please try again.');
    }
}

/**
 * Accept invite (called when first accessing portal)
 */
async function acceptInvite(token) {
    try {
        const response = await fetch(`${API_BASE_URL}/portal/accept-invite`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ token })
        });

        // Ignore errors - this is optional
        await response.json().catch(() => ({}));
    } catch (error) {
        // Silently ignore errors
        console.log('Accept invite skipped:', error.message);
    }
}

/**
 * Set up Server-Sent Events for real-time updates
 */
function setupSSE(token) {
    // SSE not available for portal users without full auth
    // Could be enhanced to use a portal-specific SSE endpoint
    console.log('Real-time updates not available for portal view');
}

/**
 * Initialize portal
 */
async function init() {
    const token = getTokenFromUrl();

    if (!token) {
        showError('No access token provided. Please use the link from your invitation email.');
        return;
    }

    // Accept the invite (first-time access)
    await acceptInvite(token);

    // Fetch and display portal data
    await fetchPortalData(token);
}

// Start the app
document.addEventListener('DOMContentLoaded', init);
