/**
 * BookCreatorAI - JavaScript Functions
 */

// API Base URL
const API_BASE = '';

// Pool of suggested themes
const allThemes = [
    // Fantasia
    "Uma aventura épica num reino mágico onde dragões e humanos coexistem",
    "Um jovem aprendiz de feiticeiro que descobre ser o herdeiro de um poder antigo",
    "Uma floresta encantada onde as árvores guardam segredos milenares",
    "A última elfa a proteger um artefacto que pode destruir o mundo",
    "Um portal mágico que liga dois mundos completamente opostos",
    
    // Romance
    "Romance proibido entre duas famílias rivais numa pequena vila",
    "Reencontro de amores de infância depois de 20 anos separados",
    "Um casamento arranjado que se transforma em amor verdadeiro",
    "Cartas de amor perdidas que unem duas almas através do tempo",
    "Um verão inesquecível na costa portuguesa que muda duas vidas",
    
    // Ficção Científica
    "Viagem espacial para colonizar Marte e os desafios da nova sociedade",
    "Inteligência artificial que desenvolve emoções e questiona a sua existência",
    "Um mundo pós-apocalíptico onde a tecnologia é proibida",
    "Viajantes do tempo que tentam corrigir erros do passado",
    "Primeiro contacto com uma civilização alienígena pacífica",
    
    // Terror/Suspense
    "Casa assombrada com segredos sombrios de uma família antiga",
    "Uma pequena aldeia onde pessoas desaparecem misteriosamente",
    "Pesadelos que começam a tornar-se realidade",
    "Um espelho antigo que mostra visões perturbadoras do futuro",
    "A criatura que habita nas profundezas de um lago esquecido",
    
    // Policial/Mistério
    "Detetive a resolver um crime impossível numa mansão isolada",
    "Série de roubos de arte que escondem uma mensagem secreta",
    "Desaparecimento misterioso de um cientista famoso",
    "Um jornalista que descobre uma conspiração governamental",
    "Crime perfeito que começa a desmoronar por pequenos detalhes",
    
    // Aventura
    "Sobrevivência numa ilha deserta após um naufrágio",
    "Expedição para encontrar uma cidade perdida na Amazónia",
    "Travessia do deserto do Saara em busca de um tesouro lendário",
    "Escalada do Evereste com reviravoltas inesperadas",
    "Caça ao tesouro através de cidades europeias históricas",
    
    // Infantil
    "Animais da floresta que se unem para salvar o seu habitat",
    "Uma criança que descobre que o seu peluche ganha vida à noite",
    "Escola de magia para crianças com poderes especiais",
    "Viagem fantástica ao centro da Terra com um avô inventor",
    "O dragão bebé que tinha medo de voar",
    
    // Drama
    "Três gerações de uma família a enfrentar segredos do passado",
    "Músico que perde a audição e reinventa a sua arte",
    "Amizade improvável entre um idoso e uma criança de rua",
    "Imigrante que constrói uma nova vida num país desconhecido",
    "Professor reformado que volta a ensinar numa escola problemática",
    
    // Histórico
    "Aventuras de um navegador português nos Descobrimentos",
    "Romance durante a Segunda Guerra Mundial em Lisboa",
    "Vida na corte de D. João V no século XVIII",
    "Revolução do 25 de Abril vista pelos olhos de uma família",
    "Gladiador romano que luta pela liberdade",
    
    // Comédia
    "Família disfuncional que herda um castelo assombrado",
    "Troca de corpos entre um CEO e o seu cão",
    "Casamento que dá tudo errado de formas hilariantes",
    "Robô doméstico com uma personalidade excêntrica",
    "Férias desastrosas que se tornam na melhor aventura",
    
    // Outros
    "Herói comum que descobre poderes extraordinários aos 50 anos",
    "Sociedade secreta que protege manuscritos antigos",
    "Mundo paralelo onde os sonhos são moeda de troca",
    "Último bibliotecário numa era onde livros são proibidos",
    "Artista que pinta quadros que preveem o futuro",
    
    // Técnico/Não-Ficção
    "Guia completo de programação Python para iniciantes",
    "Manual prático de inteligência artificial e machine learning",
    "Como criar aplicações web modernas com JavaScript",
    "Introdução à ciência de dados e análise estatística",
    "Guia de produtividade e gestão de tempo para profissionais",
    "Manual de fotografia digital: da técnica à arte",
    "Finanças pessoais: como gerir e investir o seu dinheiro",
    "Guia prático de marketing digital e redes sociais",
    "Introdução à filosofia: pensadores e ideias fundamentais",
    "Manual de escrita criativa e técnicas narrativas",
    "Guia de jardinagem e cultivo de plantas em casa",
    "Introdução à astronomia: explorando o universo",
    "Manual de culinária saudável e nutrição",
    "Guia de desenvolvimento pessoal e autoconhecimento",
    "História da arte: dos primórdios à arte contemporânea"
];

// Theme colors for visual variety
const themeColors = [
    'purple', 'pink', 'indigo', 'red', 'yellow', 
    'green', 'cyan', 'orange', 'teal', 'violet'
];

/**
 * Get random themes from the pool
 */
function getRandomThemes(count = 6) {
    const shuffled = [...allThemes].sort(() => Math.random() - 0.5);
    return shuffled.slice(0, count);
}

/**
 * Render theme chips
 */
function renderThemes(themes) {
    const container = document.getElementById('suggestedThemes');
    if (!container) return;
    
    container.innerHTML = '';
    
    themes.forEach((theme, index) => {
        const color = themeColors[index % themeColors.length];
        const button = document.createElement('button');
        button.type = 'button';
        button.onclick = function() { selectTheme(this); };
        button.className = `theme-chip px-3 py-1.5 bg-${color}-600/20 hover:bg-${color}-600/40 text-${color}-300 text-sm rounded-full border border-${color}-500/30 transition-all`;
        button.textContent = theme;
        container.appendChild(button);
    });
}

/**
 * Refresh themes with new random selection
 */
function refreshThemes() {
    const themes = getRandomThemes(6);
    renderThemes(themes);
    
    // Add animation effect
    const container = document.getElementById('suggestedThemes');
    container.classList.add('animate-pulse');
    setTimeout(() => container.classList.remove('animate-pulse'), 300);
}

/**
 * Select a suggested theme
 */
function selectTheme(button) {
    const themeInput = document.getElementById('theme');
    const themeText = button.textContent.trim();
    
    // Set the theme value
    themeInput.value = themeText;
    
    // Remove active class from all chips
    document.querySelectorAll('.theme-chip').forEach(chip => {
        chip.classList.remove('ring-2', 'ring-white');
    });
    
    // Add active class to selected chip
    button.classList.add('ring-2', 'ring-white');
    
    // Focus on the input
    themeInput.focus();
}

// Initialize themes on page load
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('suggestedThemes')) {
        refreshThemes();
    }
});

/**
 * Generate a new book
 */
