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
            this.apiUrl = container.getAttribute('data-api-url') || 'https://feedback.stormycloud.org';
            this.mode = container.getAttribute('data-mode') || 'both';
            this.status = container.getAttribute('data-status') || null;
            this.maxItems = parseInt(container.getAttribute('data-max-items')) || 10;

            this.upvotedFeatures = this.loadUpvotedFeatures();
            this.commentsCache = {}; // Cache for loaded comments

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
                    // Close modal
                    this.closeModal();
                    // Reload list
                    await this.loadFeatures();
                    this.updateFeatureList();

                    // Handle subscription if email provided and subscribe checked
                    if (formData.subscribe && formData.email && data.feature && data.feature.id) {
                        await this.subscribeToFeature(data.feature.id, formData.email);
                    }
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

                    // Prompt user to subscribe for updates
                    setTimeout(() => this.promptSubscription(featureId), 1000);
                } else {
                    this.showMessage(data.error || 'Failed to upvote', 'error');
                }
            } catch (error) {
                console.error('Failed to upvote:', error);
                this.showMessage('Network error. Please try again.', 'error');
            }
        }

        async subscribeToFeature(featureId, email) {
            try {
                const response = await fetch(`${this.apiUrl}/api/features/${featureId}/subscribe`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ email })
                });

                if (response.ok) {
                    this.showMessage('Subscribed! You\'ll receive updates via email.', 'success');
                } else {
                    const data = await response.json();
                    console.error('Failed to subscribe:', data.error);
                }
            } catch (error) {
                console.error('Failed to subscribe:', error);
            }
        }

        promptSubscription(featureId) {
            // Check if user has already been prompted for this feature
            const prompted = localStorage.getItem(`prompted_subscribe_${featureId}`);
            if (prompted) {
                return;
            }

            // Mark as prompted
            localStorage.setItem(`prompted_subscribe_${featureId}`, 'true');

            // Open subscribe modal
            this.openSubscribeModal(featureId);
        }

        openSubscribeModal(featureId) {
            const modal = this.container.querySelector('#subscribe-modal');
            const featureIdInput = this.container.querySelector('#subscribe-feature-id');
            const emailInput = this.container.querySelector('#subscribe-email');

            if (modal && featureIdInput && emailInput) {
                featureIdInput.value = featureId;
                emailInput.value = '';
                modal.style.display = 'flex';
                document.body.style.overflow = 'hidden';
            }
        }

        closeSubscribeModal() {
            const modal = this.container.querySelector('#subscribe-modal');
            const form = this.container.querySelector('#subscribe-form');

            if (modal) {
                modal.style.display = 'none';
                document.body.style.overflow = '';
                if (form) form.reset();
            }
        }

        async loadComments(featureId) {
            try {
                const response = await fetch(`${this.apiUrl}/api/features/${featureId}/comments`);

                if (!response.ok) {
                    throw new Error('Failed to load comments');
                }

                const data = await response.json();
                this.commentsCache[featureId] = data.comments || [];
                return this.commentsCache[featureId];
            } catch (error) {
                console.error('Failed to load comments:', error);
                this.commentsCache[featureId] = [];
                return [];
            }
        }

        async submitComment(featureId, commentData) {
            try {
                const response = await fetch(`${this.apiUrl}/api/features/${featureId}/comments`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(commentData)
                });

                const data = await response.json();

                if (response.ok) {
                    this.showMessage('Comment posted successfully!', 'success');
                    // Reload comments
                    await this.loadComments(featureId);
                    // Update the comments display for this feature
                    await this.updateFeatureComments(featureId);
                    return true;
                } else {
                    this.showMessage(data.error || 'Failed to post comment', 'error');
                    return false;
                }
            } catch (error) {
                console.error('Failed to submit comment:', error);
                this.showMessage('Network error. Please try again.', 'error');
                return false;
            }
        }

        async toggleComments(featureId) {
            const commentsSection = this.container.querySelector(`#comments-${featureId}`);
            const toggleBtn = this.container.querySelector(`[data-toggle-comments="${featureId}"]`);

            if (!commentsSection) return;

            if (commentsSection.style.display === 'none' || !commentsSection.style.display) {
                // Load comments if not already loaded
                if (!this.commentsCache[featureId]) {
                    await this.loadComments(featureId);
                }
                await this.updateFeatureComments(featureId);
                commentsSection.style.display = 'block';
                if (toggleBtn) toggleBtn.textContent = '▼ Hide Comments';
            } else {
                commentsSection.style.display = 'none';
                if (toggleBtn) toggleBtn.textContent = `▶ Show Comments (${this.commentsCache[featureId]?.length || 0})`;
            }
        }

        async updateFeatureComments(featureId) {
            const commentsContainer = this.container.querySelector(`#comments-list-${featureId}`);
            if (!commentsContainer) return;

            const comments = this.commentsCache[featureId] || [];

            if (comments.length === 0) {
                commentsContainer.innerHTML = '<div class="comments-empty">No comments yet. Be the first to comment!</div>';
            } else {
                commentsContainer.innerHTML = comments.map(comment => this.renderComment(comment)).join('');
            }

            // Update comment count badge
            const countBadge = this.container.querySelector(`[data-comment-count="${featureId}"]`);
            if (countBadge) {
                countBadge.textContent = comments.length;
                if (comments.length === 0) {
                    countBadge.style.display = 'none';
                } else {
                    countBadge.style.display = 'inline-block';
                }
            }
        }

        renderComment(comment) {
            const authorName = this.escapeHtml(comment.author_name || 'Anonymous');
            const commentText = this.escapeHtml(comment.comment_text);
            const date = this.formatDate(comment.created_at);

            return `
                <div class="comment-item">
                    <div class="comment-header">
                        <span class="comment-author">${authorName}</span>
                        <span class="comment-date">${date}</span>
                    </div>
                    <div class="comment-text">${commentText}</div>
                </div>
            `;
        }

        render() {
            let html = '<div class="features-widget">';

            // Feature list (always shown)
            if (this.mode === 'list' || this.mode === 'both') {
                html += this.renderFeatureList();
            }

            // Submit form in modal
            html += this.renderModal();

            // Subscribe modal
            html += this.renderSubscribeModal();

            html += '<div class="features-message"></div>';
            html += '</div>';

            this.container.innerHTML = html;

            // Add event listeners
            this.attachEventListeners();
        }

        renderModal() {
            return `
                <div class="features-modal" id="features-modal" style="display: none;">
                    <div class="features-modal-overlay"></div>
                    <div class="features-modal-content">
                        <div class="features-modal-header">
                            <h3>Submit a Feature Request</h3>
                            <button class="features-modal-close">&times;</button>
                        </div>
                        <form class="features-form" id="feature-submit-form">
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
                            <div class="features-form-group" style="margin-bottom: 0;">
                                <label class="features-form-checkbox">
                                    <input type="checkbox" id="feature-subscribe" name="subscribe">
                                    <span>Notify me when the status of this feature changes</span>
                                </label>
                            </div>
                        </form>
                        <div class="features-modal-footer">
                            <button type="submit" form="feature-submit-form" class="features-btn features-btn-primary">Submit Feature</button>
                        </div>
                    </div>
                </div>
            `;
        }

        renderSubscribeModal() {
            return `
                <div class="features-modal" id="subscribe-modal" style="display: none;">
                    <div class="features-modal-overlay"></div>
                    <div class="features-modal-content" style="max-width: 450px;">
                        <div class="features-modal-header">
                            <h3>Get Status Updates</h3>
                            <button class="subscribe-modal-close">&times;</button>
                        </div>
                        <div style="padding: 20px;">
                            <p style="margin-bottom: 20px; color: #555; line-height: 1.6;">
                                Want to be notified when the status of this feature changes? Enter your email below.
                            </p>
                            <form id="subscribe-form">
                                <input type="hidden" id="subscribe-feature-id" value="">
                                <div class="features-form-group">
                                    <label for="subscribe-email">Email Address *</label>
                                    <input type="email" id="subscribe-email" name="email" required
                                           placeholder="your@email.com" style="width: 100%;">
                                </div>
                                <div class="features-modal-footer" style="border-top: none; padding: 0; margin-top: 20px;">
                                    <button type="button" class="features-btn features-btn-secondary subscribe-modal-close">No Thanks</button>
                                    <button type="submit" class="features-btn features-btn-primary">Subscribe</button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            `;
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
                    <div class="features-list-header">
                        <h3 class="features-list-title">Feature Requests</h3>
                        <button class="features-submit-btn-link">+ Submit Feature Request</button>
                    </div>
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
                                <div class="feature-actions">
                                    <button class="feature-comments-toggle" data-toggle-comments="${feature.id}">
                                        ▶ Show Comments <span class="comment-count-badge" data-comment-count="${feature.id}" style="display: none;">0</span>
                                    </button>
                                </div>
                                <div class="feature-comments-section" id="comments-${feature.id}" style="display: none;">
                                    <div class="comments-list" id="comments-list-${feature.id}">
                                        <div class="comments-empty">No comments yet. Be the first to comment!</div>
                                    </div>
                                    <form class="comment-form" data-feature-id="${feature.id}">
                                        <textarea class="comment-input" name="comment" placeholder="Add your comment..." rows="3" required minlength="10" maxlength="2000"></textarea>
                                        <div class="comment-form-row">
                                            <input type="text" class="comment-name" name="name" placeholder="Your name (optional)" maxlength="100">
                                            <input type="email" class="comment-email" name="email" placeholder="Email (optional)" maxlength="255">
                                        </div>
                                        <button type="submit" class="comment-submit-btn">Post Comment</button>
                                    </form>
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
                this.attachCommentListeners();

                // Reload comment counts
                this.features.forEach(async feature => {
                    await this.loadComments(feature.id);
                    this.updateFeatureComments(feature.id);
                });
            }
        }

        attachEventListeners() {
            // Submit button to open modal
            const submitBtn = this.container.querySelector('.features-submit-btn-link');
            if (submitBtn) {
                submitBtn.addEventListener('click', () => {
                    this.openModal();
                });
            }

            // Modal close buttons
            const closeButtons = this.container.querySelectorAll('.features-modal-close');
            closeButtons.forEach(btn => {
                btn.addEventListener('click', () => {
                    this.closeModal();
                });
            });

            // Modal overlay click to close
            const overlay = this.container.querySelector('.features-modal-overlay');
            if (overlay) {
                overlay.addEventListener('click', () => {
                    this.closeModal();
                });
            }

            // Form submission
            const form = this.container.querySelector('.features-form');
            if (form) {
                form.addEventListener('submit', (e) => {
                    e.preventDefault();
                    const formData = {
                        title: form.title.value,
                        description: form.description.value,
                        name: form.name.value,
                        email: form.email.value,
                        subscribe: form.subscribe.checked
                    };
                    this.submitFeature(formData);
                });
            }

            // Subscribe modal close buttons
            const subscribeCloseButtons = this.container.querySelectorAll('.subscribe-modal-close');
            subscribeCloseButtons.forEach(btn => {
                btn.addEventListener('click', () => {
                    this.closeSubscribeModal();
                });
            });

            // Subscribe modal overlay click to close
            const subscribeOverlay = this.container.querySelector('#subscribe-modal .features-modal-overlay');
            if (subscribeOverlay) {
                subscribeOverlay.addEventListener('click', () => {
                    this.closeSubscribeModal();
                });
            }

            // Subscribe form submission
            const subscribeForm = this.container.querySelector('#subscribe-form');
            if (subscribeForm) {
                subscribeForm.addEventListener('submit', (e) => {
                    e.preventDefault();
                    const featureId = parseInt(this.container.querySelector('#subscribe-feature-id').value);
                    const email = this.container.querySelector('#subscribe-email').value.trim();

                    if (email && email.includes('@')) {
                        this.subscribeToFeature(featureId, email);
                        this.closeSubscribeModal();
                    } else {
                        this.showMessage('Please enter a valid email address', 'error');
                    }
                });
            }

            this.attachUpvoteListeners();
            this.attachCommentListeners();
        }

        attachCommentListeners() {
            // Comment toggle buttons
            const toggleBtns = this.container.querySelectorAll('.feature-comments-toggle');
            toggleBtns.forEach(btn => {
                btn.addEventListener('click', () => {
                    const featureId = parseInt(btn.getAttribute('data-toggle-comments'));
                    this.toggleComments(featureId);
                });
            });

            // Comment forms
            const commentForms = this.container.querySelectorAll('.comment-form');
            commentForms.forEach(form => {
                form.addEventListener('submit', async (e) => {
                    e.preventDefault();
                    const featureId = parseInt(form.getAttribute('data-feature-id'));
                    const commentData = {
                        comment: form.comment.value.trim(),
                        name: form.name.value.trim() || null,
                        email: form.email.value.trim() || null
                    };

                    const success = await this.submitComment(featureId, commentData);
                    if (success) {
                        form.reset(); // Clear the form
                    }
                });
            });
        }

        openModal() {
            const modal = this.container.querySelector('.features-modal');
            if (modal) {
                modal.style.display = 'flex';
                document.body.style.overflow = 'hidden';
            }
        }

        closeModal() {
            const modal = this.container.querySelector('.features-modal');
            if (modal) {
                modal.style.display = 'none';
                document.body.style.overflow = '';
                // Clear form
                const form = this.container.querySelector('.features-form');
                if (form) form.reset();
            }
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
