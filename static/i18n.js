/**
 * BookCreatorAI - Internationalization (i18n)
 */

const translations = {
    'pt-pt': {
        nav_create: 'Criar Livro', nav_my_books: 'Meus Livros',
        hero_title: 'Crie Livros com', hero_highlight: 'Inteligência Artificial',
        hero_subtitle: 'Transforme as suas ideias em histórias completas. Basta inserir um tema e deixar a IA criar um livro único para si.',
        label_theme: 'Tema do Livro', placeholder_theme: 'Escreva o seu tema ou selecione um abaixo...',
        label_suggested: 'Temas sugeridos:', btn_other_themes: 'Outros temas',
        label_chapters: 'Número de Capítulos', hint_chapters: 'Entre 1 e 20 capítulos',
        label_pages: 'Número de Páginas', hint_pages: '~250 palavras por página',
        label_style: 'Estilo Literário', label_book_lang: 'Idioma do Livro',
        hint_multi_lang: 'Selecione um ou mais idiomas (gera um livro por idioma)',
        btn_generate: 'Gerar Livro',
        loading_title: 'A gerar o seu livro...', loading_subtitle: 'Isto pode demorar alguns minutos',
        success_title: 'Livro Criado com Sucesso!', btn_view: 'Ver Livro',
        error_title: 'Erro ao Gerar Livro', error_theme: 'Por favor, insira um tema para o livro.',
        feature1_title: 'Geração Rápida', feature1_desc: 'Crie livros completos em minutos com a potência da IA Gemini',
        feature2_title: 'Múltiplos Estilos', feature2_desc: 'Escolha entre romance, fantasia, terror, ficção científica e muito mais',
        feature3_title: 'Download Fácil', feature3_desc: 'Transfira os seus livros em formato .txt ou .md',
        footer: 'BookCreatorAI © 2024 - Criado com IA Gemini',
        list_title: 'Meus Livros', list_subtitle: 'Todos os livros que criou com IA',
        btn_new: 'Novo Livro', empty_title: 'Nenhum livro ainda', empty_subtitle: 'Comece a criar o seu primeiro livro com IA',
        btn_first: 'Criar Primeiro Livro', chapters: 'capítulos',
        delete_title: 'Eliminar Livro?', delete_msg: 'Esta ação não pode ser revertida.',
        btn_cancel: 'Cancelar', btn_delete: 'Eliminar',
        btn_back: 'Voltar aos livros', index: 'Índice', full_text: 'Texto Completo', theme: 'Tema:',
        // Styles
        s_romance: 'Romance', s_scifi: 'Ficção Científica', s_fantasy: 'Fantasia', s_horror: 'Terror',
        s_crime: 'Policial', s_children: 'Infantil', s_adventure: 'Aventura', s_drama: 'Drama',
        s_comedy: 'Comédia', s_historical: 'Histórico', s_suspense: 'Suspense', s_autobiography: 'Autobiografia',
        s_technical: '📚 Técnico / Não-Ficção', s_tutorial: '📖 Tutorial / Guia Prático',
        s_educational: '🎓 Educacional / Didático', s_selfhelp: '💡 Autoajuda / Desenvolvimento',
        // Pages
        p_10: '~10 páginas (conto)', p_20: '~20 páginas (história curta)', p_50: '~50 páginas (novela curta)',
        p_100: '~100 páginas (novela)', p_150: '~150 páginas (romance curto)', p_200: '~200 páginas (romance)'
    },
    'pt-br': {
        nav_create: 'Criar Livro', nav_my_books: 'Meus Livros',
        hero_title: 'Crie Livros com', hero_highlight: 'Inteligência Artificial',
        hero_subtitle: 'Transforme suas ideias em histórias completas. Basta inserir um tema e deixar a IA criar um livro único para você.',
        label_theme: 'Tema do Livro', placeholder_theme: 'Escreva seu tema ou selecione um abaixo...',
        label_suggested: 'Temas sugeridos:', btn_other_themes: 'Outros temas',
        label_chapters: 'Número de Capítulos', hint_chapters: 'Entre 1 e 20 capítulos',
        label_pages: 'Número de Páginas', hint_pages: '~250 palavras por página',
        label_style: 'Estilo Literário', label_book_lang: 'Idioma do Livro',
        hint_multi_lang: 'Selecione um ou mais idiomas (gera um livro por idioma)',
        btn_generate: 'Gerar Livro',
        loading_title: 'Gerando seu livro...', loading_subtitle: 'Isso pode demorar alguns minutos',
        success_title: 'Livro Criado com Sucesso!', btn_view: 'Ver Livro',
        error_title: 'Erro ao Gerar Livro', error_theme: 'Por favor, insira um tema para o livro.',
        feature1_title: 'Geração Rápida', feature1_desc: 'Crie livros completos em minutos com o poder da IA Gemini',
        feature2_title: 'Múltiplos Estilos', feature2_desc: 'Escolha entre romance, fantasia, terror, ficção científica e muito mais',
        feature3_title: 'Download Fácil', feature3_desc: 'Baixe seus livros em formato .txt ou .md',
        footer: 'BookCreatorAI © 2024 - Criado com IA Gemini',
        list_title: 'Meus Livros', list_subtitle: 'Todos os livros que você criou com IA',
        btn_new: 'Novo Livro', empty_title: 'Nenhum livro ainda', empty_subtitle: 'Comece a criar seu primeiro livro com IA',
        btn_first: 'Criar Primeiro Livro', chapters: 'capítulos',
        delete_title: 'Excluir Livro?', delete_msg: 'Esta ação não pode ser desfeita.',
        btn_cancel: 'Cancelar', btn_delete: 'Excluir',
        btn_back: 'Voltar aos livros', index: 'Índice', full_text: 'Texto Completo', theme: 'Tema:',
        s_romance: 'Romance', s_scifi: 'Ficção Científica', s_fantasy: 'Fantasia', s_horror: 'Terror',
        s_crime: 'Policial', s_children: 'Infantil', s_adventure: 'Aventura', s_drama: 'Drama',
        s_comedy: 'Comédia', s_historical: 'Histórico', s_suspense: 'Suspense', s_autobiography: 'Autobiografia',
        s_technical: '📚 Técnico / Não-Ficção', s_tutorial: '📖 Tutorial / Guia Prático',
        s_educational: '🎓 Educacional / Didático', s_selfhelp: '💡 Autoajuda / Desenvolvimento',
        p_10: '~10 páginas (conto)', p_20: '~20 páginas (história curta)', p_50: '~50 páginas (novela curta)',
        p_100: '~100 páginas (novela)', p_150: '~150 páginas (romance curto)', p_200: '~200 páginas (romance)'
    },
    'en': {
        nav_create: 'Create Book', nav_my_books: 'My Books',
        hero_title: 'Create Books with', hero_highlight: 'Artificial Intelligence',
        hero_subtitle: 'Transform your ideas into complete stories. Just enter a theme and let AI create a unique book for you.',
        label_theme: 'Book Theme', placeholder_theme: 'Write your theme or select one below...',
        label_suggested: 'Suggested themes:', btn_other_themes: 'Other themes',
        label_chapters: 'Number of Chapters', hint_chapters: 'Between 1 and 20 chapters',
        label_pages: 'Number of Pages', hint_pages: '~250 words per page',
        label_style: 'Literary Style', label_book_lang: 'Book Language',
        hint_multi_lang: 'Select one or more languages (generates one book per language)',
        btn_generate: 'Generate Book',
        loading_title: 'Generating your book...', loading_subtitle: 'This may take a few minutes',
        success_title: 'Book Created Successfully!', btn_view: 'View Book',
        error_title: 'Error Generating Book', error_theme: 'Please enter a theme for the book.',
        feature1_title: 'Fast Generation', feature1_desc: 'Create complete books in minutes with Gemini AI power',
        feature2_title: 'Multiple Styles', feature2_desc: 'Choose from romance, fantasy, horror, science fiction and more',
        feature3_title: 'Easy Download', feature3_desc: 'Download your books in .txt or .md format',
        footer: 'BookCreatorAI © 2024 - Created with Gemini AI',
        list_title: 'My Books', list_subtitle: 'All books you created with AI',
        btn_new: 'New Book', empty_title: 'No books yet', empty_subtitle: 'Start creating your first book with AI',
        btn_first: 'Create First Book', chapters: 'chapters',
        delete_title: 'Delete Book?', delete_msg: 'This action cannot be undone.',
        btn_cancel: 'Cancel', btn_delete: 'Delete',
        btn_back: 'Back to books', index: 'Index', full_text: 'Full Text', theme: 'Theme:',
        s_romance: 'Romance', s_scifi: 'Science Fiction', s_fantasy: 'Fantasy', s_horror: 'Horror',
        s_crime: 'Crime', s_children: 'Children', s_adventure: 'Adventure', s_drama: 'Drama',
        s_comedy: 'Comedy', s_historical: 'Historical', s_suspense: 'Suspense', s_autobiography: 'Autobiography',
        s_technical: '📚 Technical / Non-Fiction', s_tutorial: '📖 Tutorial / Practical Guide',
        s_educational: '🎓 Educational / Didactic', s_selfhelp: '💡 Self-Help / Development',
        p_10: '~10 pages (short story)', p_20: '~20 pages (short story)', p_50: '~50 pages (novella)',
        p_100: '~100 pages (novel)', p_150: '~150 pages (short novel)', p_200: '~200 pages (novel)'
    },
    'fr': {
        nav_create: 'Créer un Livre', nav_my_books: 'Mes Livres',
        hero_title: 'Créez des Livres avec', hero_highlight: "l'Intelligence Artificielle",
        hero_subtitle: "Transformez vos idées en histoires complètes. Entrez un thème et laissez l'IA créer un livre unique.",
        label_theme: 'Thème du Livre', placeholder_theme: 'Écrivez votre thème ou sélectionnez-en un...',
        label_suggested: 'Thèmes suggérés:', btn_other_themes: 'Autres thèmes',
        label_chapters: 'Nombre de Chapitres', hint_chapters: 'Entre 1 et 20 chapitres',
        label_pages: 'Nombre de Pages', hint_pages: '~250 mots par page',
        label_style: 'Style Littéraire', label_book_lang: 'Langue du Livre',
        hint_multi_lang: 'Sélectionnez une ou plusieurs langues (génère un livre par langue)',
        btn_generate: 'Générer le Livre',
        loading_title: 'Génération en cours...', loading_subtitle: 'Cela peut prendre quelques minutes',
        success_title: 'Livre Créé avec Succès!', btn_view: 'Voir le Livre',
        error_title: 'Erreur de Génération', error_theme: 'Veuillez entrer un thème.',
        feature1_title: 'Génération Rapide', feature1_desc: 'Créez des livres complets en minutes avec Gemini AI',
        feature2_title: 'Styles Multiples', feature2_desc: 'Choisissez parmi romance, fantasy, horreur et plus',
        feature3_title: 'Téléchargement Facile', feature3_desc: 'Téléchargez en format .txt ou .md',
        footer: 'BookCreatorAI © 2024 - Créé avec Gemini AI',
        list_title: 'Mes Livres', list_subtitle: "Tous les livres créés avec l'IA",
        btn_new: 'Nouveau Livre', empty_title: 'Aucun livre', empty_subtitle: "Créez votre premier livre avec l'IA",
        btn_first: 'Créer le Premier', chapters: 'chapitres',
        delete_title: 'Supprimer?', delete_msg: 'Cette action est irréversible.',
        btn_cancel: 'Annuler', btn_delete: 'Supprimer',
        btn_back: 'Retour', index: 'Index', full_text: 'Texte Complet', theme: 'Thème:',
        s_romance: 'Romance', s_scifi: 'Science-Fiction', s_fantasy: 'Fantaisie', s_horror: 'Horreur',
        s_crime: 'Policier', s_children: 'Enfants', s_adventure: 'Aventure', s_drama: 'Drame',
        s_comedy: 'Comédie', s_historical: 'Historique', s_suspense: 'Suspense', s_autobiography: 'Autobiographie',
        s_technical: '📚 Technique / Non-Fiction', s_tutorial: '📖 Tutoriel / Guide',
        s_educational: '🎓 Éducatif', s_selfhelp: '💡 Développement Personnel',
        p_10: '~10 pages', p_20: '~20 pages', p_50: '~50 pages', p_100: '~100 pages', p_150: '~150 pages', p_200: '~200 pages'
    },
    'de': {
        nav_create: 'Buch Erstellen', nav_my_books: 'Meine Bücher',
        hero_title: 'Bücher Erstellen mit', hero_highlight: 'Künstlicher Intelligenz',
        hero_subtitle: 'Verwandeln Sie Ihre Ideen in Geschichten. Geben Sie ein Thema ein und lassen Sie die KI ein Buch erstellen.',
        label_theme: 'Buchthema', placeholder_theme: 'Schreiben Sie Ihr Thema oder wählen Sie eines...',
        label_suggested: 'Vorgeschlagene Themen:', btn_other_themes: 'Andere Themen',
        label_chapters: 'Anzahl Kapitel', hint_chapters: 'Zwischen 1 und 20',
        label_pages: 'Seitenzahl', hint_pages: '~250 Wörter pro Seite',
        label_style: 'Literarischer Stil', label_book_lang: 'Buchsprache',
        hint_multi_lang: 'Wählen Sie eine oder mehrere Sprachen (erstellt ein Buch pro Sprache)',
        btn_generate: 'Buch Generieren',
        loading_title: 'Wird generiert...', loading_subtitle: 'Dies kann einige Minuten dauern',
        success_title: 'Buch Erstellt!', btn_view: 'Buch Ansehen',
        error_title: 'Fehler', error_theme: 'Bitte geben Sie ein Thema ein.',
        feature1_title: 'Schnelle Generierung', feature1_desc: 'Erstellen Sie Bücher in Minuten mit Gemini AI',
        feature2_title: 'Mehrere Stile', feature2_desc: 'Wählen Sie aus Romantik, Fantasy, Horror und mehr',
        feature3_title: 'Einfacher Download', feature3_desc: 'Download in .txt oder .md Format',
        footer: 'BookCreatorAI © 2024 - Erstellt mit Gemini AI',
        list_title: 'Meine Bücher', list_subtitle: 'Alle mit KI erstellten Bücher',
        btn_new: 'Neues Buch', empty_title: 'Keine Bücher', empty_subtitle: 'Erstellen Sie Ihr erstes Buch',
        btn_first: 'Erstes Buch Erstellen', chapters: 'Kapitel',
        delete_title: 'Buch Löschen?', delete_msg: 'Diese Aktion kann nicht rückgängig gemacht werden.',
        btn_cancel: 'Abbrechen', btn_delete: 'Löschen',
        btn_back: 'Zurück', index: 'Index', full_text: 'Volltext', theme: 'Thema:',
        s_romance: 'Romantik', s_scifi: 'Science-Fiction', s_fantasy: 'Fantasy', s_horror: 'Horror',
        s_crime: 'Krimi', s_children: 'Kinder', s_adventure: 'Abenteuer', s_drama: 'Drama',
        s_comedy: 'Komödie', s_historical: 'Historisch', s_suspense: 'Spannung', s_autobiography: 'Autobiografie',
        s_technical: '📚 Technisch / Sachbuch', s_tutorial: '📖 Tutorial / Leitfaden',
        s_educational: '🎓 Pädagogisch', s_selfhelp: '💡 Selbsthilfe',
        p_10: '~10 Seiten', p_20: '~20 Seiten', p_50: '~50 Seiten', p_100: '~100 Seiten', p_150: '~150 Seiten', p_200: '~200 Seiten'
    },
    'it': {
        nav_create: 'Crea Libro', nav_my_books: 'I Miei Libri',
        hero_title: 'Crea Libri con', hero_highlight: "l'Intelligenza Artificiale",
        hero_subtitle: "Trasforma le tue idee in storie complete. Inserisci un tema e lascia che l'IA crei un libro unico.",
        label_theme: 'Tema del Libro', placeholder_theme: 'Scrivi il tuo tema o selezionane uno...',
        label_suggested: 'Temi suggeriti:', btn_other_themes: 'Altri temi',
        label_chapters: 'Numero Capitoli', hint_chapters: 'Tra 1 e 20 capitoli',
        label_pages: 'Numero Pagine', hint_pages: '~250 parole per pagina',
        label_style: 'Stile Letterario', label_book_lang: 'Lingua del Libro',
        hint_multi_lang: 'Seleziona una o più lingue (genera un libro per lingua)',
        btn_generate: 'Genera Libro',
        loading_title: 'Generazione in corso...', loading_subtitle: 'Questo può richiedere alcuni minuti',
        success_title: 'Libro Creato!', btn_view: 'Vedi Libro',
        error_title: 'Errore', error_theme: 'Per favore inserisci un tema.',
        feature1_title: 'Generazione Veloce', feature1_desc: 'Crea libri completi in minuti con Gemini AI',
        feature2_title: 'Stili Multipli', feature2_desc: 'Scegli tra romantico, fantasy, horror e altro',
        feature3_title: 'Download Facile', feature3_desc: 'Scarica in formato .txt o .md',
        footer: 'BookCreatorAI © 2024 - Creato con Gemini AI',
        list_title: 'I Miei Libri', list_subtitle: "Tutti i libri creati con l'IA",
        btn_new: 'Nuovo Libro', empty_title: 'Nessun libro', empty_subtitle: "Crea il tuo primo libro con l'IA",
        btn_first: 'Crea il Primo', chapters: 'capitoli',
        delete_title: 'Eliminare?', delete_msg: 'Questa azione non può essere annullata.',
        btn_cancel: 'Annulla', btn_delete: 'Elimina',
        btn_back: 'Indietro', index: 'Indice', full_text: 'Testo Completo', theme: 'Tema:',
        s_romance: 'Romantico', s_scifi: 'Fantascienza', s_fantasy: 'Fantasy', s_horror: 'Horror',
        s_crime: 'Poliziesco', s_children: 'Bambini', s_adventure: 'Avventura', s_drama: 'Dramma',
        s_comedy: 'Commedia', s_historical: 'Storico', s_suspense: 'Suspense', s_autobiography: 'Autobiografia',
        s_technical: '📚 Tecnico / Non-Fiction', s_tutorial: '📖 Tutorial / Guida',
        s_educational: '🎓 Educativo', s_selfhelp: '💡 Auto-Aiuto',
        p_10: '~10 pagine', p_20: '~20 pagine', p_50: '~50 pagine', p_100: '~100 pagine', p_150: '~150 pagine', p_200: '~200 pagine'
    }
};

