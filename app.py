from flask import Flask, render_template, request, jsonify, Response
import google.generativeai as genai
import json
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

from models.book import db, Book, Series
import config

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY

# Use absolute path for database
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'database', 'books.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

# Configure Gemini API
print(f"DEBUG: API KEY FOUND? {'Yes' if config.GEMINI_API_KEY else 'No'}")
if not config.GEMINI_API_KEY:
    print("ERROR: GEMINI_API_KEY is missing from environment variables!")

genai.configure(api_key=config.GEMINI_API_KEY)

def generate_book_with_gemini(theme, style, num_chapters, num_pages=50, language='pt-pt'):
    """
    Generate a complete book using Google Gemini API.
    Returns title, chapters list, and full text.
    """
    # Calculate words: ~250 words per page
    total_words = num_pages * 250
    words_per_chapter = total_words // num_chapters
    
    # Language configuration
    language_config = {
        'pt-pt': {
            'name': 'Português de Portugal',
            'chapter': 'Capítulo',
            'instructions': 'Escreve em Português Europeu (Portugal), usando vocabulário e expressões típicas de Portugal.'
        },
        'pt-br': {
            'name': 'Português do Brasil',
            'chapter': 'Capítulo',
            'instructions': 'Escreve em Português Brasileiro, usando vocabulário e expressões típicas do Brasil.'
        },
        'en': {
            'name': 'English',
            'chapter': 'Chapter',
            'instructions': 'Write in English, using proper grammar and vocabulary.'
        },
        'fr': {
            'name': 'Français',
            'chapter': 'Chapitre',
            'instructions': 'Écris en Français, en utilisant un vocabulaire et une grammaire corrects.'
        },
        'de': {
            'name': 'Deutsch',
            'chapter': 'Kapitel',
            'instructions': 'Schreibe auf Deutsch mit korrekter Grammatik und Wortschatz.'
        },
        'it': {
            'name': 'Italiano',
            'chapter': 'Capitolo',
            'instructions': 'Scrivi in Italiano, usando vocabolario e grammatica corretti.'
        }
    }
    
    lang = language_config.get(language, language_config['pt-pt'])
    chapter_word = lang['chapter']
    
    # Style-specific instructions
    style_instructions = {
        'tecnico': 'Escreve de forma técnica e informativa, com explicações claras, exemplos práticos e linguagem profissional. Inclui definições, conceitos-chave e referências quando apropriado.',
        'tutorial': 'Escreve como um guia passo-a-passo, com instruções claras, dicas práticas, exemplos concretos e exercícios. Usa uma linguagem acessível e direta.',
        'educacional': 'Escreve de forma didática e pedagógica, com explicações progressivas, exemplos ilustrativos, resumos e perguntas de revisão. Adequado para aprendizagem.',
        'autoajuda': 'Escreve de forma motivacional e prática, com reflexões, exercícios de autoconhecimento, histórias inspiradoras e estratégias aplicáveis ao dia-a-dia.'
    }
    
    style_extra = style_instructions.get(style, '')
    is_technical = style in ['tecnico', 'tutorial', 'educacional', 'autoajuda']
    
    prompt = f"""Cria um livro completo.
Tema: {theme}.
Estilo literário: {style}.
Número de capítulos: {num_chapters}.
Número total de páginas: aproximadamente {num_pages} páginas.
Total de palavras: aproximadamente {total_words} palavras.
Idioma: {lang['name']}.

{lang['instructions']}

Gera:
1. Um título original e apelativo
2. Uma lista de capítulos numerada
3. O texto completo do livro, com narrativa contínua e coerente, com subtítulo de cada capítulo.

IMPORTANTE: 
- O livro DEVE ser escrito inteiramente em {lang['name']}.
- O livro deve ter aproximadamente {num_pages} páginas ({total_words} palavras no total).
- Cada capítulo deve ter aproximadamente {words_per_chapter} palavras.
{f'- {style_extra}' if style_extra else '- Escreve uma narrativa rica, detalhada e envolvente.'}
{f'- Para livros técnicos: inclui introdução, conceitos fundamentais, exemplos práticos, e conclusão em cada capítulo.' if is_technical else ''}
- Formata a resposta EXATAMENTE assim:

===TÍTULO===
[Título do livro aqui]

===ÍNDICE===
{chapter_word} 1: [Nome do capítulo]
{chapter_word} 2: [Nome do capítulo]
[... continuar para todos os capítulos]

===TEXTO COMPLETO===
[Texto completo do livro com todos os capítulos, cada um começando com "{chapter_word} X: Nome"]
"""

    try:
        # Use Gemini Pro model
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        
        if response and response.text:
            return parse_book_response(response.text)
        else:
            raise Exception("Resposta vazia do Gemini")
            
    except Exception as e:
        raise Exception(f"Erro ao gerar livro: {str(e)}")

def translate_book_with_gemini(original_book, target_language):
    """
    Translate an existing book to a target language using Gemini API.
    Maintains the same story, just in a different language.
    """
    language_config = {
        'pt-pt': {'name': 'Português de Portugal', 'chapter': 'Capítulo'},
        'pt-br': {'name': 'Português do Brasil', 'chapter': 'Capítulo'},
        'en': {'name': 'English', 'chapter': 'Chapter'},
        'fr': {'name': 'Français', 'chapter': 'Chapitre'},
        'de': {'name': 'Deutsch', 'chapter': 'Kapitel'},
        'it': {'name': 'Italiano', 'chapter': 'Capitolo'}
    }
    
    lang = language_config.get(target_language, language_config['pt-pt'])
    chapter_word = lang['chapter']
    
    prompt = f"""Traduz o seguinte livro para {lang['name']}.
Mantém a mesma história, personagens, enredo e estrutura.
Adapta apenas o idioma, mantendo o estilo e tom do original.

LIVRO ORIGINAL:
Título: {original_book['title']}

Índice:
{chr(10).join(original_book['chapters'])}

Texto completo:
{original_book['full_text']}

IMPORTANTE:
- Traduz TUDO para {lang['name']}.
- Mantém a mesma estrutura de capítulos.
- Os capítulos devem usar a palavra "{chapter_word}" em vez do original.
- Mantém a mesma história e detalhes, apenas traduzidos.

Formata a resposta EXATAMENTE assim:

===TÍTULO===
[Título traduzido]

===ÍNDICE===
{chapter_word} 1: [Nome traduzido]
{chapter_word} 2: [Nome traduzido]
[... todos os capítulos]

===TEXTO COMPLETO===
[Texto completo traduzido]
"""

    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        
        if response and response.text:
            return parse_book_response(response.text)
        else:
            raise Exception("Resposta vazia do Gemini na tradução")
            
    except Exception as e:
        raise Exception(f"Erro ao traduzir livro: {str(e)}")

def parse_book_response(response_text):
    """
    Parse the Gemini response to extract title, chapters, and full text.
    """
    title = "Livro Sem Título"
    chapters = []
    full_text = ""
    
    try:
        # Try to parse structured response
        if "===TÍTULO===" in response_text:
            parts = response_text.split("===")
            
            for i, part in enumerate(parts):
                if "TÍTULO" in part and i + 1 < len(parts):
                    title = parts[i + 1].strip()
                elif "ÍNDICE" in part and i + 1 < len(parts):
                    index_text = parts[i + 1].strip()
                    # Extract chapter names
                    for line in index_text.split('\n'):
                        line = line.strip()
                        if line and ('Capítulo' in line or 'capitulo' in line.lower()):
                            chapters.append(line)
                elif "TEXTO COMPLETO" in part and i + 1 < len(parts):
                    full_text = parts[i + 1].strip()
        else:
            # Fallback: try to extract from unstructured response
            lines = response_text.split('\n')
            
            # First non-empty line might be the title
            for line in lines:
                if line.strip():
                    title = line.strip().replace('#', '').strip()
                    break
            
            # Extract chapters from lines containing "Capítulo"
            for line in lines:
                if 'Capítulo' in line or 'capitulo' in line.lower():
                    if ':' in line:
                        chapters.append(line.strip())
            
            # Full text is everything
            full_text = response_text
        
        # Ensure we have at least some chapters
        if not chapters:
            chapters = ["Capítulo 1: Início", "Capítulo 2: Desenvolvimento", "Capítulo 3: Conclusão"]
        
        # Ensure full_text is not empty
        if not full_text:
            full_text = response_text
            
    except Exception as e:
        print(f"Error parsing response: {e}")
        title = "Livro Gerado"
        chapters = ["Capítulo 1"]
        full_text = response_text
    
    return {
        'title': title,
        'chapters': chapters,
        'full_text': full_text
    }

