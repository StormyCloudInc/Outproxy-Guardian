/**
 * Admin Panel JavaScript
 */

// Dynamically determine API URL based on current location
const API_URL = window.location.origin;

// Production URL for widget embed codes (always use this in embed examples)
const EMBED_URL = 'https://feedback.stormycloud.org';

// ==================== Utility Functions ====================

function showNotification(message, type = 'info') {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.className = `notification show ${type}`;

    setTimeout(() => {
        notification.classList.remove('show');
    }, 5000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleString();
}

function formatStatus(status) {
    return status.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

// ==================== Navigation ====================

function initNavigation() {
    const navBtns = document.querySelectorAll('.nav-btn');
    const sections = document.querySelectorAll('.admin-section');

    navBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const sectionId = btn.getAttribute('data-section');

            // Update active nav button
            navBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Show corresponding section
            sections.forEach(s => s.classList.remove('active'));
            document.getElementById(`${sectionId}-section`).classList.add('active');
        });
    });
}

// ==================== Modal Management ====================

function initModals() {
    const modals = document.querySelectorAll('.modal');

    modals.forEach(modal => {
        const closeButtons = modal.querySelectorAll('.modal-close');

        closeButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                modal.style.display = 'none';
            });
        });

        // Close on outside click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
    });
}

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'flex';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
    }
}

// ==================== Polls Management ====================

function showEmbedCode(pollId) {
    const embedCode = `<!-- Poll Widget -->
<div id="poll-widget"
     data-poll-id="${pollId}"
     data-api-url="${EMBED_URL}"
     data-show-results="false">
</div>

<!-- Load widget script (add once per page) -->
<script src="${EMBED_URL}/widgets/voting.js"></script>
<link rel="stylesheet" href="${EMBED_URL}/widgets/styles.css">`;

    document.getElementById('embed-code-content').textContent = embedCode;
    openModal('embed-code-modal');

    // Attach copy button handler each time modal opens
    const copyBtn = document.getElementById('copy-embed-btn');
    copyBtn.onclick = function() {
        navigator.clipboard.writeText(embedCode).then(() => {
            const originalText = copyBtn.textContent;
            copyBtn.textContent = 'Copied!';
            copyBtn.style.background = '#28a745';

            setTimeout(() => {
                copyBtn.textContent = originalText;
                copyBtn.style.background = '';
            }, 2000);
        }).catch(err => {
            console.error('Failed to copy:', err);
            showNotification('Failed to copy to clipboard', 'error');
        });
    };
}