async function generateBook(event) {
    event.preventDefault();
    
    const form = document.getElementById('bookForm');
    const loadingState = document.getElementById('loadingState');
    const successMessage = document.getElementById('successMessage');
    const errorMessage = document.getElementById('errorMessage');
    const generateBtn = document.getElementById('generateBtn');
    
    // Get form values
    const theme = document.getElementById('theme').value.trim();
    const numChapters = parseInt(document.getElementById('numChapters').value);
    const numPages = parseInt(document.getElementById('numPages').value);
    const style = document.getElementById('style').value;
    
    // Get selected languages (multiple)
    const languageCheckboxes = document.querySelectorAll('input[name="languages"]:checked');
    const languages = Array.from(languageCheckboxes).map(cb => cb.value);
    
    // Validate
    if (!theme) {
        showError('Por favor, insira um tema para o livro.');
        return;
    }
    
    if (numChapters < 1 || numChapters > 20) {
        showError('O número de capítulos deve ser entre 1 e 20.');
        return;
    }
    
    if (languages.length === 0) {
        showError('Por favor, selecione pelo menos um idioma.');
        return;
    }
    
    // Show loading state
    generateBtn.disabled = true;
    generateBtn.classList.add('opacity-50', 'cursor-not-allowed');
    loadingState.classList.remove('hidden');
    successMessage.classList.add('hidden');
    errorMessage.classList.add('hidden');
    
    try {
        const response = await fetch(`${API_BASE}/generate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                theme: theme,
                num_chapters: numChapters,
                num_pages: numPages,
                style: style,
                languages: languages
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Show success message
            loadingState.classList.add('hidden');
            successMessage.classList.remove('hidden');
            
            // Handle multiple books
            if (data.books && data.books.length > 1) {
                document.getElementById('successTitle').textContent = `${data.books.length} livros criados!`;
                document.getElementById('viewBookLink').href = `/books`;
                document.getElementById('viewBookLink').textContent = 'Ver Todos os Livros';
            } else {
                document.getElementById('successTitle').textContent = `"${data.title}"`;
                document.getElementById('viewBookLink').href = `/book/${data.book_id}`;
                document.getElementById('viewBookLink').textContent = 'Ver Livro';
            }
            
            // Clear form
            form.reset();
            document.getElementById('numChapters').value = 5;
        } else {
            showError(data.error || 'Erro desconhecido ao gerar o livro.');
        }
    } catch (error) {
        console.error('Error:', error);
        showError('Erro de conexão. Por favor, tente novamente.');
    } finally {
        // Reset button state
        generateBtn.disabled = false;
        generateBtn.classList.remove('opacity-50', 'cursor-not-allowed');
        loadingState.classList.add('hidden');
    }
}

/**
 * Show error message
 */
function showError(message) {
    const errorMessage = document.getElementById('errorMessage');
    const errorText = document.getElementById('errorText');
    const loadingState = document.getElementById('loadingState');
    
    if (loadingState) loadingState.classList.add('hidden');
    errorMessage.classList.remove('hidden');
    errorText.textContent = message;
}

/**
 * Load all books for the list page
 */
async function loadBooks() {
    const loadingBooks = document.getElementById('loadingBooks');
    const emptyState = document.getElementById('emptyState');
    const booksGrid = document.getElementById('booksGrid');
    
    try {
        const response = await fetch(`${API_BASE}/api/books`);
        const data = await response.json();
        
        loadingBooks.classList.add('hidden');
        
        if (data.success && data.books.length > 0) {
            booksGrid.classList.remove('hidden');
            renderBooks(data.books);
        } else {
            emptyState.classList.remove('hidden');
        }
    } catch (error) {
        console.error('Error loading books:', error);
        loadingBooks.classList.add('hidden');
        emptyState.classList.remove('hidden');
    }
}

/**
 * Render books in the grid
 */
function renderBooks(books) {
    const booksGrid = document.getElementById('booksGrid');
    booksGrid.innerHTML = '';
    
    books.forEach((book, index) => {
        const card = createBookCard(book);
        booksGrid.appendChild(card);
    });
}

/**
 * Create a book card element
 */
function createBookCard(book) {
    const card = document.createElement('div');
    card.className = 'book-card bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 p-6 fade-in';
    card.style.opacity = '0';
    
    // Format date
    const date = new Date(book.created_at);
    const formattedDate = date.toLocaleDateString('pt-PT', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    });
    
    // Get style display name
    const styleNames = {
        'romance': 'Romance',
        'ficcao_cientifica': 'Ficção Científica',
        'fantasia': 'Fantasia',
        'terror': 'Terror',
        'policial': 'Policial',
        'infantil': 'Infantil',
        'aventura': 'Aventura',
        'drama': 'Drama',
        'comedia': 'Comédia',
        'historico': 'Histórico',
        'suspense': 'Suspense',
        'autobiografia': 'Autobiografia'
    };
    const styleName = styleNames[book.style] || book.style;
    
    // Truncate theme if too long
    const truncatedTheme = book.theme.length > 100 
        ? book.theme.substring(0, 100) + '...' 
        : book.theme;
    
    // Build tags HTML
    const tagsHtml = (book.tags || []).map(tag => 
        `<span class="inline-flex items-center px-2 py-0.5 bg-indigo-600/30 text-indigo-300 rounded-full text-xs">#${escapeHtml(tag)}</span>`
    ).join('');
    
    // Reading time
    const readingTime = book.reading_time || Math.max(1, Math.round((book.word_count || 0) / 200));
    
    // Language flag
    const langFlag = getLanguageFlag(book.language);
    
    // Favorite icon fill
    const favFill = book.is_favorite ? 'currentColor' : 'none';
    const favClass = book.is_favorite ? 'text-yellow-400' : 'text-gray-400 hover:text-yellow-400';
    
    card.innerHTML = `
        <div class="flex justify-between items-start mb-3">
            <h3 class="text-xl font-bold text-white line-clamp-2 flex-1">${escapeHtml(book.title)}</h3>
            <button onclick="toggleFavorite(${book.id}, this)" class="${favClass} transition-colors ml-2" title="Favorito">
                <svg class="w-5 h-5" fill="${favFill}" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"></path>
                </svg>
            </button>
        </div>
        <p class="text-gray-400 text-sm line-clamp-2 mb-3">${escapeHtml(truncatedTheme)}</p>
        
        <div class="flex flex-wrap gap-2 mb-3">
            <span class="inline-flex items-center px-2 py-1 bg-purple-600/30 text-purple-300 rounded-full text-xs">
                ${escapeHtml(styleName)}
            </span>
            <span class="inline-flex items-center px-2 py-1 bg-pink-600/30 text-pink-300 rounded-full text-xs">
                ${book.chapters.length} cap.
            </span>
            <span class="inline-flex items-center px-2 py-1 bg-green-600/30 text-green-300 rounded-full text-xs">
                ~${readingTime} min
            </span>
            <span class="inline-flex items-center px-2 py-1 bg-blue-600/30 text-blue-300 rounded-full text-xs">
                ${langFlag}
            </span>
        </div>
        
        ${tagsHtml ? `<div class="flex flex-wrap gap-1 mb-3">${tagsHtml}</div>` : ''}
        
        <div class="flex items-center text-gray-400 text-sm mb-4">
            <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
            </svg>
            ${formattedDate}
            ${book.word_count ? `<span class="ml-3">${book.word_count.toLocaleString()} palavras</span>` : ''}
        </div>
        
        <!-- Main Actions -->
        <div class="flex flex-wrap gap-2 mb-2">
            <a href="/book/${book.id}" class="flex-1 inline-flex items-center justify-center px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white text-sm font-medium rounded-lg transition-colors">
                <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
                </svg>
                Ver
            </a>
            <div class="relative group">
                <button class="inline-flex items-center justify-center px-3 py-2 bg-green-600 hover:bg-green-700 text-white text-sm font-medium rounded-lg transition-colors">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path>
                    </svg>
                </button>
                <div class="absolute right-0 bottom-full mb-1 hidden group-hover:block bg-gray-900 rounded-lg shadow-lg border border-white/20 overflow-hidden z-10">
                    <a href="/download/${book.id}" class="block px-4 py-2 text-sm text-white hover:bg-white/10">.TXT</a>
                    <a href="/download/${book.id}/md" class="block px-4 py-2 text-sm text-white hover:bg-white/10">.MD</a>
                    <a href="/download/${book.id}/pdf" class="block px-4 py-2 text-sm text-white hover:bg-white/10">.PDF</a>
                    <a href="/download/${book.id}/epub" class="block px-4 py-2 text-sm text-white hover:bg-white/10">.EPUB</a>
                </div>
            </div>
            <button onclick="confirmDeleteBook(${book.id})" class="inline-flex items-center justify-center px-3 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-lg transition-colors" title="Eliminar">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                </svg>
            </button>
        </div>
        
        <!-- Secondary Actions -->
        <div class="flex flex-wrap gap-2">
            <a href="/edit/${book.id}" class="inline-flex items-center justify-center px-2 py-1 bg-yellow-600/30 hover:bg-yellow-600/50 text-yellow-300 text-xs font-medium rounded transition-colors" title="Editar">
                <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
                </svg>
                Editar
            </a>
            <button onclick="showBookStats(${book.id})" class="inline-flex items-center justify-center px-2 py-1 bg-white/10 hover:bg-white/20 text-gray-300 text-xs font-medium rounded transition-colors" title="Estatísticas">
                <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
                </svg>
                Stats
            </button>
            <button onclick="duplicateBook(${book.id})" class="inline-flex items-center justify-center px-2 py-1 bg-white/10 hover:bg-white/20 text-gray-300 text-xs font-medium rounded transition-colors" title="Duplicar">
                <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path>
                </svg>
                Duplicar
            </button>
            <button onclick="shareBook(${book.id})" class="inline-flex items-center justify-center px-2 py-1 bg-white/10 hover:bg-white/20 text-gray-300 text-xs font-medium rounded transition-colors" title="Partilhar">
                <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"></path>
                </svg>
                Partilhar
            </button>
        </div>
    `;
    
    // Trigger animation
    setTimeout(() => {
        card.style.opacity = '1';
    }, 50);
    
    return card;
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Delete book confirmation
 */
let bookToDelete = null;

function confirmDeleteBook(bookId) {
    bookToDelete = bookId;
    const modal = document.getElementById('deleteModal');
    modal.classList.remove('hidden');
}

function closeDeleteModal() {
    const modal = document.getElementById('deleteModal');
    modal.classList.add('hidden');
    bookToDelete = null;
}

async function deleteBook() {
    if (!bookToDelete) return;
    
    try {
        const response = await fetch(`${API_BASE}/delete/${bookToDelete}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            closeDeleteModal();
            loadBooks(); // Reload the list
        } else {
            alert('Erro ao eliminar o livro: ' + data.error);
        }
    } catch (error) {
        console.error('Error deleting book:', error);
        alert('Erro de conexão ao eliminar o livro.');
    }
}

// Event Listeners
document.addEventListener('DOMContentLoaded', function() {
    // Book generation form
    const bookForm = document.getElementById('bookForm');
    if (bookForm) {
        bookForm.addEventListener('submit', generateBook);
    }
    
    // Delete modal buttons
    const cancelDelete = document.getElementById('cancelDelete');
    const confirmDelete = document.getElementById('confirmDelete');
    
    if (cancelDelete) {
        cancelDelete.addEventListener('click', closeDeleteModal);
    }
    
    if (confirmDelete) {
        confirmDelete.addEventListener('click', deleteBook);
    }
    
    // Close modal on backdrop click
    const deleteModal = document.getElementById('deleteModal');
    if (deleteModal) {
        deleteModal.addEventListener('click', function(e) {
            if (e.target === deleteModal) {
                closeDeleteModal();
            }
        });
    }
    
    // Close modal on Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeDeleteModal();
        }
    });
});

// Smooth scroll for chapter links
document.querySelectorAll('a[href^="#chapter-"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// ==================== NEW FEATURES ====================

// Current search/filter state
let currentFilters = {
    query: '',
    tag: '',
    favorites: false,
    style: '',
    language: ''
};

/**
 * Search books with filters
 */
async function searchBooks() {
    const params = new URLSearchParams();
    if (currentFilters.query) params.append('q', currentFilters.query);
    if (currentFilters.tag) params.append('tag', currentFilters.tag);
    if (currentFilters.favorites) params.append('favorites', 'true');
    if (currentFilters.style) params.append('style', currentFilters.style);
    if (currentFilters.language) params.append('language', currentFilters.language);
    
    const loadingBooks = document.getElementById('loadingBooks');
    const emptyState = document.getElementById('emptyState');
    const booksGrid = document.getElementById('booksGrid');
    
    if (loadingBooks) loadingBooks.classList.remove('hidden');
    if (booksGrid) booksGrid.classList.add('hidden');
    if (emptyState) emptyState.classList.add('hidden');
    
    try {
        const response = await fetch(`${API_BASE}/api/books/search?${params}`);
        const data = await response.json();
        
        if (loadingBooks) loadingBooks.classList.add('hidden');
        
        if (data.success && data.books.length > 0) {
            if (booksGrid) booksGrid.classList.remove('hidden');
            renderBooks(data.books);
            updateResultCount(data.count);
        } else {
            if (emptyState) emptyState.classList.remove('hidden');
            updateResultCount(0);
        }
    } catch (error) {
        console.error('Error searching books:', error);
        if (loadingBooks) loadingBooks.classList.add('hidden');
        if (emptyState) emptyState.classList.remove('hidden');
    }
}

function updateResultCount(count) {
    const countEl = document.getElementById('resultCount');
    if (countEl) {
        countEl.textContent = `${count} livro${count !== 1 ? 's' : ''} encontrado${count !== 1 ? 's' : ''}`;
    }
}

/**
 * Toggle favorite status
 */
async function toggleFavorite(bookId, button) {
    try {
        const response = await fetch(`${API_BASE}/api/book/${bookId}/favorite`, {
            method: 'POST'
        });
        const data = await response.json();
        
        if (data.success) {
            // Update button appearance
            const icon = button.querySelector('svg');
            if (data.is_favorite) {
                icon.setAttribute('fill', 'currentColor');
                button.classList.add('text-yellow-400');
                button.classList.remove('text-gray-400');
            } else {
                icon.setAttribute('fill', 'none');
                button.classList.remove('text-yellow-400');
                button.classList.add('text-gray-400');
            }
            showToast(data.message);
        }
    } catch (error) {
        console.error('Error toggling favorite:', error);
        showToast('Erro ao atualizar favorito', 'error');
    }
}

/**
 * Duplicate a book
 */
async function duplicateBook(bookId) {
    try {
        const response = await fetch(`${API_BASE}/api/book/${bookId}/duplicate`, {
            method: 'POST'
        });
        const data = await response.json();
        
        if (data.success) {
            showToast(data.message);
            loadBooks(); // Reload the list
        } else {
            showToast(data.error, 'error');
        }
    } catch (error) {
        console.error('Error duplicating book:', error);
        showToast('Erro ao duplicar livro', 'error');
    }
}

/**
 * Generate share link
 */
async function shareBook(bookId) {
    try {
        const response = await fetch(`${API_BASE}/api/book/${bookId}/share`, {
            method: 'POST'
        });
        const data = await response.json();
        
        if (data.success) {
            const fullUrl = window.location.origin + data.share_url;
            
            // Try to copy to clipboard
            try {
                await navigator.clipboard.writeText(fullUrl);
                showToast('Link copiado para a área de transferência!');
            } catch {
                // Show modal with link if clipboard fails
                prompt('Link de partilha:', fullUrl);
            }
        } else {
            showToast(data.error, 'error');
        }
    } catch (error) {
        console.error('Error sharing book:', error);
        showToast('Erro ao gerar link', 'error');
    }
}

/**
 * Show book statistics modal
 */
async function showBookStats(bookId) {
    try {
        const response = await fetch(`${API_BASE}/api/book/${bookId}/stats`);
        const data = await response.json();
        
        if (data.success) {
            const stats = data.stats;
            const modal = document.getElementById('statsModal');
            
            if (modal) {
                document.getElementById('statsTitle').textContent = stats.title;
                document.getElementById('statsWordCount').textContent = stats.word_count.toLocaleString();
                document.getElementById('statsPageCount').textContent = stats.page_count;
                document.getElementById('statsChapterCount').textContent = stats.chapter_count;
                document.getElementById('statsReadingTime').textContent = stats.reading_time + ' min';
                document.getElementById('statsCharCount').textContent = stats.character_count.toLocaleString();
                document.getElementById('statsAvgWords').textContent = stats.avg_words_per_chapter.toLocaleString();
                
                modal.classList.remove('hidden');
            }
        }
    } catch (error) {
        console.error('Error loading stats:', error);
        showToast('Erro ao carregar estatísticas', 'error');
    }
}

function closeStatsModal() {
    const modal = document.getElementById('statsModal');
    if (modal) modal.classList.add('hidden');
}

/**
 * Add tag to book
 */
async function addTagToBook(bookId, tag) {
    try {
        const response = await fetch(`${API_BASE}/api/book/${bookId}/tags`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'add', tags: [tag] })
        });
        const data = await response.json();
        
        if (data.success) {
            showToast('Tag adicionada!');
            return data.tags;
        }
    } catch (error) {
        console.error('Error adding tag:', error);
    }
    return null;
}

/**
 * Remove tag from book
 */
async function removeTagFromBook(bookId, tag) {
    try {
        const response = await fetch(`${API_BASE}/api/book/${bookId}/tags`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'remove', tags: [tag] })
        });
        const data = await response.json();
        
        if (data.success) {
            showToast('Tag removida!');
            return data.tags;
        }
    } catch (error) {
        console.error('Error removing tag:', error);
    }
    return null;
}

/**
 * Load all available tags
 */
async function loadAllTags() {
    try {
        const response = await fetch(`${API_BASE}/api/books/tags`);
        const data = await response.json();
        
        if (data.success) {
            return data.tags;
        }
    } catch (error) {
        console.error('Error loading tags:', error);
    }
    return [];
}

/**
 * Show toast notification
 */
function showToast(message, type = 'success') {
    // Remove existing toasts
    const existingToast = document.querySelector('.toast-notification');
    if (existingToast) existingToast.remove();
    
    const toast = document.createElement('div');
    toast.className = `toast-notification fixed bottom-4 right-4 px-6 py-3 rounded-lg shadow-lg z-50 transition-all transform translate-y-0 ${
        type === 'error' ? 'bg-red-600 text-white' : 'bg-green-600 text-white'
    }`;
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        toast.classList.add('opacity-0', 'translate-y-2');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

/**
 * Format reading time
 */
function formatReadingTime(minutes) {
    if (minutes < 60) return `${minutes} min`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins}min`;
}

/**
 * Get language flag emoji
 */
function getLanguageFlag(lang) {
    const flags = {
        'pt-pt': '🇵🇹',
        'pt-br': '🇧🇷',
        'en': '🇬🇧',
        'fr': '🇫🇷',
        'de': '🇩🇪',
        'it': '🇮🇹'
    };
    return flags[lang] || '🌍';
}

// ==================== ADVANCED AI FEATURES ====================

// Store for characters and world data
let advancedAICharacters = [];
let advancedAIWorld = {};
let selectedPlotData = null;

/**
 * Toggle Advanced AI Panel
 */
function toggleAdvancedAI() {
    const panel = document.getElementById('advancedAIPanel');
    const arrow = document.getElementById('advancedAIArrow');
    
    if (panel.classList.contains('hidden')) {
        panel.classList.remove('hidden');
        arrow.style.transform = 'rotate(180deg)';
    } else {
        panel.classList.add('hidden');
        arrow.style.transform = 'rotate(0deg)';
    }
}

/**
 * Get AI Theme Suggestions
 */
async function getAIThemeSuggestions() {
    const style = document.getElementById('style').value;
    const container = document.getElementById('aiThemeSuggestions');
    
    container.innerHTML = '<div class="text-center py-4"><div class="w-6 h-6 border-2 border-purple-400 border-t-transparent rounded-full animate-spin mx-auto"></div><p class="text-sm text-gray-400 mt-2">A gerar sugestões...</p></div>';
    container.classList.remove('hidden');
    
    try {
        const response = await fetch(`${API_BASE}/api/ai/suggest-themes`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ style, count: 5 })
        });
        const data = await response.json();
        
        if (data.success && data.themes) {
            container.innerHTML = data.themes.map(theme => `
                <div class="bg-white/5 border border-white/10 rounded-lg p-3 cursor-pointer hover:bg-white/10 transition-colors" onclick="selectAITheme('${escapeHtml(theme.title)}')">
                    <h5 class="text-white font-medium">${escapeHtml(theme.title)}</h5>
                    <p class="text-xs text-gray-400 mt-1">${escapeHtml(theme.description)}</p>
                    <p class="text-xs text-purple-400 mt-1">✨ ${escapeHtml(theme.appeal)}</p>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<p class="text-red-400 text-sm">Erro ao gerar sugestões</p>';
        }
    } catch (error) {
        container.innerHTML = '<p class="text-red-400 text-sm">Erro de conexão</p>';
    }
}

function selectAITheme(title) {
    document.getElementById('theme').value = title;
    showToast('Tema selecionado!');
}

/**
 * Add Character Manually
 */
function addCharacter(character = null) {
    const list = document.getElementById('charactersList');
    const index = advancedAICharacters.length;
    
    const char = character || { name: '', role: 'personagem', description: '', traits: '', arc: '' };
    advancedAICharacters.push(char);
    
    const html = `
        <div class="bg-white/5 border border-white/10 rounded-lg p-3" id="character-${index}">
            <div class="flex justify-between items-start mb-2">
                <input type="text" placeholder="Nome do personagem" value="${escapeHtml(char.name)}" 
                    onchange="updateCharacter(${index}, 'name', this.value)"
                    class="bg-transparent text-white font-medium focus:outline-none border-b border-transparent focus:border-purple-500">
                <button type="button" onclick="removeCharacter(${index})" class="text-red-400 hover:text-red-300 text-xs">✕</button>
            </div>
            <div class="grid grid-cols-2 gap-2 text-xs">
                <select onchange="updateCharacter(${index}, 'role', this.value)" class="bg-white/5 border border-white/10 rounded px-2 py-1 text-white">
                    <option value="protagonista" ${char.role === 'protagonista' ? 'selected' : ''} class="bg-gray-800">Protagonista</option>
                    <option value="antagonista" ${char.role === 'antagonista' ? 'selected' : ''} class="bg-gray-800">Antagonista</option>
                    <option value="mentor" ${char.role === 'mentor' ? 'selected' : ''} class="bg-gray-800">Mentor</option>
                    <option value="aliado" ${char.role === 'aliado' ? 'selected' : ''} class="bg-gray-800">Aliado</option>
                    <option value="personagem" ${char.role === 'personagem' ? 'selected' : ''} class="bg-gray-800">Personagem</option>
                </select>
                <input type="text" placeholder="Traços" value="${escapeHtml(char.traits)}"
                    onchange="updateCharacter(${index}, 'traits', this.value)"
                    class="bg-white/5 border border-white/10 rounded px-2 py-1 text-white placeholder-gray-500">
            </div>
            <textarea placeholder="Descrição do personagem..." rows="2"
                onchange="updateCharacter(${index}, 'description', this.value)"
                class="w-full mt-2 bg-white/5 border border-white/10 rounded px-2 py-1 text-white text-xs placeholder-gray-500">${escapeHtml(char.description)}</textarea>
        </div>
    `;
    
    list.insertAdjacentHTML('beforeend', html);
    updateCharactersInput();
}

function updateCharacter(index, field, value) {
    if (advancedAICharacters[index]) {
        advancedAICharacters[index][field] = value;
        updateCharactersInput();
    }
}

function removeCharacter(index) {
    advancedAICharacters.splice(index, 1);
    renderCharactersList();
    updateCharactersInput();
}

function renderCharactersList() {
    const list = document.getElementById('charactersList');
    list.innerHTML = '';
    advancedAICharacters.forEach((char, i) => {
        addCharacterHTML(i, char);
    });
}

function addCharacterHTML(index, char) {
    const list = document.getElementById('charactersList');
    const html = `
        <div class="bg-white/5 border border-white/10 rounded-lg p-3" id="character-${index}">
            <div class="flex justify-between items-start mb-2">
                <input type="text" placeholder="Nome" value="${escapeHtml(char.name)}" 
                    onchange="updateCharacter(${index}, 'name', this.value)"
                    class="bg-transparent text-white font-medium focus:outline-none border-b border-transparent focus:border-purple-500 w-2/3">
                <span class="text-xs text-purple-400">${char.role}</span>
                <button type="button" onclick="removeCharacter(${index})" class="text-red-400 hover:text-red-300 text-xs ml-2">✕</button>
            </div>
            <p class="text-xs text-gray-400 line-clamp-2">${escapeHtml(char.description)}</p>
        </div>
    `;
    list.insertAdjacentHTML('beforeend', html);
}

function updateCharactersInput() {
    document.getElementById('charactersData').value = JSON.stringify(advancedAICharacters);
}

/**
 * Generate Characters with AI
 */
async function generateAICharacters() {
    const theme = document.getElementById('theme').value;
    const style = document.getElementById('style').value;
    
    if (!theme) {
        showToast('Insira um tema primeiro', 'error');
        return;
    }
    
    const list = document.getElementById('charactersList');
    list.innerHTML = '<div class="text-center py-4"><div class="w-6 h-6 border-2 border-purple-400 border-t-transparent rounded-full animate-spin mx-auto"></div><p class="text-sm text-gray-400 mt-2">A gerar personagens...</p></div>';
    
    try {
        const response = await fetch(`${API_BASE}/api/ai/generate-characters`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ theme, style, count: 4, existing: advancedAICharacters })
        });
        const data = await response.json();
        
        if (data.success && data.characters) {
            list.innerHTML = '';
            advancedAICharacters = data.characters;
            advancedAICharacters.forEach((char, i) => addCharacterHTML(i, char));
            updateCharactersInput();
            showToast('Personagens gerados!');
        } else {
            list.innerHTML = '<p class="text-red-400 text-sm">Erro ao gerar personagens</p>';
        }
    } catch (error) {
        list.innerHTML = '<p class="text-red-400 text-sm">Erro de conexão</p>';
    }
}

/**
 * Generate World with AI
 */
async function generateAIWorld() {
    const theme = document.getElementById('theme').value;
    const style = document.getElementById('style').value;
    
    if (!theme) {
        showToast('Insira um tema primeiro', 'error');
        return;
    }
    
    // Show loading in world fields
    document.getElementById('worldTimePeriod').value = 'A gerar...';
    document.getElementById('worldLocation').value = 'A gerar...';
    
    try {
        const response = await fetch(`${API_BASE}/api/ai/generate-world`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ theme, style })
        });
        const data = await response.json();
        
        if (data.success && data.world) {
            advancedAIWorld = data.world;
            document.getElementById('worldTimePeriod').value = data.world.time_period || '';
            document.getElementById('worldLocation').value = data.world.location || '';
            document.getElementById('worldAtmosphere').value = data.world.atmosphere || '';
            document.getElementById('worldRules').value = data.world.rules || '';
            document.getElementById('worldCustom').value = data.world.custom || '';
            updateWorldInput();
            showToast('Cenário gerado!');
        } else {
            showToast('Erro ao gerar cenário', 'error');
        }
    } catch (error) {
        showToast('Erro de conexão', 'error');
    }
}

function updateWorldInput() {
    advancedAIWorld = {
        time_period: document.getElementById('worldTimePeriod').value,
        location: document.getElementById('worldLocation').value,
        atmosphere: document.getElementById('worldAtmosphere').value,
        rules: document.getElementById('worldRules').value,
        custom: document.getElementById('worldCustom').value
    };
    document.getElementById('worldData').value = JSON.stringify(advancedAIWorld);
}

// Update world on input change
document.addEventListener('DOMContentLoaded', function() {
    const worldInputs = ['worldTimePeriod', 'worldLocation', 'worldAtmosphere', 'worldRules', 'worldCustom'];
    worldInputs.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('input', updateWorldInput);
    });
});

/**
 * Generate Plot Variations
 */
async function generatePlotVariations() {
    const theme = document.getElementById('theme').value;
    const style = document.getElementById('style').value;
    
    if (!theme) {
        showToast('Insira um tema primeiro', 'error');
        return;
    }
    
    const container = document.getElementById('plotVariations');
    container.innerHTML = '<div class="text-center py-4"><div class="w-6 h-6 border-2 border-purple-400 border-t-transparent rounded-full animate-spin mx-auto"></div><p class="text-sm text-gray-400 mt-2">A gerar variações de enredo...</p></div>';
    
    try {
        const response = await fetch(`${API_BASE}/api/ai/generate-plots`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                theme, 
                style, 
                characters: advancedAICharacters, 
                world_setting: advancedAIWorld,
                count: 3 
            })
        });
        const data = await response.json();
        
        if (data.success && data.plots) {
            container.innerHTML = data.plots.map((plot, i) => `
                <div class="bg-white/5 border border-white/10 rounded-lg p-3 cursor-pointer hover:bg-white/10 transition-colors ${selectedPlotData === i ? 'ring-2 ring-purple-500' : ''}" onclick="selectPlot(${i}, '${escapeHtml(JSON.stringify(plot).replace(/'/g, "\\'"))}')">
                    <div class="flex justify-between items-start">
                        <h5 class="text-white font-medium">${escapeHtml(plot.title)}</h5>
                        <span class="text-xs bg-purple-600/30 text-purple-300 px-2 py-0.5 rounded">${escapeHtml(plot.tone)}</span>
                    </div>
                    <p class="text-xs text-gray-400 mt-2">${escapeHtml(plot.synopsis)}</p>
                    <div class="mt-2 flex flex-wrap gap-1">
                        ${(plot.conflicts || []).map(c => `<span class="text-xs bg-red-600/20 text-red-300 px-2 py-0.5 rounded">${escapeHtml(c)}</span>`).join('')}
                    </div>
                    <div class="mt-2 text-xs text-gray-500">
                        ${(plot.chapters || []).slice(0, 3).map(ch => `<span class="block">• ${escapeHtml(ch)}</span>`).join('')}
                        ${(plot.chapters || []).length > 3 ? `<span class="text-purple-400">... +${plot.chapters.length - 3} mais</span>` : ''}
                    </div>
                </div>
            `).join('');
            showToast('Variações geradas! Clique para selecionar.');
        } else {
            container.innerHTML = '<p class="text-red-400 text-sm">Erro ao gerar variações</p>';
        }
    } catch (error) {
        container.innerHTML = '<p class="text-red-400 text-sm">Erro de conexão</p>';
    }
}

function selectPlot(index, plotJson) {
    selectedPlotData = index;
    document.getElementById('selectedPlot').value = plotJson;
    
    // Update visual selection
    document.querySelectorAll('#plotVariations > div').forEach((el, i) => {
        el.classList.toggle('ring-2', i === index);
        el.classList.toggle('ring-purple-500', i === index);
    });
    
    showToast('Enredo selecionado!');
}

/**
 * Analyze Book Text
 */
async function analyzeBookText(bookId) {
    showToast('A analisar texto...');
    
    try {
        const response = await fetch(`${API_BASE}/api/ai/analyze-text`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ book_id: bookId })
        });
        const data = await response.json();
        
        if (data.success && data.analysis) {
            displayAnalysis(data.analysis);
        } else {
            showToast(data.error || 'Erro na análise', 'error');
        }
    } catch (error) {
        showToast('Erro de conexão', 'error');
    }
}

function displayAnalysis(analysis) {
    // Create modal with analysis results
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50';
    modal.onclick = (e) => { if (e.target === modal) modal.remove(); };
    
    const scores = analysis.scores || {};
    const scoreLabels = {
        writing_quality: 'Qualidade da Escrita',
        coherence: 'Coerência',
        engagement: 'Envolvimento',
        originality: 'Originalidade',
        dialogues: 'Diálogos',
        descriptions: 'Descrições',
        pacing: 'Ritmo',
        tone_consistency: 'Consistência de Tom'
    };
    
    modal.innerHTML = `
        <div class="bg-gray-900 border border-white/20 rounded-2xl p-6 max-w-2xl mx-4 w-full max-h-[90vh] overflow-y-auto">
            <div class="flex justify-between items-center mb-6">
                <h3 class="text-xl font-bold text-white">📊 Análise de Texto</h3>
                <button onclick="this.closest('.fixed').remove()" class="text-gray-400 hover:text-white">✕</button>
            </div>
            
            <div class="text-center mb-6">
                <div class="inline-flex items-center justify-center w-20 h-20 rounded-full bg-purple-600/30 mb-2">
                    <span class="text-3xl font-bold text-white">${analysis.overall_score || 0}</span>
                </div>
                <p class="text-gray-400">Pontuação Geral</p>
            </div>
            
            <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
                ${Object.entries(scores).map(([key, val]) => `
                    <div class="bg-white/5 rounded-lg p-3 text-center">
                        <p class="text-lg font-bold text-white">${val}/10</p>
                        <p class="text-xs text-gray-400">${scoreLabels[key] || key}</p>
                    </div>
                `).join('')}
            </div>
            
            <div class="grid md:grid-cols-2 gap-4 mb-6">
                <div class="bg-green-600/10 border border-green-600/30 rounded-lg p-4">
                    <h4 class="text-green-400 font-medium mb-2">✓ Pontos Fortes</h4>
                    <ul class="text-sm text-gray-300 space-y-1">
                        ${(analysis.strengths || []).map(s => `<li>• ${s}</li>`).join('')}
                    </ul>
                </div>
                <div class="bg-orange-600/10 border border-orange-600/30 rounded-lg p-4">
                    <h4 class="text-orange-400 font-medium mb-2">↗ Áreas a Melhorar</h4>
                    <ul class="text-sm text-gray-300 space-y-1">
                        ${(analysis.improvements || []).map(s => `<li>• ${s}</li>`).join('')}
                    </ul>
                </div>
            </div>
            
            <div class="bg-white/5 rounded-lg p-4">
                <p class="text-sm text-gray-300"><strong class="text-white">Tom detectado:</strong> ${analysis.detected_tone || 'N/A'}</p>
                <p class="text-sm text-gray-300 mt-1"><strong class="text-white">Género:</strong> ${analysis.detected_genre || 'N/A'}</p>
                <p class="text-sm text-gray-400 mt-2">${analysis.summary || ''}</p>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
}

// ==================== TEXT-TO-SPEECH (AUDIOBOOK) ====================

let ttsState = {
    speaking: false,
    paused: false,
    utterance: null,
    currentChunk: 0,
    chunks: [],
    voice: null,
    rate: 1.0,
    bookId: null
};

/**
 * Initialize TTS with available voices
 */
function initTTS() {
    if ('speechSynthesis' in window) {
        // Load voices
        speechSynthesis.onvoiceschanged = () => {
            const voices = speechSynthesis.getVoices();
            ttsState.voice = voices.find(v => v.lang.startsWith('pt')) || voices[0];
        };
        speechSynthesis.getVoices();
    }
}

// Initialize on load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTTS);
} else {
    initTTS();
}

/**
 * Open TTS Player modal
 */
function openTTSPlayer(bookId) {
    ttsState.bookId = bookId;
    
    // Create modal
    const modal = document.createElement('div');
    modal.id = 'ttsModal';
    modal.className = 'fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50';
    modal.onclick = (e) => { if (e.target === modal) closeTTSPlayer(); };
    
    // Get available voices
    const voices = speechSynthesis.getVoices();
    const ptVoices = voices.filter(v => v.lang.startsWith('pt') || v.lang.startsWith('en') || v.lang.startsWith('fr') || v.lang.startsWith('de') || v.lang.startsWith('it'));
    
    modal.innerHTML = `
        <div class="bg-gray-900 border border-white/20 rounded-2xl p-6 max-w-lg mx-4 w-full">
            <div class="flex justify-between items-center mb-6">
                <h3 class="text-xl font-bold text-white flex items-center gap-2">
                    <span>🔊</span> Audiobook
                </h3>
                <button onclick="closeTTSPlayer()" class="text-gray-400 hover:text-white">✕</button>
            </div>
            
            <div class="space-y-4">
                <!-- Voice Selection -->
                <div>
                    <label class="text-sm text-gray-400">Voz</label>
                    <select id="ttsVoice" onchange="setTTSVoice(this.value)" class="w-full mt-1 px-3 py-2 bg-white/5 border border-white/20 rounded-lg text-white">
                        ${ptVoices.map((v, i) => `<option value="${i}" class="bg-gray-800">${v.name} (${v.lang})</option>`).join('')}
                    </select>
                </div>
                
                <!-- Speed Control -->
                <div>
                    <label class="text-sm text-gray-400">Velocidade: <span id="speedValue">1.0x</span></label>
                    <input type="range" id="ttsSpeed" min="0.5" max="2" step="0.1" value="1" 
                           onchange="setTTSSpeed(this.value)"
                           class="w-full mt-1">
                </div>
                
                <!-- Progress -->
                <div class="bg-white/5 rounded-lg p-4">
                    <div class="flex justify-between text-sm text-gray-400 mb-2">
                        <span id="ttsProgress">Pronto para reproduzir</span>
                        <span id="ttsChunkInfo">0/0</span>
                    </div>
                    <div class="w-full bg-gray-700 rounded-full h-2">
                        <div id="ttsProgressBar" class="bg-purple-600 h-2 rounded-full transition-all" style="width: 0%"></div>
                    </div>
                </div>
                
                <!-- Controls -->
                <div class="flex justify-center gap-4">
                    <button onclick="ttsSkip(-1)" class="p-3 bg-white/10 hover:bg-white/20 text-white rounded-full transition-colors" title="Anterior">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12.066 11.2a1 1 0 000 1.6l5.334 4A1 1 0 0019 16V8a1 1 0 00-1.6-.8l-5.333 4zM4.066 11.2a1 1 0 000 1.6l5.334 4A1 1 0 0011 16V8a1 1 0 00-1.6-.8l-5.334 4z"></path>
                        </svg>
                    </button>
                    <button onclick="toggleTTS()" id="ttsPlayBtn" class="p-4 bg-purple-600 hover:bg-purple-700 text-white rounded-full transition-colors" title="Play/Pause">
                        <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"></path>
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                        </svg>
                    </button>
                    <button onclick="stopTTS()" class="p-3 bg-white/10 hover:bg-white/20 text-white rounded-full transition-colors" title="Parar">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z"></path>
                        </svg>
                    </button>
                    <button onclick="ttsSkip(1)" class="p-3 bg-white/10 hover:bg-white/20 text-white rounded-full transition-colors" title="Próximo">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.933 12.8a1 1 0 000-1.6L6.6 7.2A1 1 0 005 8v8a1 1 0 001.6.8l5.333-4zM19.933 12.8a1 1 0 000-1.6l-5.333-4A1 1 0 0013 8v8a1 1 0 001.6.8l5.333-4z"></path>
                        </svg>
                    </button>
                </div>
                
                <p class="text-xs text-gray-500 text-center mt-4">
                    💡 Usa o Text-to-Speech do navegador. Melhor experiência com Chrome ou Edge.
                </p>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Load book text
    loadBookForTTS(bookId);
}

/**
 * Load book text for TTS
 */
async function loadBookForTTS(bookId) {
    try {
        const response = await fetch(`${API_BASE}/api/book/${bookId}`);
        const data = await response.json();
        
        if (data.success) {
            // Split text into chunks (sentences or paragraphs)
            const text = data.book.full_text;
            ttsState.chunks = splitTextForTTS(text);
            ttsState.currentChunk = 0;
            
            document.getElementById('ttsChunkInfo').textContent = `0/${ttsState.chunks.length}`;
            document.getElementById('ttsProgress').textContent = 'Pronto para reproduzir';
        }
    } catch (error) {
        console.error('Error loading book for TTS:', error);
    }
}

/**
 * Split text into manageable chunks for TTS
 */
function splitTextForTTS(text) {
    // Split by paragraphs first, then by sentences if too long
    const paragraphs = text.split(/\n\n+/);
    const chunks = [];
    
    paragraphs.forEach(para => {
        if (para.length < 500) {
            if (para.trim()) chunks.push(para.trim());
        } else {
            // Split by sentences
            const sentences = para.match(/[^.!?]+[.!?]+/g) || [para];
            sentences.forEach(s => {
                if (s.trim()) chunks.push(s.trim());
            });
        }
    });
    
    return chunks;
}

/**
 * Toggle TTS play/pause
 */
function toggleTTS() {
    if (!('speechSynthesis' in window)) {
        showToast('TTS não suportado neste navegador', 'error');
        return;
    }
    
    if (ttsState.speaking && !ttsState.paused) {
        // Pause
        speechSynthesis.pause();
        ttsState.paused = true;
        updateTTSButton(false);
    } else if (ttsState.paused) {
        // Resume
        speechSynthesis.resume();
        ttsState.paused = false;
        updateTTSButton(true);
    } else {
        // Start
        speakChunk(ttsState.currentChunk);
    }
}

/**
 * Speak a specific chunk
 */
function speakChunk(index) {
    if (index >= ttsState.chunks.length) {
        // End of book
        stopTTS();
        showToast('Leitura concluída!');
        return;
    }
    
    ttsState.currentChunk = index;
    const text = ttsState.chunks[index];
    
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.voice = ttsState.voice;
    utterance.rate = ttsState.rate;
    utterance.lang = ttsState.voice?.lang || 'pt-PT';
    
    utterance.onstart = () => {
        ttsState.speaking = true;
        ttsState.paused = false;
        updateTTSButton(true);
        updateTTSProgress();
    };
    
    utterance.onend = () => {
        // Move to next chunk
        speakChunk(index + 1);
    };
    
    utterance.onerror = (e) => {
        console.error('TTS Error:', e);
        ttsState.speaking = false;
        updateTTSButton(false);
    };
    
    ttsState.utterance = utterance;
    speechSynthesis.speak(utterance);
}

/**
 * Stop TTS
 */
function stopTTS() {
    speechSynthesis.cancel();
    ttsState.speaking = false;
    ttsState.paused = false;
    ttsState.currentChunk = 0;
    updateTTSButton(false);
    updateTTSProgress();
}

/**
 * Skip forward or backward
 */
function ttsSkip(direction) {
    const newIndex = ttsState.currentChunk + (direction * 5); // Skip 5 chunks
    const clampedIndex = Math.max(0, Math.min(newIndex, ttsState.chunks.length - 1));
    
    if (ttsState.speaking) {
        speechSynthesis.cancel();
        speakChunk(clampedIndex);
    } else {
        ttsState.currentChunk = clampedIndex;
        updateTTSProgress();
    }
}

/**
 * Set TTS voice
 */
function setTTSVoice(index) {
    const voices = speechSynthesis.getVoices();
    const ptVoices = voices.filter(v => v.lang.startsWith('pt') || v.lang.startsWith('en') || v.lang.startsWith('fr') || v.lang.startsWith('de') || v.lang.startsWith('it'));
    ttsState.voice = ptVoices[index];
}

/**
 * Set TTS speed
 */
function setTTSSpeed(value) {
    ttsState.rate = parseFloat(value);
    document.getElementById('speedValue').textContent = value + 'x';
    
    // Restart current chunk with new speed
    if (ttsState.speaking) {
        speechSynthesis.cancel();
        speakChunk(ttsState.currentChunk);
    }
}

/**
 * Update play/pause button
 */
function updateTTSButton(isPlaying) {
    const btn = document.getElementById('ttsPlayBtn');
    if (!btn) return;
    
    if (isPlaying) {
        btn.innerHTML = `
            <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
        `;
    } else {
        btn.innerHTML = `
            <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"></path>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
        `;
    }
}

/**
 * Update TTS progress
 */
function updateTTSProgress() {
    const progressBar = document.getElementById('ttsProgressBar');
    const chunkInfo = document.getElementById('ttsChunkInfo');
    const progressText = document.getElementById('ttsProgress');
    
    if (!progressBar) return;
    
    const percent = (ttsState.currentChunk / ttsState.chunks.length) * 100;
    progressBar.style.width = percent + '%';
    chunkInfo.textContent = `${ttsState.currentChunk + 1}/${ttsState.chunks.length}`;
    
    if (ttsState.speaking) {
        progressText.textContent = 'A reproduzir...';
    } else if (ttsState.paused) {
        progressText.textContent = 'Pausado';
    } else {
        progressText.textContent = 'Pronto para reproduzir';
    }
}

/**
 * Close TTS Player
 */
function closeTTSPlayer() {
    stopTTS();
    const modal = document.getElementById('ttsModal');
    if (modal) modal.remove();
}

// ==================== SERIES/COLLECTIONS ====================

/**
 * Open Series Manager Modal
 */
async function openSeriesManager(bookId = null) {
    const modal = document.createElement('div');
    modal.id = 'seriesModal';
    modal.className = 'fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50';
    modal.onclick = (e) => { if (e.target === modal) closeSeriesManager(); };
    
    modal.innerHTML = `
        <div class="bg-gray-900 border border-white/20 rounded-2xl p-6 max-w-2xl mx-4 w-full max-h-[80vh] overflow-y-auto">
            <div class="flex justify-between items-center mb-6">
                <h3 class="text-xl font-bold text-white">📚 Séries/Coleções</h3>
                <button onclick="closeSeriesManager()" class="text-gray-400 hover:text-white">✕</button>
            </div>
            
            <!-- Create New Series -->
            <div class="mb-6 p-4 bg-white/5 rounded-lg">
                <h4 class="text-sm font-medium text-gray-300 mb-3">Criar Nova Série</h4>
                <div class="flex gap-2">
                    <input type="text" id="newSeriesName" placeholder="Nome da série..." 
                           class="flex-1 px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-500">
                    <button onclick="createSeries()" class="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors">
                        Criar
                    </button>
                </div>
            </div>
            
            <!-- Series List -->
            <div id="seriesList" class="space-y-3">
                <p class="text-gray-400 text-center py-4">A carregar...</p>
            </div>
            
            ${bookId ? `<input type="hidden" id="selectedBookId" value="${bookId}">` : ''}
        </div>
    `;
    
    document.body.appendChild(modal);
    loadSeriesList(bookId);
}

/**
 * Load all series
 */
async function loadSeriesList(bookId = null) {
    try {
        const response = await fetch(`${API_BASE}/api/series`);
        const data = await response.json();
        
        const container = document.getElementById('seriesList');
        
        if (!data.success || !data.series.length) {
            container.innerHTML = '<p class="text-gray-400 text-center py-4">Nenhuma série criada</p>';
            return;
        }
        
        container.innerHTML = data.series.map(series => `
            <div class="flex items-center justify-between p-3 bg-white/5 rounded-lg hover:bg-white/10 transition-colors">
                <div>
                    <p class="text-white font-medium">${series.name}</p>
                    <p class="text-xs text-gray-400">${series.book_count} livros</p>
                </div>
                <div class="flex gap-2">
                    ${bookId ? `
                        <button onclick="addBookToSeries(${bookId}, ${series.id})" 
                                class="px-3 py-1 bg-green-600/30 hover:bg-green-600/50 text-green-300 text-xs rounded transition-colors">
                            + Adicionar
                        </button>
                    ` : ''}
                    <button onclick="viewSeries(${series.id})" class="px-3 py-1 bg-blue-600/30 hover:bg-blue-600/50 text-blue-300 text-xs rounded transition-colors">
                        Ver
                    </button>
                    <button onclick="deleteSeries(${series.id})" class="px-3 py-1 bg-red-600/30 hover:bg-red-600/50 text-red-300 text-xs rounded transition-colors">
                        ✕
                    </button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading series:', error);
    }
}

/**
 * Create new series
 */
async function createSeries() {
    const nameInput = document.getElementById('newSeriesName');
    const name = nameInput.value.trim();
    
    if (!name) {
        showToast('Digite um nome para a série', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/series`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        
        const data = await response.json();
        if (data.success) {
            showToast('Série criada!');
            nameInput.value = '';
            const bookId = document.getElementById('selectedBookId')?.value;
            loadSeriesList(bookId);
        } else {
            showToast(data.error || 'Erro ao criar série', 'error');
        }
    } catch (error) {
        console.error('Error creating series:', error);
        showToast('Erro ao criar série', 'error');
    }
}

/**
 * Add book to series
 */
async function addBookToSeries(bookId, seriesId) {
    try {
        const response = await fetch(`${API_BASE}/api/book/${bookId}/series`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ series_id: seriesId })
        });
        
        const data = await response.json();
        if (data.success) {
            showToast('Livro adicionado à série!');
            closeSeriesManager();
        } else {
            showToast(data.error || 'Erro', 'error');
        }
    } catch (error) {
        console.error('Error adding book to series:', error);
    }
}

/**
 * View series details
 */
async function viewSeries(seriesId) {
    try {
        const response = await fetch(`${API_BASE}/api/series/${seriesId}`);
        const data = await response.json();
        
        if (data.success) {
            const series = data.series;
            const books = data.books;
            
            const modal = document.getElementById('seriesModal');
            if (modal) {
                modal.querySelector('.bg-gray-900').innerHTML = `
                    <div class="flex justify-between items-center mb-6">
                        <div>
                            <button onclick="loadSeriesList()" class="text-gray-400 hover:text-white text-sm mb-2">← Voltar</button>
                            <h3 class="text-xl font-bold text-white">${series.name}</h3>
                        </div>
                        <button onclick="closeSeriesManager()" class="text-gray-400 hover:text-white">✕</button>
                    </div>
                    
                    <div class="space-y-3">
                        ${books.length ? books.map((book, i) => `
                            <div class="flex items-center justify-between p-3 bg-white/5 rounded-lg">
                                <div class="flex items-center gap-3">
                                    <span class="text-gray-500">#${i + 1}</span>
                                    <div>
                                        <a href="/book/${book.id}" class="text-white hover:text-purple-400">${book.title}</a>
                                        <p class="text-xs text-gray-400">${book.word_count || 0} palavras</p>
                                    </div>
                                </div>
                                <button onclick="removeBookFromSeries(${book.id})" class="text-red-400 hover:text-red-300 text-xs">
                                    Remover
                                </button>
                            </div>
                        `).join('') : '<p class="text-gray-400 text-center py-4">Nenhum livro na série</p>'}
                    </div>
                `;
            }
        }
    } catch (error) {
        console.error('Error viewing series:', error);
    }
}

/**
 * Remove book from series
 */
async function removeBookFromSeries(bookId) {
    try {
        const response = await fetch(`${API_BASE}/api/book/${bookId}/series`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ series_id: null })
        });
        
        const data = await response.json();
        if (data.success) {
            showToast('Livro removido da série!');
            loadSeriesList();
        }
    } catch (error) {
        console.error('Error removing book from series:', error);
    }
}

/**
 * Delete series
 */
async function deleteSeries(seriesId) {
    if (!confirm('Eliminar esta série? Os livros não serão apagados.')) return;
    
    try {
        const response = await fetch(`${API_BASE}/api/series/${seriesId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        if (data.success) {
            showToast('Série eliminada!');
            loadSeriesList();
        }
    } catch (error) {
        console.error('Error deleting series:', error);
    }
}

function closeSeriesManager() {
    const modal = document.getElementById('seriesModal');
    if (modal) modal.remove();
}

// ==================== SYNOPSIS/SUMMARIES ====================

/**
 * Generate and show book synopsis
 */
async function generateSynopsis(bookId) {
    showToast('A gerar sinopse...');
    
    try {
        const response = await fetch(`${API_BASE}/api/book/${bookId}/synopsis`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showSynopsisModal(data.synopsis);
        } else {
            showToast(data.error || 'Erro ao gerar sinopse', 'error');
        }
    } catch (error) {
        console.error('Error generating synopsis:', error);
        showToast('Erro ao gerar sinopse', 'error');
    }
}

/**
 * Show synopsis modal
 */
function showSynopsisModal(synopsis) {
    const modal = document.createElement('div');
    modal.id = 'synopsisModal';
    modal.className = 'fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50';
    modal.onclick = (e) => { if (e.target === modal) modal.remove(); };
    
    modal.innerHTML = `
        <div class="bg-gray-900 border border-white/20 rounded-2xl p-6 max-w-lg mx-4 w-full">
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-xl font-bold text-white">📝 Sinopse</h3>
                <button onclick="this.closest('#synopsisModal').remove()" class="text-gray-400 hover:text-white">✕</button>
            </div>
            <div class="prose prose-invert">
                <p class="text-gray-300 whitespace-pre-wrap">${synopsis}</p>
            </div>
            <button onclick="navigator.clipboard.writeText(\`${synopsis.replace(/`/g, '\\`')}\`); showToast('Copiado!')" 
                    class="mt-4 w-full px-4 py-2 bg-purple-600/30 hover:bg-purple-600/50 text-purple-300 rounded-lg transition-colors">
                📋 Copiar Sinopse
            </button>
        </div>
    `;
    
    document.body.appendChild(modal);
}

/**
 * Generate chapter summaries
 */
async function generateChapterSummaries(bookId) {
    showToast('A gerar resumos dos capítulos...');
    
    try {
        const response = await fetch(`${API_BASE}/api/book/${bookId}/chapter-summaries`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showChapterSummariesModal(data.summaries);
        } else {
            showToast(data.error || 'Erro ao gerar resumos', 'error');
        }
    } catch (error) {
        console.error('Error generating summaries:', error);
        showToast('Erro ao gerar resumos', 'error');
    }
}

/**
 * Show chapter summaries modal
 */
function showChapterSummariesModal(summaries) {
    const modal = document.createElement('div');
    modal.id = 'summariesModal';
    modal.className = 'fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50';
    modal.onclick = (e) => { if (e.target === modal) modal.remove(); };
    
    modal.innerHTML = `
        <div class="bg-gray-900 border border-white/20 rounded-2xl p-6 max-w-2xl mx-4 w-full max-h-[80vh] overflow-y-auto">
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-xl font-bold text-white">📋 Resumos dos Capítulos</h3>
                <button onclick="this.closest('#summariesModal').remove()" class="text-gray-400 hover:text-white">✕</button>
            </div>
            <div class="space-y-4">
                ${summaries.map((s, i) => `
                    <div class="p-3 bg-white/5 rounded-lg">
                        <h4 class="text-purple-400 font-medium mb-1">${s.title}</h4>
                        <p class="text-gray-300 text-sm">${s.summary}</p>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
}

// ==================== QUICK CHAT WITH BOOK ====================

let quickChatHistory = [];
let quickChatBookId = null;

/**
 * Open quick chat modal
 */
function openQuickChat(bookId) {
    quickChatBookId = bookId;
    quickChatHistory = [];
    
    const modal = document.createElement('div');
    modal.id = 'quickChatModal';
    modal.className = 'fixed inset-0 bg-black/70 backdrop-blur-sm flex items-end sm:items-center justify-center z-50';
    modal.onclick = (e) => { if (e.target === modal) closeQuickChat(); };
    
    modal.innerHTML = `
        <div class="bg-gray-900 border border-white/20 rounded-t-2xl sm:rounded-2xl w-full sm:max-w-lg sm:mx-4 h-[70vh] sm:h-[500px] flex flex-col">
            <!-- Header -->
            <div class="flex items-center justify-between p-4 border-b border-white/10">
                <h3 class="text-lg font-bold text-white flex items-center gap-2">
                    <span>💬</span> Chat Rápido
                </h3>
                <div class="flex items-center gap-2">
                    <a href="/chat/${bookId}" class="text-xs text-purple-400 hover:text-purple-300">Abrir página completa →</a>
                    <button onclick="closeQuickChat()" class="text-gray-400 hover:text-white ml-2">✕</button>
                </div>
            </div>
            
            <!-- Messages -->
            <div id="quickChatMessages" class="flex-1 overflow-y-auto p-4 space-y-3">
                <div class="flex gap-2">
                    <div class="w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center flex-shrink-0 text-sm">🤖</div>
                    <div class="bg-white/10 rounded-xl rounded-tl-none p-3 max-w-[80%]">
                        <p class="text-sm text-gray-200">Olá! Pergunte-me algo sobre este livro.</p>
                    </div>
                </div>
            </div>
            
            <!-- Input -->
            <div class="p-4 border-t border-white/10">
                <form onsubmit="sendQuickChatMessage(event)" class="flex gap-2">
                    <input type="text" id="quickChatInput" placeholder="Faça uma pergunta..."
                           class="flex-1 px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-purple-500">
                    <button type="submit" id="quickChatSendBtn" class="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 text-white text-sm rounded-lg transition-colors">
                        Enviar
                    </button>
                </form>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    document.getElementById('quickChatInput').focus();
}

/**
 * Send quick chat message
 */
async function sendQuickChatMessage(event) {
    event.preventDefault();
    
    const input = document.getElementById('quickChatInput');
    const sendBtn = document.getElementById('quickChatSendBtn');
    const message = input.value.trim();
    
    if (!message) return;
    
    // Add user message
    addQuickChatMessage(message, 'user');
    input.value = '';
    input.disabled = true;
    sendBtn.disabled = true;
    
    // Add to history
    quickChatHistory.push({ role: 'user', content: message });
    
    // Show typing
    addQuickChatTyping();
    
    try {
        const response = await fetch(`${API_BASE}/api/book/${quickChatBookId}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question: message,
                history: quickChatHistory
            })
        });
        
        const data = await response.json();
        removeQuickChatTyping();
        
        if (data.success) {
            addQuickChatMessage(data.answer, 'assistant');
            quickChatHistory.push({ role: 'assistant', content: data.answer });
        } else {
            addQuickChatMessage('Erro ao processar. Tente novamente.', 'error');
        }
    } catch (error) {
        removeQuickChatTyping();
        addQuickChatMessage('Erro de conexão.', 'error');
    } finally {
        input.disabled = false;
        sendBtn.disabled = false;
        input.focus();
    }
}