# Routes
@app.route('/')
def index():
    """Home page with book generation form"""
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    """Generate a new book using Gemini API"""
    try:
        data = request.get_json()
        
        theme = data.get('theme', '').strip()
        style = data.get('style', 'romance').strip()
        num_chapters = int(data.get('num_chapters', 5))
        num_pages = int(data.get('num_pages', 50))
        languages = data.get('languages', ['pt-pt'])
        
        # Handle single language (backwards compatibility)
        if isinstance(languages, str):
            languages = [languages]
        
        if not theme:
            return jsonify({'success': False, 'error': 'Por favor, insira um tema para o livro.'}), 400
        
        if num_chapters < 1 or num_chapters > 20:
            return jsonify({'success': False, 'error': 'Número de capítulos deve ser entre 1 e 20.'}), 400
        
        if num_pages < 5 or num_pages > 300:
            return jsonify({'success': False, 'error': 'Número de páginas deve ser entre 5 e 300.'}), 400
        
        if not languages or len(languages) == 0:
            return jsonify({'success': False, 'error': 'Por favor, selecione pelo menos um idioma.'}), 400
        
        # Generate a book for each selected language
        created_books = []
        original_book_data = None
        
        for i, language in enumerate(languages):
            if i == 0:
                # Generate the first book from scratch
                book_data = generate_book_with_gemini(theme, style, num_chapters, num_pages, language)
                original_book_data = book_data
            else:
                # Translate the original book to this language
                book_data = translate_book_with_gemini(original_book_data, language)
            
            # Create new book record
            new_book = Book(
                title=book_data['title'],
                theme=theme,
                style=style,
                full_text=book_data['full_text'],
                language=language
            )
            new_book.set_chapters(book_data['chapters'])
            new_book.word_count = new_book.calculate_word_count()
            
            # Save to database
            db.session.add(new_book)
            db.session.commit()
            
            created_books.append({
                'id': new_book.id,
                'title': new_book.title,
                'language': language
            })
        
        # Return response
        if len(created_books) == 1:
            return jsonify({
                'success': True,
                'book_id': created_books[0]['id'],
                'title': created_books[0]['title'],
                'message': 'Livro gerado com sucesso!'
            })
        else:
            return jsonify({
                'success': True,
                'books': created_books,
                'message': f'{len(created_books)} livros gerados com sucesso!'
            })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/books')
def list_books():
    """List all generated books"""
    return render_template('list_books.html')

@app.route('/api/books')
def api_books():
    """API endpoint to get all books"""
    books = Book.query.order_by(Book.created_at.desc()).all()
    return jsonify({
        'success': True,
        'books': [book.to_dict() for book in books]
    })

@app.route('/book/<int:book_id>')
def view_book(book_id):
    """View a specific book"""
    book = Book.query.get_or_404(book_id)
    return render_template('view_book.html', book=book)

@app.route('/api/book/<int:book_id>')
def api_book(book_id):
    """API endpoint to get a specific book"""
    book = Book.query.get_or_404(book_id)
    return jsonify({
        'success': True,
        'book': book.to_dict()
    })

@app.route('/download/<int:book_id>')
def download_book(book_id):
    """Download book as .txt file"""
    book = Book.query.get_or_404(book_id)
    
    # Format the book content
    content = f"""{'=' * 60}
{book.title.upper()}
{'=' * 60}

Tema: {book.theme}
Estilo: {book.style}
Data de Criação: {book.created_at.strftime('%d/%m/%Y %H:%M')}

{'=' * 60}
ÍNDICE
{'=' * 60}

"""
    
    for chapter in book.get_chapters():
        content += f"{chapter}\n"
    
    content += f"""
{'=' * 60}
TEXTO COMPLETO
{'=' * 60}

{book.full_text}

{'=' * 60}
FIM
{'=' * 60}

Gerado por BookCreatorAI
"""
    
    # Create response with file download
    filename = f"{book.title.replace(' ', '_')[:50]}.txt"
    
    return Response(
        content,
        mimetype='text/plain; charset=utf-8',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Type': 'text/plain; charset=utf-8'
        }
    )

@app.route('/download/<int:book_id>/md')
def download_book_md(book_id):
    """Download book as .md file"""
    book = Book.query.get_or_404(book_id)
    
    # Format the book content in Markdown
    content = f"""# {book.title}

**Tema:** {book.theme}  
**Estilo:** {book.style}  
**Data de Criação:** {book.created_at.strftime('%d/%m/%Y %H:%M')}

---

## Índice

"""
    
    for chapter in book.get_chapters():
        content += f"- {chapter}\n"
    
    content += f"""
---

## Texto Completo

{book.full_text}

---

*Gerado por BookCreatorAI*
"""
    
    # Create response with file download
    filename = f"{book.title.replace(' ', '_')[:50]}.md"
    
    return Response(
        content,
        mimetype='text/markdown; charset=utf-8',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Type': 'text/markdown; charset=utf-8'
        }
    )

@app.route('/delete/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    """Delete a book"""
    try:
        book = Book.query.get_or_404(book_id)
        db.session.delete(book)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Livro eliminado com sucesso!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== NEW FEATURES ====================

@app.route('/download/<int:book_id>/pdf')
def download_book_pdf(book_id):
    """Download book as PDF file"""
    from utils.exports import generate_pdf
    
    book = Book.query.get_or_404(book_id)
    
    try:
        pdf_bytes = generate_pdf(book)
        filename = f"{book.title.replace(' ', '_')[:50]}.pdf"
        
        return Response(
            pdf_bytes,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Type': 'application/pdf'
            }
        )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/download/<int:book_id>/epub')
def download_book_epub(book_id):
    """Download book as EPUB file"""
    from utils.exports import generate_epub
    
    book = Book.query.get_or_404(book_id)
    
    try:
        epub_bytes = generate_epub(book)
        filename = f"{book.title.replace(' ', '_')[:50]}.epub"
        
        return Response(
            epub_bytes,
            mimetype='application/epub+zip',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Type': 'application/epub+zip'
            }
        )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/book/<int:book_id>/favorite', methods=['POST'])