async function togglePollStatus(pollId, currentStatus) {
    const newStatus = currentStatus ? 0 : 1;
    const action = newStatus ? 'activate' : 'close';

    if (!confirm(`Are you sure you want to ${action} this poll?`)) {
        return;
    }

    try {
        const response = await fetch(`${API_URL}/api/admin/polls/${pollId}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ is_active: newStatus })
        });

        if (response.ok) {
            showNotification(`Poll ${action}d successfully`, 'success');
            loadPolls();
        } else {
            const data = await response.json();
            showNotification(data.error || `Failed to ${action} poll`, 'error');
        }
    } catch (error) {
        console.error(`Failed to ${action} poll:`, error);
        showNotification('Network error. Please try again.', 'error');
    }
}

async function loadPolls() {
    const container = document.getElementById('polls-list');
    container.innerHTML = '<div class="loading">Loading polls...</div>';

    try {
        const response = await fetch(`${API_URL}/api/polls?active_only=false`);
        const polls = await response.json();

        if (polls.length === 0) {
            container.innerHTML = '<div class="empty-state">No polls yet. Create your first poll!</div>';
            return;
        }

        let html = '';
        for (const poll of polls) {
            const pollData = await fetch(`${API_URL}/api/polls/${poll.id}`).then(r => r.json());
            const totalVotes = pollData.options.reduce((sum, opt) => sum + opt.vote_count, 0);

            const statusToggleBtn = poll.is_active
                ? `<button class="btn btn-warning btn-sm" onclick="togglePollStatus(${poll.id}, ${poll.is_active})">Close Poll</button>`
                : `<button class="btn btn-success btn-sm" onclick="togglePollStatus(${poll.id}, ${poll.is_active})">Reactivate Poll</button>`;

            html += `
                <div class="poll-card">
                    <div class="card-header">
                        <h3>${escapeHtml(poll.title)}</h3>
                        <div class="card-actions">
                            <button class="btn btn-secondary btn-sm" onclick="showEmbedCode(${poll.id})">Get Embed Code</button>
                            ${statusToggleBtn}
                            <button class="btn btn-danger btn-sm" onclick="deletePoll(${poll.id})">Delete</button>
                        </div>
                    </div>
                    ${poll.description ? `<p class="card-description">${escapeHtml(poll.description)}</p>` : ''}
                    <div class="poll-stats">
                        <span class="stat-badge ${poll.is_active ? 'active' : 'inactive'}">
                            ${poll.is_active ? 'Active' : 'Closed'}
                        </span>
                        <span class="stat-badge">${totalVotes} votes</span>
                        <span class="stat-badge">${pollData.options.length} options</span>
                    </div>
                    <div class="poll-options">
                        ${pollData.options.map(opt => `
                            <div class="poll-option-result">
                                <span class="option-text">${escapeHtml(opt.option_text)}</span>
                                <span class="option-votes">${opt.vote_count} votes</span>
                            </div>
                        `).join('')}
                    </div>
                    <div class="card-footer">
                        <small>Created: ${formatDate(poll.created_at)}</small>
                    </div>
                </div>
            `;
        }

        container.innerHTML = html;

    } catch (error) {
        console.error('Failed to load polls:', error);
        container.innerHTML = '<div class="error-state">Failed to load polls. Please try again.</div>';
    }
}

async function createPoll(formData) {
    try {
        const response = await fetch(`${API_URL}/api/admin/polls`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });

        const data = await response.json();

        if (response.ok) {
            showNotification('Poll created successfully!', 'success');
            closeModal('create-poll-modal');
            loadPolls();
            document.getElementById('create-poll-form').reset();
            // Reset options to 2
            document.getElementById('poll-options-container').innerHTML = `
                <input type="text" class="poll-option-input" placeholder="Option 1" required>
                <input type="text" class="poll-option-input" placeholder="Option 2" required>
            `;

            // Show embed code for the newly created poll
            const pollId = data.poll.poll.id;
            setTimeout(() => showEmbedCode(pollId), 300);
        } else {
            showNotification(data.error || 'Failed to create poll', 'error');
        }
    } catch (error) {
        console.error('Failed to create poll:', error);
        showNotification('Network error. Please try again.', 'error');
    }
}

async function deletePoll(pollId) {
    if (!confirm('Are you sure you want to delete this poll? This action cannot be undone.')) {
        return;
    }

    try {
        const response = await fetch(`${API_URL}/api/admin/polls/${pollId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showNotification('Poll deleted successfully', 'success');
            loadPolls();
        } else {
            const data = await response.json();
            showNotification(data.error || 'Failed to delete poll', 'error');
        }
    } catch (error) {
        console.error('Failed to delete poll:', error);
        showNotification('Network error. Please try again.', 'error');
    }
}

function initPollsSection() {
    // Create poll button
    document.getElementById('create-poll-btn').addEventListener('click', () => {
        openModal('create-poll-modal');
    });

    // Add option button
    document.getElementById('add-option-btn').addEventListener('click', () => {
        const container = document.getElementById('poll-options-container');
        const optionCount = container.querySelectorAll('.poll-option-input').length;
        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'poll-option-input';
        input.placeholder = `Option ${optionCount + 1}`;
        container.appendChild(input);
    });

    // Create poll form
    document.getElementById('create-poll-form').addEventListener('submit', (e) => {
        e.preventDefault();

        const title = document.getElementById('poll-title').value;
        const description = document.getElementById('poll-description').value;
        const allowMultipleVotes = document.getElementById('poll-multiple-votes').checked;

        const optionInputs = document.querySelectorAll('.poll-option-input');
        const options = Array.from(optionInputs)
            .map(input => input.value.trim())
            .filter(val => val.length > 0);

        if (options.length < 2) {
            showNotification('Please provide at least 2 options', 'error');
            return;
        }

        createPoll({
            title,
            description,
            allow_multiple_votes: allowMultipleVotes,
            options
        });
    });

    // Load polls
    loadPolls();
}

// ==================== Feature Requests Management ====================

async function loadFeatures(status = null) {
    const container = document.getElementById('features-list');
    container.innerHTML = '<div class="loading">Loading feature requests...</div>';

    try {
        let url = `${API_URL}/api/features?sort_by=upvote_count`;
        if (status) {
            url += `&status=${status}`;
        }

        const response = await fetch(url);
        const features = await response.json();

        if (features.length === 0) {
            container.innerHTML = '<div class="empty-state">No feature requests found.</div>';
            return;
        }

        let html = '';
        features.forEach(feature => {
            const statusClass = `status-${feature.status.replace('_', '-')}`;

            html += `
                <div class="feature-card">
                    <div class="card-header">
                        <div>
                            <h3>${escapeHtml(feature.title)}</h3>
                            <span class="status-badge ${statusClass}">${formatStatus(feature.status)}</span>
                        </div>
                        <div class="card-actions">
                            <select class="status-select" data-feature-id="${feature.id}">
                                <option value="pending" ${feature.status === 'pending' ? 'selected' : ''}>Pending</option>
                                <option value="under_review" ${feature.status === 'under_review' ? 'selected' : ''}>Under Review</option>
                                <option value="planned" ${feature.status === 'planned' ? 'selected' : ''}>Planned</option>
                                <option value="in_progress" ${feature.status === 'in_progress' ? 'selected' : ''}>In Progress</option>
                                <option value="completed" ${feature.status === 'completed' ? 'selected' : ''}>Completed</option>
                                <option value="rejected" ${feature.status === 'rejected' ? 'selected' : ''}>Rejected</option>
                            </select>
                            <button class="btn btn-secondary btn-sm" onclick="viewSubscribers(${feature.id}, '${escapeHtml(feature.title).replace(/'/g, "\\'")}')">Subscribers</button>
                            <button class="btn btn-secondary btn-sm" onclick="openEditFeatureModal(${feature.id}, '${escapeHtml(feature.title).replace(/'/g, "\\'")}', \`${escapeHtml(feature.description).replace(/`/g, '\\`')}\`)">Edit</button>
                            <button class="btn btn-danger btn-sm" onclick="deleteFeature(${feature.id})">Delete</button>
                        </div>
                    </div>
                    <p class="card-description">${escapeHtml(feature.description)}</p>
                    <div class="feature-stats">
                        <span class="stat-badge">${feature.upvote_count} upvotes</span>
                        ${feature.submitter_name ? `<span class="stat-badge">by ${escapeHtml(feature.submitter_name)}</span>` : ''}
                        ${feature.submitter_email ? `<span class="stat-badge">${escapeHtml(feature.submitter_email)}</span>` : ''}
                    </div>
                    <div class="card-footer">
                        <small>Submitted: ${formatDate(feature.created_at)}</small>
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;

        // Add event listeners for status changes
        document.querySelectorAll('.status-select').forEach(select => {
            // Store initial value for reverting if cancelled
            select.setAttribute('data-old-value', select.value);

            select.addEventListener('change', (e) => {
                const featureId = e.target.getAttribute('data-feature-id');
                const newStatus = e.target.value;
                updateFeatureStatus(featureId, newStatus, e.target);
            });
        });

    } catch (error) {
        console.error('Failed to load features:', error);
        container.innerHTML = '<div class="error-state">Failed to load feature requests. Please try again.</div>';
    }
}

async function updateFeatureStatus(featureId, status, selectElement) {
    // Store the old value to revert if cancelled
    const oldValue = selectElement.getAttribute('data-old-value') || selectElement.value;

    // Open modal to ask for optional message
    document.getElementById('status-change-feature-id').value = featureId;
    document.getElementById('status-change-new-status').value = status;
    document.getElementById('status-change-message').value = '';

    // Store select element reference to update later
    window._statusChangeSelectElement = selectElement;
    window._statusChangeOldValue = oldValue;

    openModal('status-change-modal');
}

async function submitStatusChange() {
    const featureId = document.getElementById('status-change-feature-id').value;
    const status = document.getElementById('status-change-new-status').value;
    const adminMessage = document.getElementById('status-change-message').value.trim();
    const selectElement = window._statusChangeSelectElement;

    try {
        const payload = { status };
        if (adminMessage) {
            payload.admin_message = adminMessage;
        }

        const response = await fetch(`${API_URL}/api/admin/features/${featureId}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (response.ok) {
            const emailCount = data.emails_sent || 0;
            showNotification(
                `Feature status updated${emailCount > 0 ? ` (${emailCount} email${emailCount !== 1 ? 's' : ''} sent)` : ''}`,
                'success'
            );

            // Update the status badge without reloading
            const card = selectElement.closest('.feature-card');
            const badge = card.querySelector('.status-badge');
            badge.className = `status-badge status-${status.replace('_', '-')}`;
            badge.textContent = formatStatus(status);

            // Update the stored old value
            selectElement.setAttribute('data-old-value', status);

            closeModal('status-change-modal');
        } else {
            showNotification(data.error || 'Failed to update status', 'error');
            // Revert select to old value
            selectElement.value = window._statusChangeOldValue;
        }
    } catch (error) {
        console.error('Failed to update feature status:', error);
        showNotification('Network error. Please try again.', 'error');
        // Revert select to old value
        selectElement.value = window._statusChangeOldValue;
    }
}

function cancelStatusChange() {
    // Revert select to old value
    if (window._statusChangeSelectElement && window._statusChangeOldValue) {
        window._statusChangeSelectElement.value = window._statusChangeOldValue;
    }
    closeModal('status-change-modal');
}

async function deleteFeature(featureId) {
    if (!confirm('Are you sure you want to delete this feature request? This action cannot be undone.')) {
        return;
    }

    try {
        const response = await fetch(`${API_URL}/api/admin/features/${featureId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showNotification('Feature request deleted', 'success');
            const statusFilter = document.getElementById('feature-status-filter').value;
            loadFeatures(statusFilter || null);
        } else {
            const data = await response.json();
            showNotification(data.error || 'Failed to delete feature', 'error');
        }
    } catch (error) {
        console.error('Failed to delete feature:', error);
        showNotification('Network error. Please try again.', 'error');
    }
}

function openEditFeatureModal(featureId, title, description) {
    document.getElementById('edit-feature-id').value = featureId;
    document.getElementById('edit-feature-title').value = title;
    document.getElementById('edit-feature-description').value = description;
    openModal('edit-feature-modal');
}

async function editFeature(featureId, title, description) {
    try {
        const response = await fetch(`${API_URL}/api/admin/features/${featureId}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ title, description })
        });

        if (response.ok) {
            showNotification('Feature updated successfully', 'success');
            closeModal('edit-feature-modal');
            const statusFilter = document.getElementById('feature-status-filter').value;
            loadFeatures(statusFilter || null);
        } else {
            const data = await response.json();
            showNotification(data.error || 'Failed to update feature', 'error');
        }
    } catch (error) {
        console.error('Failed to update feature:', error);
        showNotification('Network error. Please try again.', 'error');
    }
}

