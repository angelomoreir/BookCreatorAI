// Onboarding Tutorial System
(function() {
    const ONBOARDING_KEY = 'alma_onboarding_completed';
    
    // Tutorial steps configuration
    const tutorialSteps = [
        {
            target: null,
            title: '👋 Bem-vindo ao Alma do Livro!',
            content: 'Descobre a essência de qualquer livro com a ajuda da inteligência artificial. Vamos mostrar-te como funciona!',
            position: 'center',
            icon: '📚'
        },
        {
            target: '#bookTitle',
            title: '📖 Pesquisa um Livro',
            content: 'Começa por escrever o título do livro que queres explorar. Podes adicionar o autor para resultados mais precisos.',
            position: 'bottom',
            icon: '🔍'
        },
        {
            target: '#exploreBtn',
            title: '🚀 Explorar',
            content: 'Clica aqui para começar a explorar o livro. A IA vai analisar e preparar várias funcionalidades interativas.',
            position: 'bottom',
            icon: '✨'
        },
        {
            target: null,
            title: '🎯 Aspectos do Livro',
            content: 'Depois de explorar, podes descobrir diferentes aspectos: resumo, personagens, temas, citações e muito mais! Cada aspecto revela uma camada diferente da obra.',
            position: 'center',
            icon: '📊'
        },
        {
            target: null,
            title: '🎮 Funcionalidades Interativas',
            content: 'Entrevista personagens, faz quizzes, cria playlists, e até escreve finais alternativos! A criatividade é o limite.',
            position: 'center',
            icon: '🎭'
        },
        {
            target: null,
            title: '⭐ Favoritos e Histórico',
            content: 'Guarda os teus livros favoritos e acompanha o teu histórico de leitura. Tudo fica guardado para ti!',
            position: 'center',
            icon: '📚'
        },
        {
            target: null,
            title: '🎯 Recomendações Personalizadas',
            content: 'Quanto mais explorares, melhores serão as recomendações da IA baseadas nos teus gostos!',
            position: 'center',
            icon: '💡'
        },
        {
            target: null,
            title: '🎉 Estás pronto!',
            content: 'Agora já sabes tudo! Começa a explorar o mundo dos livros. Boas descobertas!',
            position: 'center',
            icon: '🚀'
        }
    ];

    let currentStep = 0;
    let overlay = null;
    let tooltip = null;

    // Check if onboarding should show
    function shouldShowOnboarding() {
        return !localStorage.getItem(ONBOARDING_KEY);
    }

    // Mark onboarding as completed
    function completeOnboarding() {
        localStorage.setItem(ONBOARDING_KEY, 'true');
    }

    // Create overlay element
    function createOverlay() {
        overlay = document.createElement('div');
        overlay.id = 'onboarding-overlay';
        overlay.innerHTML = `
            <style>
                #onboarding-overlay {
                    position: fixed;
                    inset: 0;
                    background: rgba(0, 0, 0, 0.85);
                    z-index: 9998;
                    transition: opacity 0.3s ease;
                }
                #onboarding-tooltip {
                    position: fixed;
                    z-index: 10000;
                    max-width: 400px;
                    background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%);
                    border: 1px solid rgba(139, 92, 246, 0.5);
                    border-radius: 16px;
                    padding: 24px;
                    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5), 0 0 30px rgba(139, 92, 246, 0.3);
                    animation: tooltipAppear 0.3s ease;
                }
                @keyframes tooltipAppear {
                    from { opacity: 0; transform: translateY(10px) scale(0.95); }
                    to { opacity: 1; transform: translateY(0) scale(1); }
                }
                #onboarding-tooltip.center {
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                }
                .onboarding-icon {
                    font-size: 48px;
                    text-align: center;
                    margin-bottom: 16px;
                }
                .onboarding-title {
                    font-size: 1.25rem;
                    font-weight: 700;
                    color: white;
                    margin-bottom: 12px;
                    text-align: center;
                }
                .onboarding-content {
                    color: #c4b5fd;
                    font-size: 0.95rem;
                    line-height: 1.6;
                    text-align: center;
                    margin-bottom: 20px;
                }
                .onboarding-progress {
                    display: flex;
                    justify-content: center;
                    gap: 6px;
                    margin-bottom: 20px;
                }
                .onboarding-dot {
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                    background: rgba(255, 255, 255, 0.3);
                    transition: all 0.3s ease;
                }
                .onboarding-dot.active {
                    background: #a855f7;
                    transform: scale(1.2);
                }
                .onboarding-dot.completed {
                    background: #22c55e;
                }
                .onboarding-buttons {
                    display: flex;
                    gap: 12px;
                    justify-content: center;
                }
                .onboarding-btn {
                    padding: 10px 24px;
                    border-radius: 10px;
                    font-weight: 600;
                    font-size: 0.9rem;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    border: none;
                }
                .onboarding-btn-primary {
                    background: linear-gradient(135deg, #8b5cf6 0%, #ec4899 100%);
                    color: white;
                }
                .onboarding-btn-primary:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 10px 20px rgba(139, 92, 246, 0.3);
                }
                .onboarding-btn-secondary {
                    background: rgba(255, 255, 255, 0.1);
                    color: white;
                    border: 1px solid rgba(255, 255, 255, 0.2);
                }
                .onboarding-btn-secondary:hover {
                    background: rgba(255, 255, 255, 0.2);
                }
                .onboarding-skip {
                    position: absolute;
                    top: 12px;
                    right: 12px;
                    background: none;
                    border: none;
                    color: rgba(255, 255, 255, 0.5);
                    cursor: pointer;
                    font-size: 0.8rem;
                    padding: 4px 8px;
                }
                .onboarding-skip:hover {
                    color: white;
                }
                .highlight-element {
                    position: relative;
                    z-index: 9999;
                    box-shadow: 0 0 0 4px rgba(139, 92, 246, 0.5), 0 0 20px rgba(139, 92, 246, 0.3);
                    border-radius: 8px;
                    animation: highlightPulse 2s ease-in-out infinite;
                }
                @keyframes highlightPulse {
                    0%, 100% { box-shadow: 0 0 0 4px rgba(139, 92, 246, 0.5), 0 0 20px rgba(139, 92, 246, 0.3); }
                    50% { box-shadow: 0 0 0 6px rgba(139, 92, 246, 0.7), 0 0 30px rgba(139, 92, 246, 0.5); }
                }
                .onboarding-arrow {
                    position: absolute;
                    width: 0;
                    height: 0;
                }
                .onboarding-arrow.top {
                    bottom: -10px;
                    left: 50%;
                    transform: translateX(-50%);
                    border-left: 10px solid transparent;
                    border-right: 10px solid transparent;
                    border-top: 10px solid #312e81;
                }
                .onboarding-arrow.bottom {
                    top: -10px;
                    left: 50%;
                    transform: translateX(-50%);
                    border-left: 10px solid transparent;
                    border-right: 10px solid transparent;
                    border-bottom: 10px solid #1e1b4b;
                }
            </style>
        `;
        document.body.appendChild(overlay);
    }

    // Create tooltip element
    function createTooltip() {
        tooltip = document.createElement('div');
        tooltip.id = 'onboarding-tooltip';
        document.body.appendChild(tooltip);
    }

    // Update tooltip content and position
    function showStep(stepIndex) {
        const step = tutorialSteps[stepIndex];
        if (!step) return;

        // Remove previous highlight
        document.querySelectorAll('.highlight-element').forEach(el => {
            el.classList.remove('highlight-element');
        });

        // Scroll to target element if needed and delay tooltip positioning
        if (step.target) {
            const targetEl = document.querySelector(step.target);
            if (targetEl) {
                targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                // Wait for scroll to complete before positioning tooltip
                setTimeout(() => {
                    targetEl.classList.add('highlight-element');
                    positionTooltip(targetEl, step.position);
                }, 400);
            }
        }

        // Build progress dots
        const dots = tutorialSteps.map((_, i) => {
            let className = 'onboarding-dot';
            if (i < stepIndex) className += ' completed';
            else if (i === stepIndex) className += ' active';
            return `<div class="${className}"></div>`;
        }).join('');

        // Build buttons
        const isFirst = stepIndex === 0;
        const isLast = stepIndex === tutorialSteps.length - 1;
        
        let buttons = '';
        if (!isFirst) {
            buttons += `<button class="onboarding-btn onboarding-btn-secondary" onclick="window.onboardingPrev()">← Anterior</button>`;
        }
        if (isLast) {
            buttons += `<button class="onboarding-btn onboarding-btn-primary" onclick="window.onboardingComplete()">Começar! 🚀</button>`;
        } else {
            buttons += `<button class="onboarding-btn onboarding-btn-primary" onclick="window.onboardingNext()">Próximo →</button>`;
        }

        // Update tooltip content
        tooltip.innerHTML = `
            <button class="onboarding-skip" onclick="window.onboardingSkip()">Saltar tutorial</button>
            <div class="onboarding-icon">${step.icon}</div>
            <div class="onboarding-title">${step.title}</div>
            <div class="onboarding-content">${step.content}</div>
            <div class="onboarding-progress">${dots}</div>
            <div class="onboarding-buttons">${buttons}</div>
            ${step.target && step.position !== 'center' ? `<div class="onboarding-arrow ${step.position}"></div>` : ''}
        `;

        // Position tooltip (scroll handling is done above with delay)
        if (!step.target) {
            tooltip.className = 'center';
            tooltip.style.top = '50%';
            tooltip.style.left = '50%';
            tooltip.style.transform = 'translate(-50%, -50%)';
        }
    }

    // Position tooltip relative to target element
    function positionTooltip(target, position) {
        const rect = target.getBoundingClientRect();
        const tooltipRect = tooltip.getBoundingClientRect();
        
        tooltip.className = '';
        tooltip.style.transform = '';

        switch (position) {
            case 'bottom':
                tooltip.style.top = (rect.bottom + 20) + 'px';
                tooltip.style.left = (rect.left + rect.width / 2 - 200) + 'px';
                break;
            case 'top':
                tooltip.style.top = (rect.top - tooltipRect.height - 20) + 'px';
                tooltip.style.left = (rect.left + rect.width / 2 - 200) + 'px';
                break;
            case 'left':
                tooltip.style.top = (rect.top + rect.height / 2 - tooltipRect.height / 2) + 'px';
                tooltip.style.left = (rect.left - tooltipRect.width - 20) + 'px';
                break;
            case 'right':
                tooltip.style.top = (rect.top + rect.height / 2 - tooltipRect.height / 2) + 'px';
                tooltip.style.left = (rect.right + 20) + 'px';
                break;
            default:
                tooltip.className = 'center';
                tooltip.style.top = '50%';
                tooltip.style.left = '50%';
                tooltip.style.transform = 'translate(-50%, -50%)';
        }

        // Ensure tooltip stays within viewport
        const newRect = tooltip.getBoundingClientRect();
        if (newRect.left < 20) tooltip.style.left = '20px';
        if (newRect.right > window.innerWidth - 20) {
            tooltip.style.left = (window.innerWidth - newRect.width - 20) + 'px';
        }
    }

    // Navigation functions
    window.onboardingNext = function() {
        if (currentStep < tutorialSteps.length - 1) {
            currentStep++;
            showStep(currentStep);
        }
    };

    window.onboardingPrev = function() {
        if (currentStep > 0) {
            currentStep--;
            showStep(currentStep);
        }
    };

    window.onboardingSkip = function() {
        closeOnboarding();
    };

    window.onboardingComplete = function() {
        closeOnboarding();
    };

    // Close onboarding
    function closeOnboarding() {
        completeOnboarding();
        
        // Remove highlight
        document.querySelectorAll('.highlight-element').forEach(el => {
            el.classList.remove('highlight-element');
        });

        // Fade out and remove
        if (overlay) {
            overlay.style.opacity = '0';
            tooltip.style.opacity = '0';
            setTimeout(() => {
                overlay.remove();
                tooltip.remove();
            }, 300);
        }
    }

    // Start onboarding
    function startOnboarding() {
        if (!shouldShowOnboarding()) return;
        
        createOverlay();
        createTooltip();
        currentStep = 0;
        showStep(currentStep);
    }

    // Manual trigger for testing or re-showing
    window.showOnboarding = function() {
        localStorage.removeItem(ONBOARDING_KEY);
        if (overlay) overlay.remove();
        if (tooltip) tooltip.remove();
        startOnboarding();
    };

    // Initialize on page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            setTimeout(startOnboarding, 500);
        });
    } else {
        setTimeout(startOnboarding, 500);
    }
})();