def toggle_favorite(book_id):
    """Toggle favorite status of a book"""
    try:
        book = Book.query.get_or_404(book_id)
        book.is_favorite = not book.is_favorite
        db.session.commit()
        return jsonify({
            'success': True,
            'is_favorite': book.is_favorite,
            'message': 'Adicionado aos favoritos!' if book.is_favorite else 'Removido dos favoritos!'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/book/<int:book_id>/tags', methods=['POST'])
def update_tags(book_id):
    """Add or remove tags from a book"""
    try:
        book = Book.query.get_or_404(book_id)
        data = request.get_json()
        
        action = data.get('action', 'set')  # 'add', 'remove', or 'set'
        tags = data.get('tags', [])
        
        if action == 'add':
            for tag in tags:
                book.add_tag(tag.strip())
        elif action == 'remove':
            for tag in tags:
                book.remove_tag(tag.strip())
        else:  # set
            book.set_tags([t.strip() for t in tags])
        
        db.session.commit()
        return jsonify({
            'success': True,
            'tags': book.get_tags(),
            'message': 'Tags atualizadas!'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/books/search')
def search_books():
    """Search books by title, theme, or tags"""
    query = request.args.get('q', '').strip().lower()
    tag = request.args.get('tag', '').strip()
    favorites_only = request.args.get('favorites', '').lower() == 'true'
    style = request.args.get('style', '').strip()
    language = request.args.get('language', '').strip()
    
    books = Book.query
    
    if favorites_only:
        books = books.filter(Book.is_favorite == True)
    
    if style:
        books = books.filter(Book.style == style)
    
    if language:
        books = books.filter(Book.language == language)
    
    books = books.order_by(Book.created_at.desc()).all()
    
    # Filter by query and tags in Python (SQLite doesn't support good JSON queries)
    results = []
    for book in books:
        # Search in title and theme
        if query:
            if query not in book.title.lower() and query not in book.theme.lower():
                continue
        
        # Filter by tag
        if tag:
            book_tags = [t.lower() for t in book.get_tags()]
            if tag.lower() not in book_tags:
                continue
        
        results.append(book.to_dict())
    
    return jsonify({
        'success': True,
        'books': results,
        'count': len(results)
    })

@app.route('/api/books/tags')
def get_all_tags():
    """Get all unique tags used across all books"""
    books = Book.query.all()
    all_tags = set()
    
    for book in books:
        for tag in book.get_tags():
            all_tags.add(tag)
    
    return jsonify({
        'success': True,
        'tags': sorted(list(all_tags))
    })

@app.route('/api/book/<int:book_id>/stats')
def get_book_stats(book_id):
    """Get detailed statistics for a book"""
    book = Book.query.get_or_404(book_id)
    
    stats = book.get_stats()
    stats['title'] = book.title
    stats['style'] = book.style
    stats['language'] = book.language
    stats['created_at'] = book.created_at.strftime('%Y-%m-%d %H:%M:%S')
    
    return jsonify({
        'success': True,
        'stats': stats
    })

@app.route('/api/book/<int:book_id>/duplicate', methods=['POST'])
def duplicate_book(book_id):
    """Duplicate a book"""
    try:
        original = Book.query.get_or_404(book_id)
        
        new_book = Book(
            title=f"{original.title} (Cópia)",
            theme=original.theme,
            style=original.style,
            full_text=original.full_text,
            language=original.language,
            word_count=original.word_count,
            parent_id=original.id
        )
        new_book.set_chapters(original.get_chapters())
        new_book.set_tags(original.get_tags())
        
        db.session.add(new_book)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'book_id': new_book.id,
            'title': new_book.title,
            'message': 'Livro duplicado com sucesso!'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/book/<int:book_id>/share', methods=['POST'])
def generate_share_link(book_id):
    """Generate a share token for a book"""
    try:
        book = Book.query.get_or_404(book_id)
        
        if not book.share_token:
            book.generate_share_token()
            db.session.commit()
        
        share_url = f"/shared/{book.share_token}"
        
        return jsonify({
            'success': True,
            'share_token': book.share_token,
            'share_url': share_url,
            'message': 'Link de partilha gerado!'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/book/<int:book_id>/unshare', methods=['POST'])
def remove_share_link(book_id):
    """Remove share token from a book"""
    try:
        book = Book.query.get_or_404(book_id)
        book.share_token = None
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Link de partilha removido!'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/shared/<share_token>')
def view_shared_book(share_token):
    """View a shared book (public access)"""
    book = Book.query.filter_by(share_token=share_token).first_or_404()
    return render_template('view_book.html', book=book, is_shared=True)

@app.route('/api/stats/global')
def get_global_stats():
    """Get global statistics"""
    books = Book.query.all()
    
    total_books = len(books)
    total_words = sum(b.word_count or b.calculate_word_count() for b in books)
    total_chapters = sum(len(b.get_chapters()) for b in books)
    
    # Count by style
    styles = {}
    for book in books:
        styles[book.style] = styles.get(book.style, 0) + 1
    
    # Count by language
    languages = {}
    for book in books:
        lang = book.language or 'pt-pt'
        languages[lang] = languages.get(lang, 0) + 1
    
    return jsonify({
        'success': True,
        'stats': {
            'total_books': total_books,
            'total_words': total_words,
            'total_chapters': total_chapters,
            'total_pages': round(total_words / 250) if total_words else 0,
            'avg_words_per_book': round(total_words / total_books) if total_books else 0,
            'by_style': styles,
            'by_language': languages,
            'favorites_count': sum(1 for b in books if b.is_favorite)
        }
    })

# ==================== DASHBOARD ====================

@app.route('/dashboard')
def dashboard_page():
    """Dashboard with global statistics"""
    return render_template('dashboard.html')

@app.route('/read/<int:book_id>')
def read_book_page(book_id):
    """Clean reading mode for a book"""
    book = Book.query.get_or_404(book_id)
    return render_template('read_book.html', book=book)

@app.route('/api/dashboard')
def get_dashboard_data():
    """Get comprehensive dashboard data"""
    from collections import defaultdict
    from datetime import timedelta
    
    books = Book.query.order_by(Book.created_at.desc()).all()
    
    total_books = len(books)
    total_words = sum(b.word_count or b.calculate_word_count() for b in books)
    total_chapters = sum(len(b.get_chapters()) for b in books)
    total_reading_time = sum(b.get_reading_time() for b in books)
    
    # Count by style
    styles = defaultdict(int)
    for book in books:
        styles[book.style] += 1
    
    # Count by language
    languages = defaultdict(int)
    for book in books:
        lang = book.language or 'pt-pt'
        languages[lang] += 1
    
    # Activity by day (last 30 days)
    activity = defaultdict(int)
    today = datetime.utcnow().date()
    for i in range(30):
        day = today - timedelta(days=i)
        activity[day.strftime('%d/%m')] = 0
    
    for book in books:
        if book.created_at:
            day_key = book.created_at.strftime('%d/%m')
            if day_key in activity:
                activity[day_key] += 1
    
    # Reverse to show oldest first
    activity = dict(reversed(list(activity.items())))
    
    # All tags with counts
    all_tags = defaultdict(int)
    for book in books:
        for tag in book.get_tags():
            all_tags[tag] += 1
    
    top_tags = sorted([{'name': k, 'count': v} for k, v in all_tags.items()], 
                      key=lambda x: x['count'], reverse=True)
    
    # Count series (books with parent_id or that are parents)
    series_ids = set()
    for book in books:
        if book.parent_id:
            series_ids.add(book.parent_id)
    
    # Recent books for display
    recent_books = [b.to_dict() for b in books[:10]]
    
    return jsonify({
        'success': True,
        'stats': {
            'total_books': total_books,
            'total_words': total_words,
            'total_chapters': total_chapters,
            'total_pages': round(total_words / 250) if total_words else 0,
            'avg_words_per_book': round(total_words / total_books) if total_books else 0,
            'total_reading_time': total_reading_time,
            'favorites_count': sum(1 for b in books if b.is_favorite),
            'total_series': len(series_ids),
            'unique_tags': len(all_tags),
            'by_style': dict(styles),
            'by_language': dict(languages),
            'activity_by_day': activity
        },
        'recent_books': recent_books,
        'top_tags': top_tags
    })

# ==================== EDITING FEATURES ====================

# Style Templates Configuration
STYLE_TEMPLATES = {
    'standard': {
        'name': 'Padrão',
        'description': 'Formato clássico para romances e ficção',
        'chapter_prompt': 'Escreve de forma narrativa e envolvente.',
        'font': 'serif',
        'cover_style': 'classic'
    },
    'technical': {
        'name': 'Técnico',
        'description': 'Para manuais, guias e documentação',
        'chapter_prompt': 'Escreve de forma clara, objetiva e didática. Usa listas e exemplos.',
        'font': 'sans-serif',
        'cover_style': 'minimal'
    },
    'children': {
        'name': 'Infantil',
        'description': 'Para livros infantis com linguagem simples',
        'chapter_prompt': 'Escreve com linguagem simples e divertida para crianças. Usa frases curtas.',
        'font': 'comic',
        'cover_style': 'colorful'
    },
    'academic': {
        'name': 'Académico',
        'description': 'Para trabalhos académicos e científicos',
        'chapter_prompt': 'Escreve de forma formal e académica. Cita fontes quando relevante.',
        'font': 'serif',
        'cover_style': 'formal'
    },
    'poetry': {
        'name': 'Poesia',
        'description': 'Para poesia e prosa poética',
        'chapter_prompt': 'Escreve com linguagem poética, rítmica e evocativa.',
        'font': 'cursive',
        'cover_style': 'artistic'
    },
    'screenplay': {
        'name': 'Roteiro',
        'description': 'Para roteiros de cinema ou teatro',
        'chapter_prompt': 'Escreve em formato de roteiro com diálogos e indicações de cena.',
        'font': 'monospace',
        'cover_style': 'dramatic'
    }
}

@app.route('/api/templates')
def get_style_templates():
    """Get available style templates"""
    return jsonify({
        'success': True,
        'templates': STYLE_TEMPLATES
    })

@app.route('/edit/<int:book_id>')
def edit_book_page(book_id):
    """Render the book editing page"""
    book = Book.query.get_or_404(book_id)
    return render_template('edit_book.html', book=book, templates=STYLE_TEMPLATES)

@app.route('/api/book/<int:book_id>/chapters')
def get_book_chapters(book_id):
    """Get individual chapter contents for editing"""
    book = Book.query.get_or_404(book_id)
    chapters = book.get_chapters_content()
    return jsonify({
        'success': True,
        'chapters': chapters,
        'book_id': book_id
    })

@app.route('/api/book/<int:book_id>/chapter/<int:chapter_index>', methods=['PUT'])
def update_chapter(book_id, chapter_index):
    """Update a specific chapter's content"""
    try:
        book = Book.query.get_or_404(book_id)
        data = request.get_json()
        
        new_content = data.get('content')
        new_title = data.get('title')
        
        if new_content:
            book.update_chapter(chapter_index, new_content)
        
        if new_title:
            book.update_chapter_title(chapter_index, new_title)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Capítulo atualizado!',
            'word_count': book.word_count
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/book/<int:book_id>/chapter/<int:chapter_index>/regenerate', methods=['POST'])
def regenerate_chapter(book_id, chapter_index):
    """Regenerate a specific chapter using AI"""
    try:
        book = Book.query.get_or_404(book_id)
        data = request.get_json() or {}
        
        chapters = book.get_chapters_content()
        if chapter_index < 0 or chapter_index >= len(chapters):
            return jsonify({'success': False, 'error': 'Índice de capítulo inválido'}), 400
        
        chapter = chapters[chapter_index]
        custom_instructions = data.get('instructions', '')
        
        # Get style template
        template = STYLE_TEMPLATES.get(book.style_template or 'standard', STYLE_TEMPLATES['standard'])
        
        # Build context from previous chapter
        previous_context = ""
        if chapter_index > 0:
            prev_chapter = chapters[chapter_index - 1]
            # Get last 500 chars for context
            previous_context = f"\n\nContexto do capítulo anterior ({prev_chapter['title']}):\n{prev_chapter['content'][-500:]}"
        
        prompt = f"""Reescreve o seguinte capítulo de um livro.

Título do Livro: {book.title}
Tema: {book.theme}
Estilo: {book.style}
Idioma: {book.language or 'pt-pt'}

Capítulo a reescrever: {chapter['title']}
{previous_context}

Instruções de estilo: {template['chapter_prompt']}
{f"Instruções adicionais: {custom_instructions}" if custom_instructions else ""}

Mantém o mesmo título do capítulo mas reescreve o conteúdo de forma melhorada.
O capítulo deve ter aproximadamente o mesmo tamanho que o original ({len(chapter['content'])} caracteres).

Conteúdo original para referência:
{chapter['content'][:1000]}...

Escreve APENAS o conteúdo do capítulo, começando com o título."""

        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        new_content = response.text.strip()
        
        # Update the chapter
        book.update_chapter(chapter_index, new_content)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Capítulo regenerado com sucesso!',
            'chapter': {
                'title': chapter['title'],
                'content': new_content
            },
            'word_count': book.word_count
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/book/<int:book_id>/title', methods=['PUT'])
def update_book_title(book_id):
    """Update book title"""
    try:
        book = Book.query.get_or_404(book_id)
        data = request.get_json()
        
        new_title = data.get('title', '').strip()
        if not new_title:
            return jsonify({'success': False, 'error': 'Título não pode estar vazio'}), 400
        
        book.title = new_title
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Título atualizado!',
            'title': new_title
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/book/<int:book_id>/cover', methods=['POST'])
def upload_cover(book_id):
    """Upload a cover image for a book"""
    try:
        book = Book.query.get_or_404(book_id)
        
        if 'cover' in request.files:
            file = request.files['cover']
            if file and file.filename:
                # Read and encode as base64
                import base64
                image_data = file.read()
                encoded = base64.b64encode(image_data).decode('utf-8')
                mime_type = file.content_type or 'image/jpeg'
                book.cover_image = f"data:{mime_type};base64,{encoded}"
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Capa carregada!',
                    'cover_url': book.cover_image[:100] + '...'
                })
        
        # Check for URL
        data = request.get_json() if request.is_json else {}
        if 'cover_url' in data:
            book.cover_image = data['cover_url']
            db.session.commit()
            return jsonify({
                'success': True,
                'message': 'Capa atualizada!',
                'cover_url': book.cover_image
            })
        
        return jsonify({'success': False, 'error': 'Nenhuma imagem fornecida'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/book/<int:book_id>/cover/generate', methods=['POST'])
def generate_cover(book_id):
    """Generate a cover image using AI (placeholder - returns SVG)"""
    try:
        book = Book.query.get_or_404(book_id)
        template = STYLE_TEMPLATES.get(book.style_template or 'standard', STYLE_TEMPLATES['standard'])
        
        # Generate a simple SVG cover based on style
        colors = {
            'classic': ('#1a1a2e', '#eee'),
            'minimal': ('#fff', '#333'),
            'colorful': ('#ff6b6b', '#fff'),
            'formal': ('#0a192f', '#ccd6f6'),
            'artistic': ('#2d1b69', '#f8f8f8'),
            'dramatic': ('#000', '#c9a227')
        }
        
        bg_color, text_color = colors.get(template['cover_style'], colors['classic'])
        
        # Create SVG cover
        svg_cover = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 600">
            <rect width="400" height="600" fill="{bg_color}"/>
            <rect x="20" y="20" width="360" height="560" fill="none" stroke="{text_color}" stroke-width="2"/>
            <text x="200" y="250" text-anchor="middle" fill="{text_color}" font-size="24" font-family="Georgia">{book.title[:30]}</text>
            <text x="200" y="290" text-anchor="middle" fill="{text_color}" font-size="14" font-family="Georgia" opacity="0.7">{book.style}</text>
            <text x="200" y="500" text-anchor="middle" fill="{text_color}" font-size="12" font-family="Arial">BookCreatorAI</text>
        </svg>'''
        
        import base64
        encoded = base64.b64encode(svg_cover.encode()).decode()
        book.cover_image = f"data:image/svg+xml;base64,{encoded}"
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Capa gerada!',
            'cover_image': book.cover_image
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/book/<int:book_id>/cover', methods=['DELETE'])
def remove_cover(book_id):
    """Remove cover image from a book"""
    try:
        book = Book.query.get_or_404(book_id)
        book.cover_image = None
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Capa removida!'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/book/<int:book_id>/template', methods=['PUT'])
def update_book_template(book_id):
    """Update book style template"""
    try:
        book = Book.query.get_or_404(book_id)
        data = request.get_json()
        
        template_id = data.get('template')
        if template_id not in STYLE_TEMPLATES:
            return jsonify({'success': False, 'error': 'Template inválido'}), 400
        
        book.style_template = template_id
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Template atualizado!',
            'template': STYLE_TEMPLATES[template_id]
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== ADVANCED AI FEATURES ====================

@app.route('/api/ai/suggest-themes', methods=['POST'])
def suggest_themes():
    """Generate theme suggestions based on style and preferences"""
    response_text = ""
    try:
        data = request.get_json() or {}
        style = data.get('style', 'romance')
        preferences = data.get('preferences', '')
        count = min(data.get('count', 5), 10)
        
        prompt = f"""Sugere {count} temas criativos e originais para um livro do género "{style}".
{f"Preferências do utilizador: {preferences}" if preferences else ""}

Para cada tema, fornece:
1. Um título sugestivo
2. Uma breve descrição do tema (2-3 frases)
3. O que torna este tema interessante

Responde APENAS em formato JSON válido, como array:
[
  {{"title": "Título do Tema", "description": "Descrição...", "appeal": "O que o torna interessante..."}},
  ...
]

Sê criativo e original. Evita clichés. Os temas devem ser adequados para um livro completo."""

        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        response_text = response.text
        
        # Parse JSON from response
        text = response_text.strip()
        # Remove markdown code blocks if present
        if text.startswith('```'):
            text = text.split('```')[1]
            if text.startswith('json'):
                text = text[4:]
        text = text.strip()
        
        themes = json.loads(text)
        
        return jsonify({
            'success': True,
            'themes': themes
        })
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}")
        print(f"Response text: {response_text[:500]}")
        return jsonify({
            'success': True,
            'themes': [{'title': 'Tema sugerido', 'description': response_text[:200] if response_text else 'Erro ao processar resposta', 'appeal': ''}]
        })
    except Exception as e:
        print(f"Error in suggest_themes: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai/generate-plots', methods=['POST'])
def generate_plot_variations():
    """Generate multiple plot outline variations"""
    try:
        data = request.get_json()
        theme = data.get('theme', '')
        style = data.get('style', 'romance')
        characters = data.get('characters', [])
        world_setting = data.get('world_setting', {})
        count = min(data.get('count', 3), 5)
        
        # Build context
        char_context = ""
        if characters:
            char_context = "\n\nPersonagens definidos:\n"
            for c in characters:
                char_context += f"- {c.get('name', 'Sem nome')}: {c.get('description', '')}\n"
        
        world_context = ""
        if world_setting:
            world_context = "\n\nCenário:\n"
            for key, val in world_setting.items():
                if val:
                    world_context += f"- {key}: {val}\n"
        
        prompt = f"""Gera {count} variações diferentes de enredo para um livro.

Tema: {theme}
Género: {style}
{char_context}
{world_context}

Para cada variação, fornece:
1. Um título para o enredo
2. Uma sinopse (3-4 frases)
3. O tom principal (ex: sombrio, esperançoso, tenso)
4. Os principais pontos de conflito
5. Lista de 5 capítulos sugeridos

Responde APENAS em formato JSON válido:
[
  {{
    "title": "Título do Enredo",
    "synopsis": "Sinopse...",
    "tone": "Tom principal",
    "conflicts": ["conflito1", "conflito2"],
    "chapters": ["Cap 1: ...", "Cap 2: ...", "Cap 3: ...", "Cap 4: ...", "Cap 5: ..."]
  }},
  ...
]

Cada variação deve ser significativamente diferente das outras."""

        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        
        text = response.text.strip()
        if text.startswith('```'):
            text = text.split('```')[1]
            if text.startswith('json'):
                text = text[4:]
        text = text.strip()
        
        plots = json.loads(text)
        
        return jsonify({
            'success': True,
            'plots': plots
        })
    except json.JSONDecodeError:
        return jsonify({
            'success': True,
            'plots': [{'title': 'Erro', 'synopsis': response.text[:300], 'tone': '', 'conflicts': [], 'chapters': []}]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai/analyze-text', methods=['POST'])
def analyze_text():
    """Analyze text for quality, coherence, and tone"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        book_id = data.get('book_id')
        
        if not text and book_id:
            book = Book.query.get_or_404(book_id)
            text = book.full_text
        
        if not text:
            return jsonify({'success': False, 'error': 'Nenhum texto fornecido'}), 400
        
        # Limit text for analysis
        sample_text = text[:8000] if len(text) > 8000 else text
        
        prompt = f"""Analisa o seguinte texto de um livro e fornece uma avaliação detalhada.

TEXTO:
{sample_text}

Analisa os seguintes aspectos e dá uma pontuação de 1 a 10 para cada:

1. **Qualidade da Escrita**: Gramática, vocabulário, fluidez
2. **Coerência**: Lógica narrativa, consistência
3. **Envolvimento**: Capacidade de prender o leitor
4. **Originalidade**: Criatividade e frescura das ideias
5. **Diálogos**: Naturalidade e qualidade (se aplicável)
6. **Descrições**: Riqueza e equilíbrio das descrições
7. **Ritmo**: Pacing da narrativa
8. **Tom**: Consistência do tom ao longo do texto

Também identifica:
- Pontos fortes (lista de 3-5)
- Áreas a melhorar (lista de 3-5)
- Tom geral detectado (ex: "melancólico", "esperançoso", etc.)
- Género/estilo detectado

Responde APENAS em formato JSON válido:
{{
  "scores": {{
    "writing_quality": 8,
    "coherence": 7,
    "engagement": 8,
    "originality": 7,
    "dialogues": 6,
    "descriptions": 8,
    "pacing": 7,
    "tone_consistency": 8
  }},
  "overall_score": 7.5,
  "strengths": ["ponto1", "ponto2", "ponto3"],
  "improvements": ["melhoria1", "melhoria2", "melhoria3"],
  "detected_tone": "tom detectado",
  "detected_genre": "género detectado",
  "summary": "Resumo geral da análise em 2-3 frases"
}}"""

        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        
        text_response = response.text.strip()
        if text_response.startswith('```'):
            text_response = text_response.split('```')[1]
            if text_response.startswith('json'):
                text_response = text_response[4:]
        text_response = text_response.strip()
        
        analysis = json.loads(text_response)
        
        # Save analysis if book_id provided
        if book_id:
            book = Book.query.get(book_id)
            if book:
                book.set_ai_analysis(analysis)
                db.session.commit()
        
        return jsonify({
            'success': True,
            'analysis': analysis
        })
    except json.JSONDecodeError:
        return jsonify({
            'success': False,
            'error': 'Erro ao processar análise',
            'raw': response.text[:500] if 'response' in dir() else ''
        }), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai/generate-characters', methods=['POST'])
def generate_characters():
    """Generate character suggestions based on theme and style"""
    try:
        data = request.get_json()
        theme = data.get('theme', '')
        style = data.get('style', 'romance')
        count = min(data.get('count', 4), 8)
        existing = data.get('existing', [])
        
        existing_context = ""
        if existing:
            existing_context = "\n\nPersonagens já existentes (evitar repetição):\n"
            for c in existing:
                existing_context += f"- {c.get('name', '')}\n"
        
        prompt = f"""Cria {count} personagens interessantes para um livro.

Tema: {theme}
Género: {style}
{existing_context}

Para cada personagem, fornece:
1. Nome completo
2. Papel na história (protagonista, antagonista, mentor, aliado, etc.)
3. Descrição física e personalidade (2-3 frases)
4. Traços distintivos (3-4 características)
5. Arco de personagem sugerido

Responde APENAS em formato JSON válido:
[
  {{
    "name": "Nome Completo",
    "role": "protagonista",
    "description": "Descrição...",
    "traits": "traço1, traço2, traço3",
    "arc": "Descrição do arco de personagem"
  }},
  ...
]

Cria personagens diversos, complexos e memoráveis."""

        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        
        text = response.text.strip()
        if text.startswith('```'):
            text = text.split('```')[1]
            if text.startswith('json'):
                text = text[4:]
        text = text.strip()
        
        characters = json.loads(text)
        
        return jsonify({
            'success': True,
            'characters': characters
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai/generate-world', methods=['POST'])
def generate_world():
    """Generate worldbuilding suggestions"""
    try:
        data = request.get_json()
        theme = data.get('theme', '')
        style = data.get('style', 'romance')
        
        prompt = f"""Cria um cenário/universo detalhado para um livro.

Tema: {theme}
Género: {style}

Desenvolve os seguintes aspectos do mundo:

1. Época/Período temporal
2. Localização principal
3. Atmosfera geral
4. Regras especiais do mundo (se aplicável)
5. Nível tecnológico
6. Estrutura social
7. Detalhes únicos que tornam este mundo interessante

Responde APENAS em formato JSON válido:
{{
  "time_period": "Descrição da época",
  "location": "Descrição do local",
  "atmosphere": "Descrição da atmosfera",
  "rules": "Regras especiais do mundo",
  "technology": "Nível e tipo de tecnologia",
  "society": "Estrutura social",
  "custom": "Detalhes únicos e interessantes"
}}

Sê criativo e consistente com o género."""

        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        
        text = response.text.strip()
        if text.startswith('```'):
            text = text.split('```')[1]
            if text.startswith('json'):
                text = text[4:]
        text = text.strip()
        
        world = json.loads(text)
        
        return jsonify({
            'success': True,
            'world': world
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/book/<int:book_id>/characters', methods=['GET', 'POST', 'PUT'])
def manage_book_characters(book_id):
    """Get, add, or update characters for a book"""
    book = Book.query.get_or_404(book_id)
    
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'characters': book.get_characters()
        })
    
    try:
        data = request.get_json()
        
        if request.method == 'POST':
            # Add a character
            character = data.get('character', {})
            book.add_character(character)
        else:  # PUT - replace all
            characters = data.get('characters', [])
            book.set_characters(characters)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'characters': book.get_characters(),
            'message': 'Personagens atualizados!'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/book/<int:book_id>/world', methods=['GET', 'PUT'])
def manage_book_world(book_id):
    """Get or update worldbuilding for a book"""
    book = Book.query.get_or_404(book_id)
    
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'world': book.get_world_setting()
        })
    
    try:
        data = request.get_json()
        world = data.get('world', {})
        book.set_world_setting(world)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'world': book.get_world_setting(),
            'message': 'Cenário atualizado!'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/book/<int:book_id>/analysis')
def get_book_analysis(book_id):
    """Get AI analysis for a book"""
    book = Book.query.get_or_404(book_id)
    analysis = book.get_ai_analysis()
    
    if not analysis:
        return jsonify({
            'success': True,
            'analysis': None,
            'message': 'Nenhuma análise disponível. Use /api/ai/analyze-text para analisar.'
        })
    
    return jsonify({
        'success': True,
        'analysis': analysis
    })

# ==================== SERIES/COLLECTIONS ====================

@app.route('/api/series', methods=['GET', 'POST'])
def manage_series():
    """List all series or create a new one"""
    if request.method == 'GET':
        series_list = Series.query.order_by(Series.created_at.desc()).all()
        return jsonify({
            'success': True,
            'series': [s.to_dict() for s in series_list]
        })
    
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        
        if not name:
            return jsonify({'success': False, 'error': 'Nome obrigatório'}), 400
        
        new_series = Series(
            name=name,
            description=data.get('description', ''),
            cover_image=data.get('cover_image')
        )
        db.session.add(new_series)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'series': new_series.to_dict(),
            'message': 'Série criada!'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/series/<int:series_id>', methods=['GET', 'PUT', 'DELETE'])
def manage_single_series(series_id):
    """Get, update or delete a series"""
    series = Series.query.get_or_404(series_id)
    
    if request.method == 'GET':
        books = Book.query.filter_by(series_id=series_id).order_by(Book.series_order).all()
        return jsonify({
            'success': True,
            'series': series.to_dict(),
            'books': [b.to_dict() for b in books]
        })
    
    if request.method == 'DELETE':
        try:
            # Remove series_id from all books
            for book in series.books:
                book.series_id = None
            db.session.delete(series)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Série eliminada!'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # PUT
    try:
        data = request.get_json()
        if 'name' in data:
            series.name = data['name']
        if 'description' in data:
            series.description = data['description']
        if 'cover_image' in data:
            series.cover_image = data['cover_image']
        
        db.session.commit()
        return jsonify({
            'success': True,
            'series': series.to_dict(),
            'message': 'Série atualizada!'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/book/<int:book_id>/series', methods=['PUT'])
def set_book_series(book_id):
    """Add or remove a book from a series"""
    try:
        book = Book.query.get_or_404(book_id)
        data = request.get_json()
        
        series_id = data.get('series_id')
        if series_id:
            series = Series.query.get_or_404(series_id)
            book.series_id = series_id
            book.series_order = data.get('order', series.books.count())
        else:
            book.series_id = None
            book.series_order = 0
        
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Livro atualizado!',
            'series_id': book.series_id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== SUMMARIES/SYNOPSIS ====================

@app.route('/api/book/<int:book_id>/synopsis', methods=['GET', 'POST'])
def manage_synopsis(book_id):
    """Get or generate book synopsis"""
    book = Book.query.get_or_404(book_id)
    
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'synopsis': book.synopsis
        })
    
    try:
        # Generate synopsis with AI
        prompt = f"""Cria uma sinopse envolvente para este livro.

Título: {book.title}
Tema: {book.theme}
Estilo: {book.style}

Primeiras 2000 palavras do livro:
{book.full_text[:8000]}

Escreve uma sinopse de 2-3 parágrafos que:
1. Apresente o contexto/cenário
2. Introduza os personagens principais
3. Crie intriga sem revelar o final

Responde APENAS com a sinopse, sem títulos ou explicações."""

        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        synopsis = response.text.strip()
        
        book.synopsis = synopsis
        db.session.commit()
        
        return jsonify({
            'success': True,
            'synopsis': synopsis,
            'message': 'Sinopse gerada!'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/book/<int:book_id>/chapter-summaries', methods=['POST'])
def generate_chapter_summaries(book_id):
    """Generate summaries for each chapter"""
    try:
        book = Book.query.get_or_404(book_id)
        chapters = book.get_chapters_content()
        
        summaries = []
        model = genai.GenerativeModel("gemini-2.0-flash")
        
        for i, chapter in enumerate(chapters):
            prompt = f"""Resume este capítulo em 2-3 frases concisas.

Capítulo: {chapter.get('title', f'Capítulo {i+1}')}
Conteúdo: {chapter.get('content', '')[:3000]}

Responde APENAS com o resumo, sem títulos."""

            response = model.generate_content(prompt)
            summaries.append({
                'title': chapter.get('title', f'Capítulo {i+1}'),
                'summary': response.text.strip()
            })
        
        return jsonify({
            'success': True,
            'summaries': summaries
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== CHAT WITH BOOK ====================

@app.route('/api/book/<int:book_id>/chat', methods=['POST'])
def chat_with_book(book_id):
    """Chat with a book - ask questions about its content"""
    try:
        book = Book.query.get_or_404(book_id)
        data = request.get_json()
        question = data.get('question', '').strip()
        chat_history = data.get('history', [])
        
        if not question:
            return jsonify({'success': False, 'error': 'Pergunta obrigatória'}), 400
        
        # Build context from chat history
        history_text = ""
        if chat_history:
            history_text = "\n\nHistórico da conversa:\n"
            for msg in chat_history[-6:]:  # Last 6 messages for context
                role = "Utilizador" if msg.get('role') == 'user' else "Assistente"
                history_text += f"{role}: {msg.get('content', '')}\n"
        
        # Get book content (limit to avoid token limits)
        book_content = book.full_text[:30000]  # ~7500 words
        chapters = book.get_chapters()
        characters = book.get_characters()
        world = book.get_world_setting()
        
        # Build context about the book
        context_parts = [f"Título: {book.title}", f"Tema: {book.theme}", f"Estilo: {book.style}"]
        
        if chapters:
            context_parts.append(f"Capítulos: {', '.join(chapters[:10])}")
        
        if characters:
            char_names = [c.get('name', '') for c in characters[:5]]
            context_parts.append(f"Personagens principais: {', '.join(char_names)}")
        
        if world:
            if world.get('setting'):
                context_parts.append(f"Cenário: {world.get('setting')}")
            if world.get('time_period'):
                context_parts.append(f"Época: {world.get('time_period')}")
        
        book_context = "\n".join(context_parts)
        
        prompt = f"""És um assistente especializado neste livro. Responde às perguntas do utilizador APENAS com base no conteúdo do livro fornecido.

=== INFORMAÇÕES DO LIVRO ===
{book_context}

=== CONTEÚDO DO LIVRO ===
{book_content}

=== INSTRUÇÕES ===
1. Responde APENAS com base no conteúdo do livro acima
2. Se a informação não estiver no livro, diz "Essa informação não está presente no livro"
3. Sê conciso mas informativo
4. Podes fazer citações relevantes do texto
5. Responde sempre em português
{history_text}
=== PERGUNTA DO UTILIZADOR ===
{question}

=== RESPOSTA ==="""

        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        answer = response.text.strip()
        
        return jsonify({
            'success': True,
            'answer': answer,
            'question': question
        })
        
    except Exception as e:
        print(f"Chat error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/chat/<int:book_id>')
def chat_page(book_id):
    """Chat page for a book"""
    book = Book.query.get_or_404(book_id)
    return render_template('chat_book.html', book=book)

# ==================== BOOK EXPLORER ====================

@app.route('/explorer')
def book_explorer_page():
    """Book Explorer page - analyze any existing book"""
    return render_template('book_explorer.html')

@app.route('/api/explore-book', methods=['POST'])
def explore_book():
    """Explore and analyze any existing book using AI"""
    try:
        data = request.get_json()
        title = data.get('title', '').strip()
        author = data.get('author', '').strip()
        aspect = data.get('aspect', 'info')
        question = data.get('question', '')
        history = data.get('history', [])
        
        if not title:
            return jsonify({'success': False, 'error': 'Título obrigatório'}), 400
        
        book_ref = f'"{title}"' + (f' de {author}' if author else '')
        
        # Define prompts for each aspect
        aspect_prompts = {
            'info': f"""Fornece informações básicas sobre o livro {book_ref}:
- Género literário
- Ano de publicação
- País de origem
- Breve contexto

Responde de forma concisa em português.""",

            'summary': f"""Faz um resumo completo e detalhado do livro {book_ref}.
Inclui:
- Contexto inicial
- Desenvolvimento da história
- Principais acontecimentos
- Conclusão (com spoilers)

Escreve em português, de forma clara e organizada.""",

            'characters': f"""Analisa os personagens principais do livro {book_ref}.
Para cada personagem inclui:
- Nome e papel na história
- Características físicas e psicológicas
- Motivações e objetivos
- Arco de desenvolvimento
- Relações com outros personagens

Organiza por personagem. Escreve em português.""",

            'themes': f"""Analisa os temas e mensagens do livro {book_ref}.
Inclui:
- Temas principais
- Temas secundários
- Mensagens e lições
- Críticas sociais (se aplicável)
- Relevância atual

Escreve em português de forma profunda mas acessível.""",

            'world': f"""Descreve o mundo e cenário do livro {book_ref}.
Inclui:
- Localização geográfica
- Período temporal/época
- Contexto histórico e social
- Atmosfera e ambiente
- Regras do mundo (se fantasia/ficção científica)

Escreve em português com detalhes imersivos.""",

            'style': f"""Analisa o estilo literário do livro {book_ref}.
Inclui:
- Tipo de narrador
- Estrutura narrativa
- Linguagem e tom
- Técnicas literárias utilizadas
- Influências do autor
- Comparação com outras obras

Escreve em português de forma técnica mas acessível.""",

            'quotes': f"""Lista as citações mais famosas e marcantes do livro {book_ref}.
Para cada citação:
- A frase exata (ou aproximada)
- Contexto em que aparece
- Significado e importância

Inclui pelo menos 5-8 citações memoráveis. Escreve em português.""",

            'discussion': f"""Cria questões de discussão para um clube do livro sobre {book_ref}.
Inclui:
- Perguntas sobre personagens
- Perguntas sobre temas
- Perguntas sobre decisões morais
- Perguntas de reflexão pessoal
- Perguntas de comparação com a realidade

Cria 10-12 perguntas provocadoras. Escreve em português.""",

            'similar': f"""Recomenda livros similares a {book_ref}.
Para cada recomendação inclui:
- Título e autor
- Porquê é similar
- Breve sinopse

Recomenda 6-8 livros. Organiza por relevância. Escreve em português.""",

            'trivia': f"""Partilha curiosidades interessantes sobre o livro {book_ref}.
Inclui:
- Factos sobre a escrita/publicação
- Curiosidades sobre o autor
- Impacto cultural
- Controvérsias (se existirem)
- Records e prémios
- Factos pouco conhecidos

Lista 8-10 curiosidades. Escreve em português.""",

            'timeline': f"""Cria uma cronologia dos eventos do livro {book_ref}.
Lista os principais acontecimentos em ordem:
- Eventos do passado (backstory)
- Eventos principais da narrativa
- Consequências e epílogo

Organiza de forma clara com datas/momentos. Escreve em português.""",

            'symbolism': f"""Analisa o simbolismo no livro {book_ref}.
Inclui:
- Símbolos principais e seus significados
- Metáforas recorrentes
- Elementos alegóricos
- Cores, objetos ou lugares simbólicos
- Interpretações

Explica cada símbolo em detalhe. Escreve em português.""",

            'adaptation': f"""Lista as adaptações do livro {book_ref}.
Inclui:
- Filmes
- Séries de TV
- Peças de teatro
- Audiobooks notáveis
- Outras adaptações

Para cada uma: ano, realizador/produtor, elenco principal, recepção.
Escreve em português."""
        }
        
        if aspect == 'chat':
            # Chat mode - answer specific questions
            history_text = ""
            if history:
                history_text = "\n\nHistórico:\n"
                for msg in history[-4:]:
                    role = "Utilizador" if msg.get('role') == 'user' else "Assistente"
                    history_text += f"{role}: {msg.get('content', '')}\n"
            
            prompt = f"""És um especialista no livro {book_ref}. Responde à pergunta do utilizador com base no teu conhecimento sobre esta obra.

Sê informativo, preciso e responde sempre em português.
{history_text}
Pergunta: {question}

Resposta:"""

        elif aspect == 'interview':
            # Character interview mode
            character = data.get('character', '')
            history_text = ""
            if history:
                history_text = "\n\nConversa anterior:\n"
                for msg in history[-6:]:
                    role = "Entrevistador" if msg.get('role') == 'user' else character
                    history_text += f"{role}: {msg.get('content', '')}\n"
            
            prompt = f"""És o personagem "{character}" do livro {book_ref}.
Responde às perguntas COMO SE FOSSES esse personagem.

INSTRUÇÕES:
1. Responde SEMPRE na primeira pessoa, como {character}
2. Mantém a personalidade e forma de falar do personagem
3. Usa conhecimento e memórias que o personagem teria
4. Se perguntarem algo que o personagem não saberia, diz que não sabes
5. Sê expressivo e dramático quando apropriado
6. Responde em português
{history_text}
Pergunta do entrevistador: {question}

Resposta de {character}:"""

        elif aspect == 'quiz':
            # Generate quiz questions
            difficulty = data.get('difficulty', 'medium')
            difficulty_desc = {
                'easy': 'Perguntas simples sobre factos básicos.',
                'medium': 'Perguntas que requerem boa compreensão.',
                'hard': 'Perguntas difíceis sobre detalhes e análise.'
            }
            
            prompt = f"""Cria um quiz de 10 perguntas sobre o livro {book_ref}.
Dificuldade: {difficulty} - {difficulty_desc.get(difficulty, '')}

Responde APENAS com JSON válido neste formato:
[
  {{"question": "Pergunta?", "options": ["A", "B", "C", "D"], "correct": 0, "explanation": "Explicação"}}
]

O campo "correct" é o índice (0-3) da opção correta.
Cria perguntas variadas sobre enredo, personagens, temas e detalhes.
Responde APENAS com o JSON, sem texto adicional."""

            model = genai.GenerativeModel("gemini-2.0-flash")
            response = model.generate_content(prompt)
            text = response.text.strip()
            
            if text.startswith('```'):
                text = text.split('\n', 1)[1].rsplit('```', 1)[0]
            
            import json
            questions = json.loads(text)
            return jsonify({'success': True, 'questions': questions})

        elif aspect == 'continue':
            # Continue the story
            cont_type = data.get('continuation_type', 'chapter')
            direction = data.get('direction', '')
            
            type_instructions = {
                'chapter': 'Escreve o PRÓXIMO CAPÍTULO da história (~1500 palavras)',
                'epilogue': 'Escreve um EPÍLOGO mostrando o que aconteceu depois (~800 palavras)',
                'sequel': 'Escreve o INÍCIO DE UMA SEQUELA com novo conflito (~1500 palavras)'
            }
            
            direction_text = f"\nDireção sugerida: {direction}" if direction else ""
            
            prompt = f"""És um autor talentoso. Continua a história do livro {book_ref}.

TAREFA: {type_instructions.get(cont_type, type_instructions['chapter'])}
{direction_text}

INSTRUÇÕES:
1. Mantém o estilo e tom do autor original
2. Desenvolve os personagens de forma consistente
3. Cria tensão e interesse
4. Escreve em português
5. Inclui título da secção

CONTINUAÇÃO:"""

        elif aspect == 'alternate':
            # Alternate ending
            scenario = data.get('scenario', '')
            
            prompt = f"""Reimagina o final do livro {book_ref} com base neste cenário alternativo:

CENÁRIO "E SE...": {scenario}

Escreve um final alternativo (~1000 palavras) que explore esta possibilidade.

INSTRUÇÕES:
1. Mantém os personagens fiéis às suas personalidades
2. Desenvolve as consequências lógicas do cenário
3. Cria um final satisfatório e coerente
4. Escreve em português
5. Sê criativo mas respeita o universo do livro

FINAL ALTERNATIVO:"""

        elif aspect == 'playlist':
            # Generate playlist suggestions
            mood = data.get('mood', 'geral')
            
            prompt = f"""Cria uma playlist de músicas que combinam perfeitamente com o livro {book_ref}.

INSTRUÇÕES:
1. Sugere 12-15 músicas reais (que existem de verdade)
2. Inclui artista e nome da música
3. Explica brevemente porque cada música combina
4. Varia entre géneros musicais
5. Inclui músicas clássicas e modernas
6. Considera o tom, temas e emoções do livro

FORMATO para cada música:
🎵 **"Nome da Música"** - Artista
   ↳ Porque combina: [breve explicação]

Organiza por momentos/temas do livro se apropriado.
Responde em português."""

        elif aspect == 'trailer':
            # Generate movie trailer text
            prompt = f"""Cria o texto para um TRAILER CINEMATOGRÁFICO épico do livro {book_ref}.

FORMATO:
1. FADE IN com contexto atmosférico
2. Frases impactantes intercaladas com descrições visuais
3. Apresentação dos personagens principais
4. Build-up de tensão
5. Clímax com frase marcante
6. Título e tagline final

ESTILO:
- Dramático e cinematográfico
- Frases curtas e impactantes
- Pausas dramáticas indicadas com [...]
- Descrições visuais entre [VISUAL: ...]
- Música sugerida entre [MÚSICA: ...]

Escreve em português. Cria algo épico e emocionante!"""

        elif aspect == 'cover':
            # Generate cover art prompt
            prompt = f"""Cria uma descrição detalhada para gerar a CAPA do livro {book_ref} usando IA de imagem (DALL-E, Midjourney, etc).

INCLUI:
1. **Prompt Principal** (em inglês, otimizado para IA de imagem)
2. **Estilo Visual** sugerido (ex: oil painting, digital art, minimalist, etc)
3. **Cores Dominantes** recomendadas
4. **Elementos Visuais** principais a incluir
5. **Atmosfera/Mood** da imagem
6. **Variações** (3 versões alternativas do prompt)

FORMATO DO PROMPT:
- Detalhado mas conciso
- Termos técnicos de arte
- Sem texto na imagem (a menos que essencial)

Responde em português com o prompt principal em inglês."""

        elif aspect == 'casting':
            # Suggest movie casting
            prompt = f"""Sugere o ELENCO perfeito para uma adaptação cinematográfica do livro {book_ref}.

Para cada personagem principal, sugere:
🎬 **[Nome do Personagem]**
   👤 Ator/Atriz: [Nome real]
   📝 Porque: [Breve justificação]
   🎭 Alternativa: [Outro ator possível]

INSTRUÇÕES:
1. Usa atores reais e conhecidos
2. Considera idade e características físicas
3. Considera talento para o tipo de papel
4. Inclui atores de diferentes nacionalidades se apropriado
5. Sugere 6-10 personagens

Também sugere:
🎬 **Realizador ideal**: [Nome] - Porque
🎵 **Compositor para banda sonora**: [Nome] - Porque

Responde em português."""

        else:
            prompt = aspect_prompts.get(aspect, aspect_prompts['info'])
        
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        content = response.text.strip()
        
        result = {'success': True, 'content': content}
        
        # For info aspect, try to extract genre
        if aspect == 'info':
            result['genre'] = content.split('\n')[0] if content else ''
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Explorer error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== CHARACTER INTERVIEW ====================

@app.route('/interview/<int:book_id>')
def character_interview_page(book_id):
    """Character interview page"""
    book = Book.query.get_or_404(book_id)
    return render_template('character_interview.html', book=book)

@app.route('/api/book/<int:book_id>/interview', methods=['POST'])
def interview_character(book_id):
    """Chat with a character from the book"""
    try:
        book = Book.query.get_or_404(book_id)
        data = request.get_json()
        character_name = data.get('character', '').strip()
        message = data.get('message', '').strip()
        history = data.get('history', [])
        
        if not character_name or not message:
            return jsonify({'success': False, 'error': 'Personagem e mensagem obrigatórios'}), 400
        
        # Build context
        book_context = f"Livro: {book.title}\nTema: {book.theme}\nEstilo: {book.style}"
        
        # Get character info if available
        characters = book.get_characters()
        char_info = ""
        for char in characters:
            if char.get('name', '').lower() == character_name.lower():
                char_info = f"\nInformações do personagem:\n- Papel: {char.get('role', 'N/A')}\n- Personalidade: {char.get('personality', 'N/A')}\n- Background: {char.get('background', 'N/A')}"
                break
        
        # Get book excerpt for context
        book_excerpt = book.full_text[:15000] if book.full_text else ""
        
        # Build conversation history
        history_text = ""
        if history:
            history_text = "\n\nConversa anterior:\n"
            for msg in history[-6:]:
                role = "Entrevistador" if msg.get('role') == 'user' else character_name
                history_text += f"{role}: {msg.get('content', '')}\n"
        
        prompt = f"""És o personagem "{character_name}" do livro "{book.title}". 
Responde às perguntas do entrevistador COMO SE FOSSES esse personagem.

=== CONTEXTO DO LIVRO ===
{book_context}
{char_info}

=== EXCERTO DO LIVRO ===
{book_excerpt[:10000]}

=== INSTRUÇÕES ===
1. Responde SEMPRE na primeira pessoa, como se fosses {character_name}
2. Mantém a personalidade, forma de falar e conhecimento do personagem
3. Podes revelar pensamentos e sentimentos do personagem
4. Se perguntarem algo que o personagem não saberia, diz que não sabes
5. Usa expressões e vocabulário adequados ao personagem e época
6. Responde em português
7. Sê expressivo e dramático quando apropriado
{history_text}

=== PERGUNTA DO ENTREVISTADOR ===
{message}

=== RESPOSTA DE {character_name.upper()} ==="""

        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        
        return jsonify({
            'success': True,
            'response': response.text.strip(),
            'character': character_name
        })
        
    except Exception as e:
        print(f"Interview error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/book/<int:book_id>/characters-list', methods=['GET'])
def get_book_characters_list(book_id):
    """Get list of characters for interview selection"""
    try:
        book = Book.query.get_or_404(book_id)
        
        # Try to get stored characters first
        characters = book.get_characters()
        
        if characters:
            char_list = [{'name': c.get('name', ''), 'role': c.get('role', '')} for c in characters]
            return jsonify({'success': True, 'characters': char_list})
        
        # If no characters stored, extract from book with AI
        prompt = f"""Analisa este livro e lista os personagens principais:

Título: {book.title}
Tema: {book.theme}
Texto: {book.full_text[:8000]}

Lista os 5-8 personagens mais importantes no formato JSON:
[{{"name": "Nome", "role": "Papel na história"}}]

Responde APENAS com o JSON, sem texto adicional."""

        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        
        import json
        text = response.text.strip()
        # Clean up response
        if text.startswith('```'):
            text = text.split('\n', 1)[1].rsplit('```', 1)[0]
        
        char_list = json.loads(text)
        return jsonify({'success': True, 'characters': char_list})
        
    except Exception as e:
        print(f"Characters list error: {e}")
        return jsonify({'success': False, 'characters': [], 'error': str(e)})

# ==================== CONTINUE STORY ====================

@app.route('/api/book/<int:book_id>/continue', methods=['POST'])
def continue_story(book_id):
    """Generate the next chapter or continuation of the story"""
    try:
        book = Book.query.get_or_404(book_id)
        data = request.get_json()
        continuation_type = data.get('type', 'chapter')  # chapter, epilogue, sequel
        direction = data.get('direction', '')  # Optional direction for the story
        
        # Get the last part of the book
        last_text = book.full_text[-10000:] if book.full_text else ""
        
        # Get characters and world info
        characters = book.get_characters()
        world = book.get_world_setting()
        
        char_info = ""
        if characters:
            char_names = [c.get('name', '') for c in characters[:5]]
            char_info = f"Personagens principais: {', '.join(char_names)}"
        
        world_info = ""
        if world:
            world_info = f"Cenário: {world.get('setting', '')} | Época: {world.get('time_period', '')}"
        
        type_prompts = {
            'chapter': f"""Escreve o PRÓXIMO CAPÍTULO desta história, continuando naturalmente de onde parou.
O capítulo deve ter aproximadamente 1500-2000 palavras.""",
            
            'epilogue': f"""Escreve um EPÍLOGO para esta história.
Mostra o que aconteceu aos personagens depois do final.
O epílogo deve ter aproximadamente 800-1000 palavras.""",
            
            'sequel': f"""Escreve o INÍCIO DE UMA SEQUELA desta história.
Passa algum tempo depois dos eventos originais.
Introduz um novo conflito ou desafio.
Escreve aproximadamente 2000 palavras (prólogo + capítulo 1)."""
        }
        
        direction_text = f"\n\nDireção sugerida: {direction}" if direction else ""
        
        prompt = f"""És um autor talentoso. Continua esta história mantendo o mesmo estilo e tom.

=== INFORMAÇÕES DO LIVRO ===
Título: {book.title}
Tema: {book.theme}
Estilo: {book.style}
{char_info}
{world_info}

=== ÚLTIMAS PÁGINAS DO LIVRO ===
{last_text}

=== TAREFA ===
{type_prompts.get(continuation_type, type_prompts['chapter'])}
{direction_text}

=== INSTRUÇÕES ===
1. Mantém o mesmo estilo de escrita
2. Continua naturalmente a partir do ponto onde parou
3. Desenvolve os personagens de forma consistente
4. Cria tensão e interesse
5. Escreve em português
6. Inclui título do capítulo/secção

=== CONTINUAÇÃO ==="""

        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        
        return jsonify({
            'success': True,
            'continuation': response.text.strip(),
            'type': continuation_type
        })
        
    except Exception as e:
        print(f"Continue story error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== QUIZ GENERATOR ====================

@app.route('/quiz/<int:book_id>')
def quiz_page(book_id):
    """Quiz page for a book"""
    book = Book.query.get_or_404(book_id)
    return render_template('book_quiz.html', book=book)

@app.route('/api/book/<int:book_id>/quiz', methods=['POST'])
def generate_quiz(book_id):
    """Generate a quiz about the book"""
    try:
        book = Book.query.get_or_404(book_id)
        data = request.get_json()
        difficulty = data.get('difficulty', 'medium')  # easy, medium, hard
        num_questions = min(data.get('num_questions', 10), 20)
        
        difficulty_prompts = {
            'easy': 'Perguntas simples sobre factos básicos da história.',
            'medium': 'Perguntas que requerem boa compreensão da história e personagens.',
            'hard': 'Perguntas difíceis sobre detalhes, simbolismo e análise profunda.'
        }
        
        prompt = f"""Cria um quiz sobre o livro com base no conteúdo fornecido.

=== LIVRO ===
Título: {book.title}
Tema: {book.theme}
Estilo: {book.style}

Conteúdo:
{book.full_text[:20000]}

=== TAREFA ===
Cria {num_questions} perguntas de escolha múltipla.
Dificuldade: {difficulty} - {difficulty_prompts.get(difficulty, '')}

=== FORMATO JSON ===
Responde APENAS com JSON válido neste formato:
[
  {{
    "question": "Pergunta aqui?",
    "options": ["Opção A", "Opção B", "Opção C", "Opção D"],
    "correct": 0,
    "explanation": "Explicação da resposta correta"
  }}
]

O campo "correct" é o índice (0-3) da opção correta.
Responde APENAS com o JSON, sem texto adicional."""

        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        
        import json
        text = response.text.strip()
        
        # Clean up JSON response
        if text.startswith('```'):
            text = text.split('\n', 1)[1].rsplit('```', 1)[0]
        
        questions = json.loads(text)
        
        return jsonify({
            'success': True,
            'questions': questions,
            'total': len(questions),
            'difficulty': difficulty
        })
        
    except json.JSONDecodeError as e:
        print(f"Quiz JSON error: {e}")
        return jsonify({'success': False, 'error': 'Erro ao gerar quiz. Tente novamente.'}), 500
    except Exception as e:
        print(f"Quiz error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Create database tables
with app.app_context():
    # Ensure database directory exists
    db_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database')
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
    
    db.create_all()
    print("Database tables created successfully!")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
