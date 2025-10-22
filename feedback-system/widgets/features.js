/**
 * Feature Request Widget
 * Embeddable feature request and upvoting system
 *
 * Usage:
 * <div id="features-widget" data-api-url="http://your-api.com" data-mode="list"></div>
 * <script src="http://your-api.com/widgets/features.js"></script>
 *
 * Modes:
 * - list: Show list of features with upvoting
 * - submit: Show submit form
 * - both: Show both submit form and list (default)
 */

(function() {
    'use strict';

    class FeaturesWidget {
        constructor(container) {
            this.container = container;
            this.apiUrl = container.getAttribute('data-api-url') || 'http://localhost:5000';
            this.mode = container.getAttribute('data-mode') || 'both';
            this.status = container.getAttribute('data-status') || null;
            this.maxItems = parseInt(container.getAttribute('data-max-items')) || 10;

            this.upvotedFeatures = this.loadUpvotedFeatures();

            this.init();
        }

        loadUpvotedFeatures() {
            const stored = localStorage.getItem('upvoted_features');
            return stored ? JSON.parse(stored) : [];
        }

        saveUpvotedFeatures() {
            localStorage.setItem('upvoted_features', JSON.stringify(this.upvotedFeatures));
        }

        hasUpvoted(featureId) {
            return this.upvotedFeatures.includes(featureId);
        }

        markAsUpvoted(featureId) {
            if (!this.hasUpvoted(featureId)) {
                this.upvotedFeatures.push(featureId);
                this.saveUpvotedFeatures();
            }
        }

        async init() {
            if (this.mode === 'list' || this.mode === 'both') {
                await this.loadFeatures();
            }

            this.render();

            // Refresh every 30 seconds
            if (this.mode === 'list' || this.mode === 'both') {
                setInterval(() => this.loadFeatures(true), 30000);
            }
        }

        async loadFeatures(updateOnly = false) {
            try {
                let url = `${this.apiUrl}/api/features?sort_by=upvote_count`;
                if (this.status) {
                    url += `&status=${this.status}`;
                }

                const response = await fetch(url);

                if (!response.ok) {
                    throw new Error('Failed to load features');
                }

                const data = await response.json();
                this.features = data.slice(0, this.maxItems);

                if (updateOnly) {
                    this.updateFeatureList();
                }
            } catch (error) {
                console.error('Failed to load features:', error);
                this.features = [];
            }
        }

        async submitFeature(formData) {
            try {
                const response = await fetch(`${this.apiUrl}/api/features`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        title: formData.title,
                        description: formData.description,
                        name: formData.name || null,
                        email: formData.email || null
                    })
                });

                const data = await response.json();

                if (response.ok) {
                    this.showMessage('Feature request submitted successfully!', 'success');
                    // Clear form
                    const form = this.container.querySelector('.features-form');
                    if (form) form.reset();
                    // Reload list
                    await this.loadFeatures();
                    this.updateFeatureList();
                } else {
                    this.showMessage(data.error || 'Failed to submit feature', 'error');
                }
            } catch (error) {
                console.error('Failed to submit feature:', error);
                this.showMessage('Network error. Please try again.', 'error');
            }
        }

        async upvoteFeature(featureId) {
            if (this.hasUpvoted(featureId)) {
                this.showMessage('You have already upvoted this feature', 'info');
                return;
            }

            try {
                const response = await fetch(`${this.apiUrl}/api/features/${featureId}/upvote`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });

                const data = await response.json();

                if (response.ok) {
                    this.markAsUpvoted(featureId);
                    this.showMessage('Upvote recorded!', 'success');
                    await this.loadFeatures();
                    this.updateFeatureList();
                } else {
                    this.showMessage(data.error || 'Failed to upvote', 'error');
                }
            } catch (error) {
                console.error('Failed to upvote:', error);
                this.showMessage('Network error. Please try again.', 'error');
            }
        }

        render() {
            let html = '<div class="features-widget">';

            // Submit form
            if (this.mode === 'submit' || this.mode === 'both') {
                html += this.renderSubmitForm();
            }

            // Feature list
            if (this.mode === 'list' || this.mode === 'both') {
                html += this.renderFeatureList();
            }

            html += '<div class="features-message"></div>';
            html += '</div>';

            this.container.innerHTML = html;

            // Add event listeners
            this.attachEventListeners();
        }

        renderSubmitForm() {
            return `
                <div class="features-submit">
                    <h3 class="features-submit-title">Submit a Feature Request</h3>
                    <form class="features-form">
                        <div class="features-form-group">
                            <label for="feature-title">Title *</label>
                            <input type="text" id="feature-title" name="title" required
                                   placeholder="Brief description of the feature">
                        </div>
                        <div class="features-form-group">
                            <label for="feature-description">Description *</label>
                            <textarea id="feature-description" name="description" required
                                      placeholder="Detailed explanation of what you'd like to see"
                                      rows="4"></textarea>
                        </div>
                        <div class="features-form-row">
                            <div class="features-form-group">
                                <label for="feature-name">Your Name (optional)</label>
                                <input type="text" id="feature-name" name="name"
                                       placeholder="Anonymous">
                            </div>
                            <div class="features-form-group">
                                <label for="feature-email">Email (optional)</label>
                                <input type="email" id="feature-email" name="email"
                                       placeholder="For updates on your request">
                            </div>
                        </div>
                        <button type="submit" class="features-submit-btn">Submit Feature</button>
                    </form>
                </div>
            `;
        }

        renderFeatureList() {
            let html = `
                <div class="features-list">
                    <h3 class="features-list-title">Feature Requests</h3>
            `;

            if (!this.features || this.features.length === 0) {
                html += '<div class="features-empty">No feature requests yet. Be the first to submit one!</div>';
            } else {
                html += '<div class="features-items">';
                this.features.forEach(feature => {
                    const hasUpvoted = this.hasUpvoted(feature.id);
                    const statusClass = `status-${feature.status.replace('_', '-')}`;

                    html += `
                        <div class="feature-item" data-feature-id="${feature.id}">
                            <div class="feature-upvote">
                                <button class="feature-upvote-btn ${hasUpvoted ? 'upvoted' : ''}"
                                        data-feature-id="${feature.id}"
                                        ${hasUpvoted ? 'disabled' : ''}>
                                    <span class="feature-upvote-icon">▲</span>
                                    <span class="feature-upvote-count">${feature.upvote_count}</span>
                                </button>
                            </div>
                            <div class="feature-content">
                                <div class="feature-header">
                                    <h4 class="feature-title">${this.escapeHtml(feature.title)}</h4>
                                    <span class="feature-status ${statusClass}">${this.formatStatus(feature.status)}</span>
                                </div>
                                <p class="feature-description">${this.escapeHtml(feature.description)}</p>
                                <div class="feature-meta">
                                    ${feature.submitter_name ? `by ${this.escapeHtml(feature.submitter_name)} • ` : ''}
                                    ${this.formatDate(feature.created_at)}
                                </div>
                            </div>
                        </div>
                    `;
                });
                html += '</div>';
            }

            html += '</div>';
            return html;
        }

        updateFeatureList() {
            const listContainer = this.container.querySelector('.features-items');
            if (!listContainer) return;

            // Re-render just the list
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = this.renderFeatureList();

            const newItems = tempDiv.querySelector('.features-items');
            if (newItems) {
                listContainer.innerHTML = newItems.innerHTML;
                this.attachUpvoteListeners();
            }
        }

        attachEventListeners() {
            // Form submission
            const form = this.container.querySelector('.features-form');
            if (form) {
                form.addEventListener('submit', (e) => {
                    e.preventDefault();
                    const formData = {
                        title: form.title.value,
                        description: form.description.value,
                        name: form.name.value,
                        email: form.email.value
                    };
                    this.submitFeature(formData);
                });
            }

            this.attachUpvoteListeners();
        }

        attachUpvoteListeners() {
            // Upvote buttons
            const upvoteBtns = this.container.querySelectorAll('.feature-upvote-btn:not([disabled])');
            upvoteBtns.forEach(btn => {
                btn.addEventListener('click', () => {
                    const featureId = parseInt(btn.getAttribute('data-feature-id'));
                    this.upvoteFeature(featureId);
                });
            });
        }

        showMessage(message, type) {
            const messageEl = this.container.querySelector('.features-message');
            if (messageEl) {
                messageEl.textContent = message;
                messageEl.className = `features-message ${type}`;

                setTimeout(() => {
                    messageEl.textContent = '';
                    messageEl.className = 'features-message';
                }, 5000);
            }
        }

        formatStatus(status) {
            return status.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        }

        formatDate(dateString) {
            const date = new Date(dateString);
            const now = new Date();
            const diffMs = now - date;
            const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

            if (diffDays === 0) return 'Today';
            if (diffDays === 1) return 'Yesterday';
            if (diffDays < 7) return `${diffDays} days ago`;
            if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
            if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
            return date.toLocaleDateString();
        }

        escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    }

    // Auto-initialize all feature widgets
    function initWidgets() {
        const widgets = document.querySelectorAll('#features-widget:not([data-initialized])');
        widgets.forEach(widget => {
            widget.setAttribute('data-initialized', 'true');
            new FeaturesWidget(widget);
        });
    }

    // Initialize on load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initWidgets);
    } else {
        initWidgets();
    }

    // Watch for dynamically added widgets
    if (typeof MutationObserver !== 'undefined') {
        const observer = new MutationObserver(initWidgets);
        observer.observe(document.body, { childList: true, subtree: true });
    }
})();
