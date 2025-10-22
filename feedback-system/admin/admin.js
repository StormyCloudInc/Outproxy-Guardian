/**
 * Admin Panel JavaScript
 */

const API_URL = 'http://localhost:5000';

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

            html += `
                <div class="poll-card">
                    <div class="card-header">
                        <h3>${escapeHtml(poll.title)}</h3>
                        <div class="card-actions">
                            <button class="btn btn-danger btn-sm" onclick="deletePoll(${poll.id})">Delete</button>
                        </div>
                    </div>
                    ${poll.description ? `<p class="card-description">${escapeHtml(poll.description)}</p>` : ''}
                    <div class="poll-stats">
                        <span class="stat-badge ${poll.is_active ? 'active' : 'inactive'}">
                            ${poll.is_active ? 'Active' : 'Inactive'}
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
            select.addEventListener('change', (e) => {
                const featureId = e.target.getAttribute('data-feature-id');
                const newStatus = e.target.value;
                updateFeatureStatus(featureId, newStatus);
            });
        });

    } catch (error) {
        console.error('Failed to load features:', error);
        container.innerHTML = '<div class="error-state">Failed to load feature requests. Please try again.</div>';
    }
}

async function updateFeatureStatus(featureId, status) {
    try {
        const response = await fetch(`${API_URL}/api/admin/features/${featureId}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ status })
        });

        if (response.ok) {
            showNotification('Feature status updated', 'success');
            // Update the status badge without reloading
            const card = document.querySelector(`[data-feature-id="${featureId}"]`).closest('.feature-card');
            const badge = card.querySelector('.status-badge');
            badge.className = `status-badge status-${status.replace('_', '-')}`;
            badge.textContent = formatStatus(status);
        } else {
            const data = await response.json();
            showNotification(data.error || 'Failed to update status', 'error');
        }
    } catch (error) {
        console.error('Failed to update feature status:', error);
        showNotification('Network error. Please try again.', 'error');
    }
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

function initFeaturesSection() {
    // Status filter
    document.getElementById('feature-status-filter').addEventListener('change', (e) => {
        const status = e.target.value || null;
        loadFeatures(status);
    });

    // Load features
    loadFeatures();
}

// ==================== Initialize ====================

document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initModals();
    initPollsSection();
    initFeaturesSection();

    console.log('Admin panel initialized');
});
