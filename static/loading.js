// Advanced Loading Animations System
(function() {
    // Loading messages for different contexts
    const loadingMessages = {
        explore: [
            'A descobrir a essência do livro...',
            'A analisar a obra literária...',
            'A preparar insights únicos...',
            'A mergulhar nas páginas...'
        ],
        analyze: [
            'A analisar profundamente...',
            'A extrair informações...',
            'A processar conteúdo...',
            'A gerar análise detalhada...'
        ],
        compare: [
            'A comparar as obras...',
            'A encontrar semelhanças...',
            'A identificar diferenças...',
            'A criar análise comparativa...'
        ],
        recommend: [
            'A analisar os teus gostos...',
            'A procurar livros perfeitos...',
            'A personalizar sugestões...',
            'A preparar recomendações...'
        ],
        chat: [
            'A pensar na resposta...',
            'A formular ideias...',
            'A preparar a resposta...'
        ],
        quiz: [
            'A criar perguntas...',
            'A preparar o quiz...',
            'A gerar desafios...'
        ],
        default: [
            'A processar...',
            'A gerar conteúdo...',
            'Quase lá...',
            'A preparar...'
        ]
    };

    // Book-related emojis for animation
    const bookEmojis = ['📚', '📖', '📕', '📗', '📘', '📙', '✨', '🔮', '💫', '🌟'];

    // Create loading overlay
    window.showLoadingOverlay = function(type = 'default', customMessage = null) {
        // Remove existing overlay
        hideLoadingOverlay();

        const messages = loadingMessages[type] || loadingMessages.default;
        const randomMessage = customMessage || messages[Math.floor(Math.random() * messages.length)];

        const overlay = document.createElement('div');
        overlay.id = 'loading-overlay';
        overlay.innerHTML = `
            <style>
                #loading-overlay {
                    position: fixed;
                    inset: 0;
                    background: rgba(0, 0, 0, 0.8);
                    backdrop-filter: blur(8px);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 9999;
                    animation: fadeIn 0.3s ease;
                }
                @keyframes fadeIn {
                    from { opacity: 0; }
                    to { opacity: 1; }
                }
                .loading-container {
                    text-align: center;
                    padding: 40px;
                }
                .loading-book {
                    font-size: 64px;
                    animation: bookBounce 1s ease-in-out infinite;
                    margin-bottom: 24px;
                }
                @keyframes bookBounce {
                    0%, 100% { transform: translateY(0) rotate(0deg); }
                    25% { transform: translateY(-20px) rotate(-5deg); }
                    75% { transform: translateY(-20px) rotate(5deg); }
                }
                .loading-spinner {
                    width: 60px;
                    height: 60px;
                    margin: 0 auto 24px;
                    position: relative;
                }
                .loading-spinner::before,
                .loading-spinner::after {
                    content: '';
                    position: absolute;
                    inset: 0;
                    border-radius: 50%;
                    border: 3px solid transparent;
                }
                .loading-spinner::before {
                    border-top-color: #a855f7;
                    border-right-color: #a855f7;
                    animation: spin 1s linear infinite;
                }
                .loading-spinner::after {
                    border-bottom-color: #ec4899;
                    border-left-color: #ec4899;
                    animation: spin 1s linear infinite reverse;
                    inset: 6px;
                }
                @keyframes spin {
                    to { transform: rotate(360deg); }
                }
                .loading-message {
                    color: white;
                    font-size: 1.1rem;
                    font-weight: 500;
                    margin-bottom: 16px;
                    animation: pulse 2s ease-in-out infinite;
                }
                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.6; }
                }
                .loading-dots {
                    display: flex;
                    justify-content: center;
                    gap: 8px;
                }
                .loading-dot {
                    width: 10px;
                    height: 10px;
                    background: linear-gradient(135deg, #a855f7, #ec4899);
                    border-radius: 50%;
                    animation: dotBounce 1.4s ease-in-out infinite;
                }
                .loading-dot:nth-child(1) { animation-delay: 0s; }
                .loading-dot:nth-child(2) { animation-delay: 0.2s; }
                .loading-dot:nth-child(3) { animation-delay: 0.4s; }
                @keyframes dotBounce {
                    0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; }
                    40% { transform: scale(1); opacity: 1; }
                }
                .loading-progress {
                    width: 200px;
                    height: 4px;
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 2px;
                    margin: 20px auto 0;
                    overflow: hidden;
                }
                .loading-progress-bar {
                    height: 100%;
                    background: linear-gradient(90deg, #a855f7, #ec4899, #a855f7);
                    background-size: 200% 100%;
                    animation: progressShimmer 2s linear infinite;
                    width: 100%;
                }
                @keyframes progressShimmer {
                    0% { background-position: 200% 0; }
                    100% { background-position: -200% 0; }
                }
                .loading-tip {
                    color: rgba(255, 255, 255, 0.5);
                    font-size: 0.85rem;
                    margin-top: 24px;
                    max-width: 300px;
                }
            </style>
            <div class="loading-container">
                <div class="loading-book" id="loading-emoji">📚</div>
                <div class="loading-spinner"></div>
                <div class="loading-message" id="loading-message">${randomMessage}</div>
                <div class="loading-dots">
                    <div class="loading-dot"></div>
                    <div class="loading-dot"></div>
                    <div class="loading-dot"></div>
                </div>
                <div class="loading-progress">
                    <div class="loading-progress-bar"></div>
                </div>
                <div class="loading-tip">💡 Dica: Quanto mais específico o título, melhores os resultados!</div>
            </div>
        `;
        document.body.appendChild(overlay);

        // Rotate emojis
        let emojiIndex = 0;
        const emojiEl = document.getElementById('loading-emoji');
        const emojiInterval = setInterval(() => {
            emojiIndex = (emojiIndex + 1) % bookEmojis.length;
            if (emojiEl) emojiEl.textContent = bookEmojis[emojiIndex];
        }, 800);

        // Rotate messages
        let messageIndex = 0;
        const messageEl = document.getElementById('loading-message');
        const messageInterval = setInterval(() => {
            messageIndex = (messageIndex + 1) % messages.length;
            if (messageEl) {
                messageEl.style.opacity = '0';
                setTimeout(() => {
                    messageEl.textContent = messages[messageIndex];
                    messageEl.style.opacity = '1';
                }, 200);
            }
        }, 3000);

        // Store intervals for cleanup
        overlay.dataset.emojiInterval = emojiInterval;
        overlay.dataset.messageInterval = messageInterval;

        return overlay;
    };

    // Hide loading overlay
    window.hideLoadingOverlay = function() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            clearInterval(parseInt(overlay.dataset.emojiInterval));
            clearInterval(parseInt(overlay.dataset.messageInterval));
            overlay.style.opacity = '0';
            setTimeout(() => overlay.remove(), 300);
        }
    };

    // Inline loading indicator for buttons
    window.setButtonLoading = function(button, loading = true, originalText = null) {
        if (loading) {
            button.dataset.originalText = button.innerHTML;
            button.disabled = true;
            button.innerHTML = `
                <span class="inline-flex items-center gap-2">
                    <svg class="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span class="animate-pulse">A processar...</span>
                </span>
            `;
        } else {
            button.disabled = false;
            button.innerHTML = originalText || button.dataset.originalText || 'Concluído';
        }
    };

    // Skeleton loader for content areas
    window.showSkeletonLoader = function(container, lines = 5) {
        const skeleton = document.createElement('div');
        skeleton.className = 'skeleton-loader';
        skeleton.innerHTML = `
            <style>
                .skeleton-loader {
                    padding: 16px;
                }
                .skeleton-line {
                    height: 16px;
                    background: linear-gradient(90deg, rgba(255,255,255,0.05) 25%, rgba(255,255,255,0.1) 50%, rgba(255,255,255,0.05) 75%);
                    background-size: 200% 100%;
                    animation: skeletonShimmer 1.5s infinite;
                    border-radius: 4px;
                    margin-bottom: 12px;
                }
                .skeleton-line:last-child {
                    width: 60%;
                }
                .skeleton-line:nth-child(odd) {
                    width: 90%;
                }
                @keyframes skeletonShimmer {
                    0% { background-position: 200% 0; }
                    100% { background-position: -200% 0; }
                }
            </style>
            ${Array(lines).fill('<div class="skeleton-line"></div>').join('')}
        `;
        container.innerHTML = '';
        container.appendChild(skeleton);
        return skeleton;
    };

    // Typing effect for AI responses
    window.typeWriter = function(element, text, speed = 20) {
        return new Promise((resolve) => {
            element.innerHTML = '';
            let i = 0;
            const cursor = document.createElement('span');
            cursor.className = 'typing-cursor';
            cursor.innerHTML = '|';
            cursor.style.cssText = 'animation: blink 1s infinite; margin-left: 2px;';
            
            // Add blink animation if not exists
            if (!document.getElementById('typing-cursor-style')) {
                const style = document.createElement('style');
                style.id = 'typing-cursor-style';
                style.innerHTML = '@keyframes blink { 0%, 50% { opacity: 1; } 51%, 100% { opacity: 0; } }';
                document.head.appendChild(style);
            }

            function type() {
                if (i < text.length) {
                    element.innerHTML = text.substring(0, i + 1);
                    element.appendChild(cursor);
                    i++;
                    setTimeout(type, speed);
                } else {
                    cursor.remove();
                    resolve();
                }
            }
            type();
        });
    };

    // Progress indicator with steps
    window.showStepProgress = function(container, steps, currentStep) {
        container.innerHTML = `
            <div class="flex items-center justify-center gap-2 py-4">
                ${steps.map((step, i) => `
                    <div class="flex items-center">
                        <div class="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-all
                            ${i < currentStep ? 'bg-green-500 text-white' : 
                              i === currentStep ? 'bg-purple-500 text-white animate-pulse' : 
                              'bg-white/10 text-gray-400'}">
                            ${i < currentStep ? '✓' : i + 1}
                        </div>
                        ${i < steps.length - 1 ? `
                            <div class="w-12 h-1 mx-1 rounded ${i < currentStep ? 'bg-green-500' : 'bg-white/10'}"></div>
                        ` : ''}
                    </div>
                `).join('')}
            </div>
            <p class="text-center text-sm text-purple-300">${steps[currentStep] || ''}</p>
        `;
    };
})();