/**
 * Add message to quick chat
 */
function addQuickChatMessage(content, role) {
    const container = document.getElementById('quickChatMessages');
    const div = document.createElement('div');
    div.className = 'flex gap-2' + (role === 'user' ? ' justify-end' : '');
    
    if (role === 'user') {
        div.innerHTML = `
            <div class="bg-purple-600 rounded-xl rounded-tr-none p-3 max-w-[80%]">
                <p class="text-sm text-white">${escapeHtmlChat(content)}</p>
            </div>
            <div class="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center flex-shrink-0 text-sm">👤</div>
        `;
    } else if (role === 'assistant') {
        div.innerHTML = `
            <div class="w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center flex-shrink-0 text-sm">🤖</div>
            <div class="bg-white/10 rounded-xl rounded-tl-none p-3 max-w-[80%]">
                <p class="text-sm text-gray-200">${escapeHtmlChat(content).replace(/\n/g, '<br>')}</p>
            </div>
        `;
    } else {
        div.innerHTML = `
            <div class="w-8 h-8 rounded-full bg-red-600 flex items-center justify-center flex-shrink-0 text-sm">⚠️</div>
            <div class="bg-red-600/20 rounded-xl rounded-tl-none p-3 max-w-[80%]">
                <p class="text-sm text-red-300">${escapeHtmlChat(content)}</p>
            </div>
        `;
    }
    
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

/**
 * Add typing indicator
 */
function addQuickChatTyping() {
    const container = document.getElementById('quickChatMessages');
    const div = document.createElement('div');
    div.id = 'quickChatTyping';
    div.className = 'flex gap-2';
    div.innerHTML = `
        <div class="w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center flex-shrink-0 text-sm">🤖</div>
        <div class="bg-white/10 rounded-xl rounded-tl-none px-4 py-3">
            <div class="flex gap-1">
                <span class="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style="animation-delay: 0s"></span>
                <span class="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style="animation-delay: 0.1s"></span>
                <span class="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style="animation-delay: 0.2s"></span>
            </div>
        </div>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

/**
 * Remove typing indicator
 */
function removeQuickChatTyping() {
    const typing = document.getElementById('quickChatTyping');
    if (typing) typing.remove();
}

/**
 * Escape HTML for chat
 */
function escapeHtmlChat(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Close quick chat
 */
function closeQuickChat() {
    const modal = document.getElementById('quickChatModal');
    if (modal) modal.remove();
}

// ==================== CONTINUE STORY ====================

/**
 * Open continue story modal
 */
function openContinueStory(bookId) {
    const modal = document.createElement('div');
    modal.id = 'continueStoryModal';
    modal.className = 'fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50';
    modal.onclick = (e) => { if (e.target === modal) closeContinueStory(); };
    
    modal.innerHTML = `
        <div class="bg-gray-900 border border-white/20 rounded-2xl p-6 max-w-2xl mx-4 w-full max-h-[85vh] overflow-hidden flex flex-col">
            <!-- Header -->
            <div class="flex justify-between items-center mb-6">
                <h3 class="text-xl font-bold text-white flex items-center gap-2">
                    <span>📖</span> Continuar História
                </h3>
                <button onclick="closeContinueStory()" class="text-gray-400 hover:text-white">✕</button>
            </div>
            
            <!-- Options (shown initially) -->
            <div id="continueOptions" class="space-y-4">
                <p class="text-gray-400 text-sm">Escolha como quer continuar a história:</p>
                
                <!-- Continuation Types -->
                <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <button onclick="selectContinueType('chapter')" class="continue-type-btn p-4 bg-white/5 hover:bg-white/10 border-2 border-purple-500 rounded-xl text-center transition-all" data-type="chapter">
                        <span class="text-3xl block mb-2">📄</span>
                        <span class="text-white font-medium block">Próximo Capítulo</span>
                        <span class="text-xs text-gray-400">Continua de onde parou</span>
                    </button>
                    <button onclick="selectContinueType('epilogue')" class="continue-type-btn p-4 bg-white/5 hover:bg-white/10 border-2 border-white/10 hover:border-purple-500/50 rounded-xl text-center transition-all" data-type="epilogue">
                        <span class="text-3xl block mb-2">🔚</span>
                        <span class="text-white font-medium block">Epílogo</span>
                        <span class="text-xs text-gray-400">O que aconteceu depois</span>
                    </button>
                    <button onclick="selectContinueType('sequel')" class="continue-type-btn p-4 bg-white/5 hover:bg-white/10 border-2 border-white/10 hover:border-purple-500/50 rounded-xl text-center transition-all" data-type="sequel">
                        <span class="text-3xl block mb-2">📚</span>
                        <span class="text-white font-medium block">Sequela</span>
                        <span class="text-xs text-gray-400">Nova aventura</span>
                    </button>
                </div>
                
                <!-- Direction Input -->
                <div class="mt-4">
                    <label class="block text-sm text-gray-400 mb-2">Direção da história (opcional):</label>
                    <input type="text" id="storyDirection" placeholder="Ex: O protagonista descobre um segredo..."
                           class="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500">
                </div>
                
                <!-- Generate Button -->
                <button onclick="generateContinuation(${bookId})" id="generateContinueBtn" 
                        class="w-full py-3 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 disabled:from-gray-600 disabled:to-gray-600 text-white font-semibold rounded-xl transition-all flex items-center justify-center gap-2">
                    <span>✨</span> Gerar Continuação
                </button>
            </div>
            
            <!-- Loading -->
            <div id="continueLoading" class="hidden flex-1 flex flex-col items-center justify-center py-8">
                <div class="w-16 h-16 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mb-4"></div>
                <p class="text-white font-medium">A gerar continuação...</p>
                <p class="text-sm text-gray-400">Isto pode demorar alguns segundos</p>
            </div>
            
            <!-- Result -->
            <div id="continueResult" class="hidden flex-1 flex flex-col overflow-hidden">
                <div class="flex items-center justify-between mb-4">
                    <h4 id="resultTitle" class="text-lg font-semibold text-purple-400"></h4>
                    <div class="flex gap-2">
                        <button onclick="copyContinuation()" class="px-3 py-1 bg-white/10 hover:bg-white/20 text-gray-300 text-xs rounded transition-colors">
                            📋 Copiar
                        </button>
                        <button onclick="resetContinueModal()" class="px-3 py-1 bg-purple-600/30 hover:bg-purple-600/50 text-purple-300 text-xs rounded transition-colors">
                            🔄 Nova
                        </button>
                    </div>
                </div>
                <div id="continuationContent" class="flex-1 overflow-y-auto bg-white/5 rounded-lg p-4 text-gray-300 whitespace-pre-wrap leading-relaxed"></div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
}

let selectedContinueType = 'chapter';

/**
 * Select continuation type
 */
function selectContinueType(type) {
    selectedContinueType = type;
    document.querySelectorAll('.continue-type-btn').forEach(btn => {
        btn.classList.remove('border-purple-500');
        btn.classList.add('border-white/10');
    });
    document.querySelector(`[data-type="${type}"]`).classList.remove('border-white/10');
    document.querySelector(`[data-type="${type}"]`).classList.add('border-purple-500');
}

/**
 * Generate story continuation
 */
async function generateContinuation(bookId) {
    const direction = document.getElementById('storyDirection')?.value || '';
    const btn = document.getElementById('generateContinueBtn');
    
    // Show loading
    document.getElementById('continueOptions').classList.add('hidden');
    document.getElementById('continueLoading').classList.remove('hidden');
    
    try {
        const response = await fetch(`${API_BASE}/api/book/${bookId}/continue`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                type: selectedContinueType,
                direction: direction
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Show result
            document.getElementById('continueLoading').classList.add('hidden');
            document.getElementById('continueResult').classList.remove('hidden');
            
            const titles = {
                'chapter': '📄 Próximo Capítulo',
                'epilogue': '🔚 Epílogo',
                'sequel': '📚 Início da Sequela'
            };
            document.getElementById('resultTitle').textContent = titles[data.type] || 'Continuação';
            document.getElementById('continuationContent').textContent = data.continuation;
        } else {
            showToast(data.error || 'Erro ao gerar', 'error');
            resetContinueModal();
        }
    } catch (error) {
        console.error('Continue error:', error);
        showToast('Erro de conexão', 'error');
        resetContinueModal();
    }
}

/**
 * Copy continuation text
 */
function copyContinuation() {
    const content = document.getElementById('continuationContent').textContent;
    navigator.clipboard.writeText(content);
    showToast('Copiado!');
}

/**
 * Reset continue modal to initial state
 */
function resetContinueModal() {
    document.getElementById('continueOptions').classList.remove('hidden');
    document.getElementById('continueLoading').classList.add('hidden');
    document.getElementById('continueResult').classList.add('hidden');
    document.getElementById('storyDirection').value = '';
    selectedContinueType = 'chapter';
    selectContinueType('chapter');
}

/**
 * Close continue story modal
 */
function closeContinueStory() {
    const modal = document.getElementById('continueStoryModal');
    if (modal) modal.remove();
}