async function viewSubscribers(featureId, featureTitle) {
    try {
        const response = await fetch(`${API_URL}/api/admin/features/${featureId}/subscribers`);
        const data = await response.json();

        if (response.ok) {
            displaySubscribers(featureId, featureTitle, data.subscribers);
        } else {
            showNotification(data.error || 'Failed to load subscribers', 'error');
        }
    } catch (error) {
        console.error('Failed to load subscribers:', error);
        showNotification('Network error loading subscribers', 'error');
    }
}

function displaySubscribers(featureId, featureTitle, subscribers) {
    // Update modal title
    document.querySelector('#view-subscribers-modal .modal-header h3').textContent = `Subscribers: ${featureTitle}`;

    // Display subscribers list
    const listContainer = document.getElementById('subscribers-list');

    if (subscribers.length === 0) {
        listContainer.innerHTML = '<p style="color: #999; text-align: center; padding: 20px;">No subscribers for this feature</p>';
    } else {
        const html = `
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="border-bottom: 2px solid #dee2e6; text-align: left;">
                        <th style="padding: 12px;">Email</th>
                        <th style="padding: 12px;">Subscribed At</th>
                        <th style="padding: 12px; text-align: center;">Action</th>
                    </tr>
                </thead>
                <tbody>
                    ${subscribers.map(sub => `
                        <tr style="border-bottom: 1px solid #dee2e6;">
                            <td style="padding: 12px;">${escapeHtml(sub.email)}</td>
                            <td style="padding: 12px; color: #666;">${formatDate(sub.subscribed_at)}</td>
                            <td style="padding: 12px; text-align: center;">
                                <button class="btn btn-danger btn-sm" onclick="removeSubscriber(${featureId}, '${escapeHtml(sub.email).replace(/'/g, "\\'")}', '${escapeHtml(featureTitle).replace(/'/g, "\\'")}')">
                                    Remove
                                </button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
        listContainer.innerHTML = html;
    }

    openModal('view-subscribers-modal');
}