let currentUILang = localStorage.getItem('uiLanguage') || 'pt-pt';

function t(key) {
    return translations[currentUILang]?.[key] || translations['pt-pt'][key] || key;
}

function changeUILanguage(lang) {
    currentUILang = lang;
    localStorage.setItem('uiLanguage', lang);
    applyTranslations();
    const sel = document.getElementById('uiLangSelect');
    if (sel) sel.value = lang;
}

function applyTranslations() {
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        el.textContent = t(key);
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        el.placeholder = t(el.getAttribute('data-i18n-placeholder'));
    });
    // Update style select
    const styleSelect = document.getElementById('style');
    if (styleSelect) {
        const map = {romance:'s_romance',ficcao_cientifica:'s_scifi',fantasia:'s_fantasy',terror:'s_horror',
            policial:'s_crime',infantil:'s_children',aventura:'s_adventure',drama:'s_drama',comedia:'s_comedy',
            historico:'s_historical',suspense:'s_suspense',autobiografia:'s_autobiography',tecnico:'s_technical',
            tutorial:'s_tutorial',educacional:'s_educational',autoajuda:'s_selfhelp'};
        Array.from(styleSelect.options).forEach(opt => {
            if (map[opt.value]) opt.textContent = t(map[opt.value]);
        });
    }
    // Update pages select
    const pagesSelect = document.getElementById('numPages');
    if (pagesSelect) {
        const map = {'10':'p_10','20':'p_20','50':'p_50','100':'p_100','150':'p_150','200':'p_200'};
        Array.from(pagesSelect.options).forEach(opt => {
            if (map[opt.value]) opt.textContent = t(map[opt.value]);
        });
    }
}

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    const sel = document.getElementById('uiLangSelect');
    if (sel) {
        sel.value = currentUILang;
        sel.addEventListener('change', (e) => changeUILanguage(e.target.value));
    }
    applyTranslations();
});
