/**
 * Voting/Poll Widget
 * Embeddable voting system for polls
 *
 * Usage:
 * <div id="poll-widget" data-poll-id="1" data-api-url="http://your-api.com"></div>
 * <script src="http://your-api.com/widgets/voting.js"></script>
 */

(function() {
    'use strict';

    class PollWidget {
        constructor(container) {
            this.container = container;
            this.pollId = container.getAttribute('data-poll-id');
            this.apiUrl = container.getAttribute('data-api-url') || 'http://localhost:5000';
            this.showResults = container.getAttribute('data-show-results') === 'true';
            this.hasVoted = this.checkIfVoted();

            if (!this.pollId) {
                console.error('Poll widget: data-poll-id is required');
                return;
            }

            this.init();
        }

        checkIfVoted() {
            const key = `poll_voted_${this.pollId}`;
            return localStorage.getItem(key) === 'true';
        }

        markAsVoted() {
            const key = `poll_voted_${this.pollId}`;
            localStorage.setItem(key, 'true');
            this.hasVoted = true;
        }

        async init() {
            await this.loadPoll();
            this.render();

            // Refresh results every 10 seconds if showing results
            if (this.showResults || this.hasVoted) {
                setInterval(() => this.loadPoll(true), 10000);
            }
        }

        async loadPoll(updateOnly = false) {
            try {
                const response = await fetch(`${this.apiUrl}/api/polls/${this.pollId}`);

                if (!response.ok) {
                    throw new Error('Failed to load poll');
                }

                const data = await response.json();
                this.pollData = data;

                if (updateOnly) {
                    this.updateResults();
                }
            } catch (error) {
                console.error('Failed to load poll:', error);
                this.container.innerHTML = '<div class="poll-error">Failed to load poll</div>';
            }
        }

        async submitVote(optionId) {
            if (this.hasVoted) {
                this.showMessage('You have already voted', 'info');
                return;
            }

            try {
                const response = await fetch(`${this.apiUrl}/api/polls/${this.pollId}/vote`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        option_id: optionId
                    })
                });

                const data = await response.json();

                if (response.ok) {
                    this.pollData = data.poll;
                    this.markAsVoted();
                    this.showMessage('Vote recorded successfully!', 'success');
                    this.render();
                } else {
                    this.showMessage(data.error || 'Failed to submit vote', 'error');
                }
            } catch (error) {
                console.error('Failed to submit vote:', error);
                this.showMessage('Network error. Please try again.', 'error');
            }
        }

        render() {
            const poll = this.pollData.poll;
            const options = this.pollData.options;

            const totalVotes = options.reduce((sum, opt) => sum + opt.vote_count, 0);

            let optionsHtml = '';

            if (this.hasVoted || this.showResults) {
                // Show results
                optionsHtml = options.map(option => {
                    const percentage = totalVotes > 0
                        ? Math.round((option.vote_count / totalVotes) * 100)
                        : 0;

                    return `
                        <div class="poll-option-result">
                            <div class="poll-option-text">${this.escapeHtml(option.option_text)}</div>
                            <div class="poll-option-bar">
                                <div class="poll-option-bar-fill" style="width: ${percentage}%"></div>
                                <div class="poll-option-stats">${option.vote_count} votes (${percentage}%)</div>
                            </div>
                        </div>
                    `;
                }).join('');
            } else {
                // Show voting options
                optionsHtml = options.map(option => `
                    <button class="poll-option-btn" data-option-id="${option.id}">
                        ${this.escapeHtml(option.option_text)}
                    </button>
                `).join('');
            }

            this.container.innerHTML = `
                <div class="poll-widget">
                    <div class="poll-title">${this.escapeHtml(poll.title)}</div>
                    ${poll.description ? `<div class="poll-description">${this.escapeHtml(poll.description)}</div>` : ''}
                    <div class="poll-options">
                        ${optionsHtml}
                    </div>
                    <div class="poll-footer">
                        <span class="poll-total-votes">${totalVotes} total votes</span>
                    </div>
                    <div class="poll-message"></div>
                </div>
            `;

            // Add event listeners for voting buttons
            if (!this.hasVoted && !this.showResults) {
                const buttons = this.container.querySelectorAll('.poll-option-btn');
                buttons.forEach(btn => {
                    btn.addEventListener('click', () => {
                        const optionId = btn.getAttribute('data-option-id');
                        this.submitVote(parseInt(optionId));
                    });
                });
            }
        }

        updateResults() {
            if (!this.hasVoted && !this.showResults) return;

            const options = this.pollData.options;
            const totalVotes = options.reduce((sum, opt) => sum + opt.vote_count, 0);

            // Update total votes
            const totalEl = this.container.querySelector('.poll-total-votes');
            if (totalEl) {
                totalEl.textContent = `${totalVotes} total votes`;
            }

            // Update each option
            const resultElements = this.container.querySelectorAll('.poll-option-result');
            resultElements.forEach((el, index) => {
                if (options[index]) {
                    const option = options[index];
                    const percentage = totalVotes > 0
                        ? Math.round((option.vote_count / totalVotes) * 100)
                        : 0;

                    const barFill = el.querySelector('.poll-option-bar-fill');
                    const stats = el.querySelector('.poll-option-stats');

                    if (barFill) barFill.style.width = `${percentage}%`;
                    if (stats) stats.textContent = `${option.vote_count} votes (${percentage}%)`;
                }
            });
        }

        showMessage(message, type) {
            const messageEl = this.container.querySelector('.poll-message');
            if (messageEl) {
                messageEl.textContent = message;
                messageEl.className = `poll-message ${type}`;

                setTimeout(() => {
                    messageEl.textContent = '';
                    messageEl.className = 'poll-message';
                }, 5000);
            }
        }

        escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    }

    // Auto-initialize all poll widgets
    function initWidgets() {
        const widgets = document.querySelectorAll('#poll-widget:not([data-initialized])');
        widgets.forEach(widget => {
            widget.setAttribute('data-initialized', 'true');
            new PollWidget(widget);
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