async function removeSubscriber(featureId, email, featureTitle) {
    if (!confirm(`Are you sure you want to unsubscribe ${email} from this feature?`)) {
        return;
    }

    try {
        const response = await fetch(`${API_URL}/api/admin/features/${featureId}/subscribers/${encodeURIComponent(email)}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (response.ok) {
            showNotification('Subscriber removed successfully', 'success');
            // Reload the subscribers list
            viewSubscribers(featureId, featureTitle);
        } else {
            showNotification(data.error || 'Failed to remove subscriber', 'error');
        }
    } catch (error) {
        console.error('Failed to remove subscriber:', error);
        showNotification('Network error. Please try again.', 'error');
    }
}

function initFeaturesSection() {
    // Status filter
    document.getElementById('feature-status-filter').addEventListener('change', (e) => {
        const status = e.target.value || null;
        loadFeatures(status);
    });

    // Edit feature form submission
    document.getElementById('edit-feature-form').addEventListener('submit', (e) => {
        e.preventDefault();
        const featureId = document.getElementById('edit-feature-id').value;
        const title = document.getElementById('edit-feature-title').value;
        const description = document.getElementById('edit-feature-description').value;
        editFeature(featureId, title, description);
    });

    // Load features
    loadFeatures();
}

// ==================== Widgets Section ====================

function initWidgetsSection() {
    // Define embed codes
    const embedCodes = {
        feedback: `<!-- Feedback Widget -->
<div id="feedback-widget"
     data-document-id="your-page-id"
     data-api-url="${EMBED_URL}">
</div>

<!-- Load widget scripts (add once per page) -->
<script src="${EMBED_URL}/widgets/feedback.js"></script>
<link rel="stylesheet" href="${EMBED_URL}/widgets/styles.css">`,

        features: `<!-- Feature Request Widget -->
<div id="features-widget"
     data-api-url="${EMBED_URL}"
     data-mode="list"
     data-max-items="10">
</div>

<!-- Load widget scripts (add once per page) -->
<script src="${EMBED_URL}/widgets/features.js"></script>
<link rel="stylesheet" href="${EMBED_URL}/widgets/styles.css">`,

        mailingList: `<!-- Mailing List Widget -->
<div id="mailing-list-widget"
     data-api-url="${EMBED_URL}"
     data-button-text="Subscribe"
     data-placeholder="Enter your email">
</div>

<!-- Load widget scripts (add once per page) -->
<script src="${EMBED_URL}/widgets/mailing-list.js"></script>
<link rel="stylesheet" href="${EMBED_URL}/widgets/styles.css">`
    };

    // Populate code blocks
    const codeBlocks = document.querySelectorAll('.widget-code-card .code-content');
    const codeTypes = ['feedback', 'features', 'mailingList'];
    codeBlocks.forEach((pre, index) => {
        const codeType = codeTypes[index] || 'feedback';
        pre.textContent = embedCodes[codeType];
    });

    // Add copy button handlers
    document.querySelectorAll('.widget-code-card .copy-code-btn').forEach((btn, index) => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();

            const codeBlock = this.closest('.code-display').querySelector('.code-content');
            const code = codeBlock.textContent;

            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(code).then(() => {
                    const originalText = this.textContent;
                    this.textContent = 'Copied!';
                    this.style.background = '#28a745';
                    this.style.color = 'white';

                    setTimeout(() => {
                        this.textContent = originalText;
                        this.style.background = '';
                        this.style.color = '';
                    }, 2000);
                }).catch(err => {
                    console.error('Failed to copy:', err);
                    fallbackCopy(code, this);
                });
            } else {
                fallbackCopy(code, this);
            }
        });
    });
}

function fallbackCopy(text, button) {
    // Fallback for browsers without clipboard API
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();

    try {
        document.execCommand('copy');
        const originalText = button.textContent;
        button.textContent = 'Copied!';
        button.style.background = '#28a745';
        button.style.color = 'white';

        setTimeout(() => {
            button.textContent = originalText;
            button.style.background = '';
            button.style.color = '';
        }, 2000);
    } catch (err) {
        showNotification('Failed to copy to clipboard', 'error');
    }

    document.body.removeChild(textarea);
}

// ==================== Feedback Section ====================

async function loadFeedbackStats() {
    try {
        const response = await fetch(`${API_URL}/api/admin/feedback/stats`);
        const data = await response.json();

        if (response.ok) {
            displayFeedbackStats(data.documents);
        } else {
            document.getElementById('feedback-docs-list').innerHTML =
                '<div class="error">Failed to load feedback stats</div>';
        }
    } catch (error) {
        console.error('Error loading feedback stats:', error);
        document.getElementById('feedback-docs-list').innerHTML =
            '<div class="error">Network error loading stats</div>';
    }
}

async function loadRecentFeedback() {
    try {
        const response = await fetch(`${API_URL}/api/admin/feedback/recent?limit=20`);
        const data = await response.json();

        if (response.ok) {
            displayRecentFeedback(data.feedback);
        } else {
            document.getElementById('feedback-messages-list').innerHTML =
                '<div class="error">Failed to load recent feedback</div>';
        }
    } catch (error) {
        console.error('Error loading recent feedback:', error);
        document.getElementById('feedback-messages-list').innerHTML =
            '<div class="error">Network error loading feedback</div>';
    }
}

function displayFeedbackStats(documents) {
    // Calculate totals
    let totalDocs = documents.length;
    let totalUp = 0;
    let totalDown = 0;

    documents.forEach(doc => {
        totalUp += doc.up;
        totalDown += doc.down;
    });

    const satisfaction = totalUp + totalDown > 0
        ? Math.round((totalUp / (totalUp + totalDown)) * 100)
        : 0;

    // Update summary cards
    document.getElementById('stat-total-docs').textContent = totalDocs;
    document.getElementById('stat-thumbs-up').textContent = totalUp;
    document.getElementById('stat-thumbs-down').textContent = totalDown;
    document.getElementById('stat-satisfaction').textContent = `${satisfaction}%`;

    // Display documents table
    if (documents.length === 0) {
        document.getElementById('feedback-docs-list').innerHTML =
            '<p style="color: #999; text-align: center; padding: 20px;">No feedback received yet</p>';
        return;
    }

    const html = `
        <table style="width: 100%; border-collapse: collapse;">
            <thead>
                <tr style="border-bottom: 2px solid #dee2e6; text-align: left;">
                    <th style="padding: 12px;">Document Path</th>
                    <th style="padding: 12px; text-align: center;">👍 Up</th>
                    <th style="padding: 12px; text-align: center;">👎 Down</th>
                    <th style="padding: 12px; text-align: center;">Total</th>
                    <th style="padding: 12px; text-align: center;">Rating</th>
                    <th style="padding: 12px;">Last Feedback</th>
                </tr>
            </thead>
            <tbody>
                ${documents.map(doc => {
                    const rating = doc.total > 0
                        ? Math.round((doc.up / doc.total) * 100)
                        : 0;
                    const ratingColor = rating >= 75 ? '#28a745' : rating >= 50 ? '#ffc107' : '#dc3545';

                    return `
                        <tr style="border-bottom: 1px solid #dee2e6;">
                            <td style="padding: 12px; font-family: monospace; font-size: 13px;">${doc.document_id}</td>
                            <td style="padding: 12px; text-align: center; color: #28a745; font-weight: 600;">${doc.up}</td>
                            <td style="padding: 12px; text-align: center; color: #dc3545; font-weight: 600;">${doc.down}</td>
                            <td style="padding: 12px; text-align: center; font-weight: 600;">${doc.total}</td>
                            <td style="padding: 12px; text-align: center;">
                                <span style="display: inline-block; padding: 4px 12px; background: ${ratingColor}15; color: ${ratingColor}; border-radius: 12px; font-weight: 600; font-size: 13px;">
                                    ${rating}%
                                </span>
                            </td>
                            <td style="padding: 12px; color: #666; font-size: 13px;">${new Date(doc.last_feedback).toLocaleString()}</td>
                        </tr>
                    `;
                }).join('')}
            </tbody>
        </table>
    `;

    document.getElementById('feedback-docs-list').innerHTML = html;
}

function displayRecentFeedback(feedback) {
    if (feedback.length === 0) {
        document.getElementById('feedback-messages-list').innerHTML =
            '<p style="color: #999; text-align: center; padding: 20px;">No detailed feedback messages yet</p>';
        return;
    }

    const html = feedback.map(item => `
        <div style="padding: 15px; border: 1px solid #dee2e6; border-radius: 6px; margin-bottom: 15px; background: #f8f9fa;">
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 10px;">
                <div style="font-family: monospace; font-size: 13px; color: #0066cc;">${item.document_id}</div>
                <div style="font-size: 12px; color: #999;">${new Date(item.created_at).toLocaleString()}</div>
            </div>
            ${item.email ? `<div style="margin-bottom: 8px;"><strong>Email:</strong> ${item.email}</div>` : ''}
            ${item.message ? `<div style="background: white; padding: 12px; border-radius: 4px; border: 1px solid #dee2e6;"><strong>Message:</strong><br>${item.message}</div>` : ''}
        </div>
    `).join('');

    document.getElementById('feedback-messages-list').innerHTML = html;
}

function initFeedbackSection() {
    // Load initial data
    loadFeedbackStats();
    loadRecentFeedback();

    // Refresh button
    const refreshBtn = document.getElementById('refresh-feedback-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            loadFeedbackStats();
            loadRecentFeedback();
            showNotification('Feedback stats refreshed', 'success');
        });
    }
}

// ==================== Email Stats Section ====================

async function loadEmailStats() {
    try {
        const response = await fetch(`${API_URL}/api/admin/email/stats`);
        const data = await response.json();

        if (response.ok) {
            displayEmailStats(data);
        } else {
            document.getElementById('email-logs-list').innerHTML =
                '<div class="error">Failed to load email stats</div>';
        }
    } catch (error) {
        console.error('Error loading email stats:', error);
        document.getElementById('email-logs-list').innerHTML =
            '<div class="error">Network error loading stats</div>';
    }
}

async function loadRecentEmails() {
    try {
        const response = await fetch(`${API_URL}/api/admin/email/recent?limit=50`);
        const data = await response.json();

        if (response.ok) {
            displayRecentEmails(data.emails);
        } else {
            document.getElementById('email-logs-list').innerHTML =
                '<div class="error">Failed to load email logs</div>';
        }
    } catch (error) {
        console.error('Error loading recent emails:', error);
        document.getElementById('email-logs-list').innerHTML =
            '<div class="error">Network error loading email logs</div>';
    }
}

function displayEmailStats(stats) {
    document.getElementById('stat-email-total').textContent = stats.total || 0;
    document.getElementById('stat-email-success').textContent = stats.successful || 0;
    document.getElementById('stat-email-failed').textContent = stats.failed || 0;
    document.getElementById('stat-email-last').textContent = stats.last_sent
        ? new Date(stats.last_sent).toLocaleString()
        : 'Never';
}

function displayRecentEmails(emails) {
    if (emails.length === 0) {
        document.getElementById('email-logs-list').innerHTML =
            '<p style="color: #999; text-align: center; padding: 20px;">No emails sent yet</p>';
        return;
    }

    const html = `
        <table style="width: 100%; border-collapse: collapse;">
            <thead>
                <tr style="border-bottom: 2px solid #dee2e6; text-align: left;">
                    <th style="padding: 12px;">Type</th>
                    <th style="padding: 12px;">Recipient</th>
                    <th style="padding: 12px;">Subject</th>
                    <th style="padding: 12px; text-align: center;">Status</th>
                    <th style="padding: 12px;">Timestamp</th>
                </tr>
            </thead>
            <tbody>
                ${emails.map(email => `
                    <tr style="border-bottom: 1px solid #dee2e6;">
                        <td style="padding: 12px;">${email.email_type}</td>
                        <td style="padding: 12px;">${email.recipient}</td>
                        <td style="padding: 12px; max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${email.subject || '-'}</td>
                        <td style="padding: 12px; text-align: center;">
                            <span style="display: inline-block; padding: 4px 12px; background: ${email.status === 'success' ? '#d4edda' : '#f8d7da'}; color: ${email.status === 'success' ? '#155724' : '#721c24'}; border-radius: 12px; font-weight: 600; font-size: 12px;">
                                ${email.status === 'success' ? '✓ Success' : '✗ Failed'}
                            </span>
                            ${email.error_message ? `<div style="font-size: 11px; color: #dc3545; margin-top: 4px;">${email.error_message}</div>` : ''}
                        </td>
                        <td style="padding: 12px; color: #666; font-size: 13px;">${new Date(email.created_at).toLocaleString()}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;

    document.getElementById('email-logs-list').innerHTML = html;
}

function initEmailsSection() {
    loadEmailStats();
    loadRecentEmails();

    const refreshBtn = document.getElementById('refresh-email-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            loadEmailStats();
            loadRecentEmails();
            showNotification('Email stats refreshed', 'success');
        });
    }
}

// ==================== Settings Section ====================

async function loadSettings() {
    try {
        const response = await fetch(`${API_URL}/api/admin/config`);
        const data = await response.json();

        if (response.ok) {
            displaySettings(data.config);
        } else {
            document.getElementById('settings-form').innerHTML =
                '<div class="error">Failed to load settings</div>';
        }
    } catch (error) {
        console.error('Error loading settings:', error);
        document.getElementById('settings-form').innerHTML =
            '<div class="error">Network error loading settings</div>';
    }
}

function displaySettings(config) {
    const sections = {
        'Database': ['DATABASE_PATH'],
        'Server': ['HOST', 'PORT', 'DEBUG'],
        'CORS': ['CORS_ORIGINS'],
        'Admin': ['ADMIN_ONLY_LOCALHOST'],
        'Rate Limiting': ['RATE_LIMIT_ENABLED', 'RATE_LIMIT_FEEDBACK', 'RATE_LIMIT_VOTE', 'RATE_LIMIT_FEATURE_SUBMIT', 'RATE_LIMIT_FEATURE_UPVOTE'],
        'Email (SMTP)': ['SMTP_ENABLED', 'SMTP_HOST', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASSWORD', 'SMTP_USE_TLS', 'SMTP_FROM', 'SMTP_TO'],
        'Security': ['SECRET_KEY', 'SESSION_COOKIE_SECURE'],
        'Network URLs': ['CLEARNET_URL', 'I2P_URL', 'TOR_URL']
    };

    let html = '';
    for (const [section, keys] of Object.entries(sections)) {
        html += `<div style="margin-bottom: 30px;">`;
        html += `<h3 style="margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid #dee2e6;">${section}</h3>`;

        keys.forEach(key => {
            const value = config[key] || '';
            const isPassword = key.includes('PASSWORD') || key.includes('SECRET') || key.includes('KEY');
            const isBoolean = value === 'True' || value === 'False' || value === 'true' || value === 'false';

            html += `<div class="form-group" style="margin-bottom: 15px;">`;
            html += `<label for="setting-${key}" style="display: block; margin-bottom: 5px; font-weight: 500;">${key}</label>`;

            if (isBoolean) {
                html += `<select id="setting-${key}" class="setting-input" data-key="${key}" style="width: 100%; padding: 10px; border: 1px solid #ced4da; border-radius: 4px;">`;
                html += `<option value="True" ${(value === 'True' || value === 'true') ? 'selected' : ''}>True</option>`;
                html += `<option value="False" ${(value === 'False' || value === 'false') ? 'selected' : ''}>False</option>`;
                html += `</select>`;
            } else {
                html += `<input type="${isPassword ? 'password' : 'text'}" id="setting-${key}" class="setting-input" data-key="${key}" value="${value}" style="width: 100%; padding: 10px; border: 1px solid #ced4da; border-radius: 4px;">`;
            }

            html += `</div>`;
        });

        html += `</div>`;
    }

    document.getElementById('settings-form').innerHTML = html;
}

async function saveSettings() {
    const inputs = document.querySelectorAll('.setting-input');
    const config = {};

    inputs.forEach(input => {
        const key = input.getAttribute('data-key');
        config[key] = input.value;
    });

    try {
        const response = await fetch(`${API_URL}/api/admin/config`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ config })
        });

        const data = await response.json();

        if (response.ok) {
            showNotification('Settings saved successfully! Please restart the application.', 'success');
        } else {
            showNotification(data.error || 'Failed to save settings', 'error');
        }
    } catch (error) {
        console.error('Error saving settings:', error);
        showNotification('Network error saving settings', 'error');
    }
}

function initSettingsSection() {
    loadSettings();

    const saveBtn = document.getElementById('save-settings-btn');
    if (saveBtn) {
        saveBtn.addEventListener('click', saveSettings);
    }
}

// ==================== Mailing List Section ====================

async function loadMailingListStats() {
    try {
        const response = await fetch(`${API_URL}/api/admin/mailing-list/stats`);
        const data = await response.json();

        if (response.ok) {
            document.getElementById('stat-mailing-total').textContent = data.total || 0;
            document.getElementById('stat-mailing-active').textContent = data.active || 0;
            document.getElementById('stat-mailing-unsubscribed').textContent = data.unsubscribed || 0;
        }
    } catch (error) {
        console.error('Error loading mailing list stats:', error);
    }
}

async function loadMailingListSubscribers() {
    const container = document.getElementById('mailing-list-subscribers');
    container.innerHTML = '<div class="loading">Loading subscribers...</div>';

    try {
        const response = await fetch(`${API_URL}/api/admin/mailing-list/subscribers`);
        const data = await response.json();

        if (!response.ok) {
            container.innerHTML = '<div class="error">Failed to load subscribers</div>';
            return;
        }

        if (data.subscribers.length === 0) {
            container.innerHTML = '<p style="color: #999; text-align: center; padding: 20px;">No subscribers yet</p>';
            return;
        }

        const html = `
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="border-bottom: 2px solid #dee2e6; text-align: left;">
                        <th style="padding: 12px;">Email</th>
                        <th style="padding: 12px;">Subscribed At</th>
                        <th style="padding: 12px; text-align: center;">Status</th>
                        <th style="padding: 12px; text-align: center;">Action</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.subscribers.map(sub => `
                        <tr style="border-bottom: 1px solid #dee2e6;">
                            <td style="padding: 12px;">${escapeHtml(sub.email)}</td>
                            <td style="padding: 12px; color: #666;">${formatDate(sub.subscribed_at)}</td>
                            <td style="padding: 12px; text-align: center;">
                                <span style="display: inline-block; padding: 4px 12px; background: ${sub.is_active ? '#d4edda' : '#f8d7da'}; color: ${sub.is_active ? '#155724' : '#721c24'}; border-radius: 12px; font-weight: 600; font-size: 12px;">
                                    ${sub.is_active ? 'Active' : 'Unsubscribed'}
                                </span>
                            </td>
                            <td style="padding: 12px; text-align: center;">
                                ${sub.is_active ? `<button class="btn btn-danger btn-sm" onclick="removeMailingListSubscriber('${escapeHtml(sub.email).replace(/'/g, "\\'")}')">Remove</button>` : '-'}
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;

        container.innerHTML = html;

    } catch (error) {
        console.error('Error loading mailing list subscribers:', error);
        container.innerHTML = '<div class="error">Network error loading subscribers</div>';
    }
}

async function removeMailingListSubscriber(email) {
    if (!confirm(`Are you sure you want to remove ${email} from the mailing list?`)) {
        return;
    }

    try {
        const response = await fetch(`${API_URL}/api/admin/mailing-list/subscribers/${encodeURIComponent(email)}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (response.ok) {
            showNotification('Subscriber removed successfully', 'success');
            loadMailingListStats();
            loadMailingListSubscribers();
        } else {
            showNotification(data.error || 'Failed to remove subscriber', 'error');
        }
    } catch (error) {
        console.error('Failed to remove subscriber:', error);
        showNotification('Network error. Please try again.', 'error');
    }
}

async function sendBroadcastEmail(subject, message, htmlMessage) {
    try {
        const response = await fetch(`${API_URL}/api/admin/mailing-list/send`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                subject,
                message,
                html_message: htmlMessage || null
            })
        });

        const data = await response.json();

        if (response.ok) {
            showNotification(`Broadcast sent to ${data.sent_count} subscriber${data.sent_count !== 1 ? 's' : ''}`, 'success');
            closeModal('send-broadcast-modal');
            document.getElementById('broadcast-form').reset();
        } else {
            showNotification(data.error || 'Failed to send broadcast', 'error');
        }
    } catch (error) {
        console.error('Failed to send broadcast:', error);
        showNotification('Network error. Please try again.', 'error');
    }
}

function initMailingListSection() {
    loadMailingListStats();
    loadMailingListSubscribers();

    // Send broadcast button
    const sendBtn = document.getElementById('send-broadcast-btn');
    if (sendBtn) {
        sendBtn.addEventListener('click', () => {
            openModal('send-broadcast-modal');
        });
    }

    // Broadcast form
    const form = document.getElementById('broadcast-form');
    if (form) {
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            const subject = document.getElementById('broadcast-subject').value;
            const message = document.getElementById('broadcast-message').value;
            const htmlMessage = document.getElementById('broadcast-html').value;

            if (!confirm('Are you sure you want to send this email to all subscribers?')) {
                return;
            }

            sendBroadcastEmail(subject, message, htmlMessage);
        });
    }
}

// ==================== Comments Section ====================

async function loadComments() {
    const container = document.getElementById('comments-list');
    container.innerHTML = '<div class="loading">Loading comments...</div>';

    try {
        const response = await fetch(`${API_URL}/api/admin/comments/recent?limit=100`);
        const data = await response.json();

        if (!response.ok) {
            container.innerHTML = '<div class="error">Failed to load comments</div>';
            return;
        }

        if (data.comments.length === 0) {
            container.innerHTML = '<p style="color: #999; text-align: center; padding: 20px;">No comments yet</p>';
            return;
        }

        displayComments(data.comments);

    } catch (error) {
        console.error('Error loading comments:', error);
        container.innerHTML = '<div class="error">Network error loading comments</div>';
    }
}

function displayComments(comments) {
    const container = document.getElementById('comments-list');

    const html = `
        <table style="width: 100%; border-collapse: collapse;">
            <thead>
                <tr style="border-bottom: 2px solid #dee2e6; text-align: left;">
                    <th style="padding: 12px;">Feature</th>
                    <th style="padding: 12px;">Author</th>
                    <th style="padding: 12px;">Comment</th>
                    <th style="padding: 12px;">Date</th>
                    <th style="padding: 12px; text-align: center;">Actions</th>
                </tr>
            </thead>
            <tbody>
                ${comments.map(comment => `
                    <tr style="border-bottom: 1px solid #dee2e6; ${comment.is_deleted ? 'background: #f8d7da;' : ''}">
                        <td style="padding: 12px;">
                            <div style="font-weight: 600; margin-bottom: 4px;">${escapeHtml(comment.feature_title)}</div>
                            <div style="font-size: 12px; color: #666;">Feature #${comment.feature_id}</div>
                        </td>
                        <td style="padding: 12px;">
                            <div style="font-weight: 500;">${escapeHtml(comment.author_name || 'Anonymous')}</div>
                            ${comment.author_email ? `<div style="font-size: 12px; color: #666;">${escapeHtml(comment.author_email)}</div>` : ''}
                            ${comment.ip_address ? `<div style="font-size: 11px; color: #999;">${comment.ip_address}</div>` : ''}
                        </td>
                        <td style="padding: 12px; max-width: 400px;">
                            <div style="word-wrap: break-word; white-space: pre-wrap;">${escapeHtml(comment.comment_text)}</div>
                            ${comment.is_deleted ? '<div style="color: #721c24; font-weight: 600; margin-top: 6px;">DELETED</div>' : ''}
                        </td>
                        <td style="padding: 12px; color: #666; font-size: 13px; white-space: nowrap;">${formatDate(comment.created_at)}</td>
                        <td style="padding: 12px; text-align: center;">
                            ${!comment.is_deleted ? `<button class="btn btn-danger btn-sm" onclick="deleteComment(${comment.id})">Delete</button>` : '-'}
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;

    container.innerHTML = html;
}

async function deleteComment(commentId) {
    if (!confirm('Are you sure you want to delete this comment? This action cannot be undone.')) {
        return;
    }

    try {
        const response = await fetch(`${API_URL}/api/admin/comments/${commentId}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (response.ok) {
            showNotification('Comment deleted successfully', 'success');
            loadComments();
        } else {
            showNotification(data.error || 'Failed to delete comment', 'error');
        }
    } catch (error) {
        console.error('Failed to delete comment:', error);
        showNotification('Network error. Please try again.', 'error');
    }
}

function initCommentsSection() {
    loadComments();

    const refreshBtn = document.getElementById('refresh-comments-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            loadComments();
            showNotification('Comments refreshed', 'success');
        });
    }
}

// ==================== Initialize ====================

document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initModals();
    initPollsSection();
    initFeaturesSection();
    initCommentsSection();
    initMailingListSection();
    initWidgetsSection();
    initFeedbackSection();
    initEmailsSection();
    initSettingsSection();

    console.log('Admin panel initialized');
});
