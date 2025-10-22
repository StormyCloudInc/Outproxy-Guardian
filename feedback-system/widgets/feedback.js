/**
 * Document Feedback Widget
 * Embeddable thumbs up/down feedback system
 *
 * Usage:
 * <div id="feedback-widget" data-document-id="page-123" data-api-url="http://your-api.com"></div>
 * <script src="http://your-api.com/widgets/feedback.js"></script>
 */

(function() {
    'use strict';

    class FeedbackWidget {
        constructor(container) {
            this.container = container;
            this.documentId = container.getAttribute('data-document-id');
            this.apiUrl = container.getAttribute('data-api-url') || 'http://localhost:5000';
            this.hasVoted = this.checkIfVoted();

            if (!this.documentId) {
                console.error('Feedback widget: data-document-id is required');
                return;
            }

            this.init();
        }

        checkIfVoted() {
            // Check localStorage to prevent multiple votes
            const key = `feedback_voted_${this.documentId}`;
            return localStorage.getItem(key) === 'true';
        }

        markAsVoted() {
            const key = `feedback_voted_${this.documentId}`;
            localStorage.setItem(key, 'true');
            this.hasVoted = true;
        }

        async init() {
            // Load current stats
            await this.loadStats();

            // Render widget
            this.render();

            // Load stats every 30 seconds
            setInterval(() => this.loadStats(true), 30000);
        }

        async loadStats(updateOnly = false) {
            try {
                const response = await fetch(`${this.apiUrl}/api/feedback/${this.documentId}/stats`);
                const stats = await response.json();

                this.stats = stats;

                if (updateOnly) {
                    this.updateStats();
                }
            } catch (error) {
                console.error('Failed to load feedback stats:', error);
                this.stats = { up: 0, down: 0 };
            }
        }

        async submitFeedback(type) {
            if (this.hasVoted) {
                this.showMessage('You have already provided feedback', 'info');
                return;
            }

            try {
                const response = await fetch(`${this.apiUrl}/api/feedback`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        document_id: this.documentId,
                        type: type
                    })
                });

                const data = await response.json();

                if (response.ok) {
                    this.stats = data.stats;
                    this.markAsVoted();
                    this.updateStats();
                    this.showMessage('Thank you for your feedback!', 'success');
                } else {
                    this.showMessage(data.error || 'Failed to submit feedback', 'error');
                }
            } catch (error) {
                console.error('Failed to submit feedback:', error);
                this.showMessage('Network error. Please try again.', 'error');
            }
        }

        render() {
            this.container.innerHTML = `
                <div class="feedback-widget">
                    <div class="feedback-title">Was this helpful?</div>
                    <div class="feedback-buttons">
                        <button class="feedback-btn feedback-up ${this.hasVoted ? 'disabled' : ''}"
                                ${this.hasVoted ? 'disabled' : ''}>
                            <span class="feedback-icon">👍</span>
                            <span class="feedback-count">${this.stats?.up || 0}</span>
                        </button>
                        <button class="feedback-btn feedback-down ${this.hasVoted ? 'disabled' : ''}"
                                ${this.hasVoted ? 'disabled' : ''}>
                            <span class="feedback-icon">👎</span>
                            <span class="feedback-count">${this.stats?.down || 0}</span>
                        </button>
                    </div>
                    <div class="feedback-message"></div>
                </div>
            `;

            // Add event listeners
            const upBtn = this.container.querySelector('.feedback-up');
            const downBtn = this.container.querySelector('.feedback-down');

            if (upBtn && !this.hasVoted) {
                upBtn.addEventListener('click', () => this.submitFeedback('up'));
            }

            if (downBtn && !this.hasVoted) {
                downBtn.addEventListener('click', () => this.submitFeedback('down'));
            }
        }

        updateStats() {
            const upCount = this.container.querySelector('.feedback-up .feedback-count');
            const downCount = this.container.querySelector('.feedback-down .feedback-count');

            if (upCount) upCount.textContent = this.stats.up || 0;
            if (downCount) downCount.textContent = this.stats.down || 0;
        }

        showMessage(message, type) {
            const messageEl = this.container.querySelector('.feedback-message');
            if (messageEl) {
                messageEl.textContent = message;
                messageEl.className = `feedback-message ${type}`;

                setTimeout(() => {
                    messageEl.textContent = '';
                    messageEl.className = 'feedback-message';
                }, 5000);
            }
        }
    }

    // Auto-initialize all feedback widgets
    function initWidgets() {
        const widgets = document.querySelectorAll('#feedback-widget:not([data-initialized])');
        widgets.forEach(widget => {
            widget.setAttribute('data-initialized', 'true');
            new FeedbackWidget(widget);
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
