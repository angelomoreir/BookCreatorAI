from flask import Flask, render_template, request, jsonify, Response, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
import google.generativeai as genai
import json
import os
import logging
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

from models.book import db, Book, Series, User, SubscriptionHistory, AnalysisHistory, Favorite, PLAN_CONFIG, PushSubscription, Notification, UserTasteProfile, BookPrediction, PromoCode, ErrorLog, LoginLog, EmailTemplate, ScheduledNotification, AdminGoal, AppSettings, BlockedIP
import config

# Configure logging
logging.basicConfig(
    level=logging.INFO if config.FLASK_ENV == 'production' else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY

# Security configurations
app.config['SESSION_COOKIE_SECURE'] = config.SESSION_COOKIE_SECURE
app.config['SESSION_COOKIE_HTTPONLY'] = config.SESSION_COOKIE_HTTPONLY
app.config['SESSION_COOKIE_SAMESITE'] = config.SESSION_COOKIE_SAMESITE

# Use DATABASE_URL from environment (PostgreSQL on Render) or fallback to SQLite locally
database_url = os.environ.get('DATABASE_URL')
if database_url:
    # Render provides postgres:// but SQLAlchemy requires postgresql://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(basedir, 'database', 'books.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor, faça login para aceder a esta página.'
login_manager.login_message_category = 'info'

# Import security utilities
from utils.security import add_security_headers, check_blocked_ip, get_client_ip, rate_limit, sanitize_string
from utils.cache import cache, get_cached_ai_response, cache_ai_response

@app.before_request
def before_request_security():
    """Security checks before each request"""
    # Check if IP is blocked
    blocked_response = check_blocked_ip()
    if blocked_response:
        return blocked_response

@app.after_request
def after_request_security(response):
    """Add security headers to all responses"""
    return add_security_headers(response)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Custom decorator for API routes that need login
from functools import wraps
def api_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'error': 'Login necessário', 'login_required': True}), 401
        return f(*args, **kwargs)
    return decorated_function

# Custom decorator for admin routes
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        if not getattr(current_user, 'is_admin', False):
            flash('Acesso não autorizado.', 'error')
            return redirect(url_for('book_explorer_page'))
        return f(*args, **kwargs)
    return decorated_function

# Register blueprints
from routes.subscription import subscription_bp
app.register_blueprint(subscription_bp, url_prefix='/subscription')

# Configure Gemini API
if config.DEBUG:
    logger.debug(f"API KEY FOUND? {'Yes' if config.GEMINI_API_KEY else 'No'}")
if not config.GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY is missing from environment variables!")

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
        model = genai.GenerativeModel('gemini-2.5-flash')
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
        model = genai.GenerativeModel('gemini-2.5-flash')
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
        logger.warning(f"Error parsing response: {e}")
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
    """Landing page for non-authenticated users, explorer for authenticated"""
    if current_user.is_authenticated:
        return redirect(url_for('book_explorer_page'))
    return render_template('landing.html')

@app.route('/home')
def landing():
    """Landing page"""
    return render_template('landing.html')

@app.route('/setup-admin-bookcreatorai-2026')
def setup_admin():
    """One-time setup route to create supervisor account"""
    existing = User.query.filter_by(email='supervisor').first()
    if existing:
        return jsonify({'status': 'already exists', 'email': 'supervisor', 'is_admin': existing.is_admin})
    hashed_password = bcrypt.generate_password_hash('Tgnwlp4s1americo').decode('utf-8')
    supervisor = User(
        name='Supervisor',
        email='supervisor',
        password_hash=hashed_password,
        is_admin=True,
        is_verified=True,
        plan='premium',
        is_active=True
    )
    db.session.add(supervisor)
    db.session.commit()
    return jsonify({'status': 'created', 'email': 'supervisor', 'password': 'Tgnwlp4s1americo', 'dashboard': '/admin/dashboard'})

@app.route('/faq')
def faq():
    """FAQ and Support page"""
    return render_template('faq.html')

@app.route('/terms')
def terms():
    """Terms of Service page"""
    return render_template('terms.html')

@app.route('/privacy')
def privacy():
    """Privacy Policy page"""
    return render_template('privacy.html')

@app.route('/manual')
def manual():
    """User manual page"""
    return render_template('manual.html')

@app.route('/manual/download')
def download_manual():
    """Download manual as PDF"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
    from io import BytesIO
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=24, spaceAfter=30, alignment=TA_CENTER, textColor=colors.HexColor('#6366f1'))
    h1_style = ParagraphStyle('CustomH1', parent=styles['Heading1'], fontSize=18, spaceBefore=20, spaceAfter=10, textColor=colors.HexColor('#6366f1'))
    h2_style = ParagraphStyle('CustomH2', parent=styles['Heading2'], fontSize=14, spaceBefore=15, spaceAfter=8, textColor=colors.HexColor('#8b5cf6'))
    body_style = ParagraphStyle('CustomBody', parent=styles['Normal'], fontSize=11, spaceAfter=8, alignment=TA_JUSTIFY)
    bullet_style = ParagraphStyle('CustomBullet', parent=styles['Normal'], fontSize=11, leftIndent=20, spaceAfter=4)
    tip_style = ParagraphStyle('CustomTip', parent=styles['Normal'], fontSize=10, leftIndent=10, textColor=colors.HexColor('#7c3aed'), spaceAfter=10)
    
    story = []
    
    # Title
    story.append(Paragraph("📖 Manual de Utilização", title_style))
    story.append(Paragraph("Alma do Livro - Guia Completo", styles['Heading2']))
    story.append(Spacer(1, 30))
    
    # Section 1
    story.append(Paragraph("1. Introdução", h1_style))
    story.append(Paragraph("Bem-vindo ao Alma do Livro! Esta aplicação utiliza inteligência artificial avançada para te ajudar a explorar, compreender e interagir com qualquer livro de forma única e envolvente.", body_style))
    story.append(Paragraph("Com o Alma do Livro, podes:", body_style))
    story.append(Paragraph("• Obter resumos detalhados de qualquer livro", bullet_style))
    story.append(Paragraph("• Analisar personagens, temas e simbolismo", bullet_style))
    story.append(Paragraph("• Entrevistar personagens fictícios", bullet_style))
    story.append(Paragraph("• Criar quizzes para testar conhecimentos", bullet_style))
    story.append(Paragraph("• Gerar continuações e finais alternativos", bullet_style))
    story.append(Paragraph("• Descobrir playlists, casting de filmes e muito mais", bullet_style))
    story.append(Spacer(1, 15))
    
    # Section 2
    story.append(Paragraph("2. Como Começar", h1_style))
    story.append(Paragraph("<b>Passo 1: Criar Conta</b> - Clica em 'Começar Grátis' na página inicial e preenche o formulário com o teu nome, email e password. A conta gratuita dá-te acesso a 10 análises por mês.", body_style))
    story.append(Paragraph("<b>Passo 2: Fazer Login</b> - Após criar a conta, faz login com o teu email e password para aceder ao Explorador de Livros.", body_style))
    story.append(Paragraph("<b>Passo 3: Explorar um Livro</b> - No Explorador, introduz o título do livro que queres analisar (e opcionalmente o autor). Clica em 'Explorar Livro' para começar!", body_style))
    story.append(Spacer(1, 15))
    
    # Section 3
    story.append(Paragraph("3. Explorador de Livros", h1_style))
    story.append(Paragraph("O Explorador é a funcionalidade principal da aplicação. Permite-te analisar qualquer livro publicado usando inteligência artificial.", body_style))
    story.append(Paragraph("💡 Dica: A IA conhece milhões de livros! Desde clássicos como 'Dom Quixote' até bestsellers modernos como 'Harry Potter'.", tip_style))
    
    story.append(Paragraph("3.1 Análises Disponíveis", h2_style))
    story.append(Paragraph("• <b>Resumo</b> - Sinopse completa e detalhada do livro", bullet_style))
    story.append(Paragraph("• <b>Personagens</b> - Lista e análise de todos os personagens", bullet_style))
    story.append(Paragraph("• <b>Temas</b> - Temas principais e mensagens da obra", bullet_style))
    story.append(Paragraph("• <b>Mundo</b> - Cenário, época e ambientação", bullet_style))
    story.append(Paragraph("• <b>Estilo</b> - Análise do estilo literário do autor", bullet_style))
    story.append(Paragraph("• <b>Citações</b> - Citações famosas e memoráveis", bullet_style))
    story.append(Paragraph("• <b>Similares</b> - Recomendações de livros semelhantes", bullet_style))
    story.append(Paragraph("• <b>Simbolismo</b> - Símbolos e significados ocultos", bullet_style))
    story.append(Spacer(1, 15))
    
    # Section 4
    story.append(Paragraph("4. Funcionalidades Interativas", h1_style))
    story.append(Paragraph("Estas são as funcionalidades mais divertidas e únicas do Alma do Livro! Disponíveis nos planos Pro e Premium.", body_style))
    
    story.append(Paragraph("4.1 Entrevistas com Personagens", h2_style))
    story.append(Paragraph("Conversa diretamente com qualquer personagem do livro! A IA assume a personalidade do personagem e responde como se fosse ele.", body_style))
    
    story.append(Paragraph("4.2 Quiz Interativo", h2_style))
    story.append(Paragraph("Testa os teus conhecimentos sobre o livro com perguntas de escolha múltipla geradas pela IA. Disponível em três níveis: Fácil, Médio e Difícil.", body_style))
    
    story.append(Paragraph("4.3 Continuações de História", h2_style))
    story.append(Paragraph("Gera novos conteúdos para o livro: próximo capítulo, epílogo ou início de uma sequela.", body_style))
    
    story.append(Paragraph("4.4 Finais Alternativos", h2_style))
    story.append(Paragraph("Explora cenários 'E se...?' e descobre como a história poderia ter sido diferente.", body_style))
    story.append(Spacer(1, 15))
    
    # Section 5
    story.append(Paragraph("5. Funcionalidades Extra", h1_style))
    story.append(Paragraph("• <b>Playlist Sugerida</b> - Músicas reais que combinam com a atmosfera do livro", bullet_style))
    story.append(Paragraph("• <b>Trailer Cinematográfico</b> - Texto descritivo para um trailer de filme", bullet_style))
    story.append(Paragraph("• <b>Casting de Filme</b> - Sugestões de atores para cada personagem", bullet_style))
    story.append(Paragraph("• <b>Prompt para Capa</b> - Descrições otimizadas para DALL-E/Midjourney", bullet_style))
    story.append(Paragraph("• <b>Cronologia</b> - Linha temporal dos eventos do livro", bullet_style))
    story.append(Paragraph("• <b>Adaptações</b> - Filmes e séries baseados no livro", bullet_style))
    story.append(Spacer(1, 15))
    
    # Section 6
    story.append(Paragraph("6. Gestão de Conta", h1_style))
    story.append(Paragraph("Na tua conta podes:", body_style))
    story.append(Paragraph("• Ver o teu uso mensal (quantas análises já fizeste)", bullet_style))
    story.append(Paragraph("• Histórico de leitura (todos os livros que exploraste)", bullet_style))
    story.append(Paragraph("• Favoritos (guardar livros e análises favoritas)", bullet_style))
    story.append(Paragraph("• Dashboard (estatísticas detalhadas de utilização)", bullet_style))
    story.append(Paragraph("• Gerir subscrição (fazer upgrade ou cancelar plano)", bullet_style))
    story.append(Paragraph("💡 Dica: O contador de uso reinicia no primeiro dia de cada mês!", tip_style))
    story.append(Spacer(1, 15))
    
    # Section 7
    story.append(Paragraph("7. Planos e Preços", h1_style))
    story.append(Paragraph("<b>Gratuito (€0/mês)</b> - 10 análises/mês, resumos e personagens, temas e análise básica.", body_style))
    story.append(Paragraph("<b>Pro (€9.99/mês)</b> - 100 análises/mês, todas as análises, quiz e entrevistas, continuações e finais alternativos.", body_style))
    story.append(Paragraph("<b>Premium (€19.99/mês)</b> - 1000 análises/mês, tudo do Pro, exportação PDF, suporte prioritário.", body_style))
    story.append(Spacer(1, 15))
    
    # Section 8
    story.append(Paragraph("8. Dicas e Truques", h1_style))
    story.append(Paragraph("💡 <b>Sê específico com o título</b> - Se existem vários livros com o mesmo nome, adiciona o autor para melhores resultados.", tip_style))
    story.append(Paragraph("💡 <b>Usa os exemplos rápidos</b> - Clica nos botões de exemplo para testar rapidamente com livros populares.", tip_style))
    story.append(Paragraph("💡 <b>Guarda nos favoritos</b> - Usa o botão ⭐ para guardar livros e análises que queres revisitar.", tip_style))
    story.append(Paragraph("💡 <b>Exporta as análises</b> - Usa o botão 📥 para exportar todas as análises de um livro em PDF ou EPUB.", tip_style))
    story.append(Paragraph("💡 <b>Muda o idioma</b> - Usa o seletor de idioma no topo para obter análises em diferentes línguas.", tip_style))
    
    story.append(Spacer(1, 30))
    story.append(Paragraph("Alma do Livro © 2026 - Manual de Utilização v1.0", ParagraphStyle('Footer', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER, textColor=colors.gray)))
    
    doc.build(story)
    buffer.seek(0)
    
    return Response(
        buffer.getvalue(),
        mimetype='application/pdf',
        headers={
            'Content-Disposition': 'attachment; filename="Manual_Alma_do_Livro.pdf"',
            'Content-Type': 'application/pdf'
        }
    )

# ==================== PUSH NOTIFICATIONS API ====================

# VAPID public key for Web Push
VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY', 'BEl62iUYgUivxIkv69yViEuiBIa-Ib9-SkvMeAtA3LFgDzkrxZJjSgSnfckjBJuBkr3qBUYIHBQFLXYp5Nksh8U')

@app.route('/api/notifications/vapid-key')
def get_vapid_key():
    """Get VAPID public key for push subscription"""
    return jsonify({
        'success': True,
        'publicKey': VAPID_PUBLIC_KEY
    })

@app.route('/api/notifications/subscribe', methods=['POST'])
@api_login_required
def subscribe_push():
    """Subscribe to push notifications"""
    try:
        data = request.get_json()
        subscription = data.get('subscription', {})
        
        endpoint = subscription.get('endpoint')
        keys = subscription.get('keys', {})
        p256dh = keys.get('p256dh')
        auth = keys.get('auth')
        
        if not endpoint or not p256dh or not auth:
            return jsonify({'success': False, 'error': 'Dados de subscrição inválidos'}), 400
        
        # Check if subscription already exists
        existing = PushSubscription.query.filter_by(endpoint=endpoint).first()
        
        if existing:
            # Update existing subscription
            existing.user_id = current_user.id
            existing.p256dh_key = p256dh
            existing.auth_key = auth
            existing.is_active = True
            existing.last_used = datetime.utcnow()
        else:
            # Create new subscription
            new_sub = PushSubscription(
                user_id=current_user.id,
                endpoint=endpoint,
                p256dh_key=p256dh,
                auth_key=auth
            )
            db.session.add(new_sub)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Notificações ativadas com sucesso!'
        })
    except Exception as e:
        db.session.rollback()
        logger.warning(f"Subscribe push error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/notifications/unsubscribe', methods=['POST'])
@api_login_required
def unsubscribe_push():
    """Unsubscribe from push notifications"""
    try:
        data = request.get_json()
        endpoint = data.get('endpoint')
        
        if endpoint:
            sub = PushSubscription.query.filter_by(
                endpoint=endpoint,
                user_id=current_user.id
            ).first()
            
            if sub:
                sub.is_active = False
                db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Notificações desativadas'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/notifications/preferences', methods=['GET'])
@api_login_required
def get_notification_preferences():
    """Get user's notification preferences"""
    sub = PushSubscription.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).first()
    
    if not sub:
        return jsonify({
            'success': True,
            'subscribed': False,
            'preferences': None
        })
    
    return jsonify({
        'success': True,
        'subscribed': True,
        'preferences': {
            'usage_reset': sub.notify_usage_reset,
            'new_features': sub.notify_new_features,
            'tips': sub.notify_tips,
            'promotions': sub.notify_promotions
        }
    })

@app.route('/api/notifications/preferences', methods=['POST'])
@api_login_required
def update_notification_preferences():
    """Update user's notification preferences"""
    try:
        data = request.get_json()
        
        subs = PushSubscription.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).all()
        
        for sub in subs:
            if 'usage_reset' in data:
                sub.notify_usage_reset = data['usage_reset']
            if 'new_features' in data:
                sub.notify_new_features = data['new_features']
            if 'tips' in data:
                sub.notify_tips = data['tips']
            if 'promotions' in data:
                sub.notify_promotions = data['promotions']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Preferências atualizadas!'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/notifications/history')
@api_login_required
def get_notification_history():
    """Get user's notification history"""
    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(Notification.sent_at.desc()).limit(50).all()
    
    return jsonify({
        'success': True,
        'notifications': [n.to_dict() for n in notifications],
        'unread_count': sum(1 for n in notifications if not n.is_read)
    })

@app.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
@api_login_required
def mark_notification_read(notification_id):
    """Mark a notification as read"""
    notification = Notification.query.filter_by(
        id=notification_id,
        user_id=current_user.id
    ).first()
    
    if notification:
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/notifications/test', methods=['POST'])
@api_login_required
def test_notification():
    """Send a test notification to the current user"""
    try:
        from utils.notifications import send_notification_to_user
        
        count = send_notification_to_user(
            current_user,
            title="🔔 Teste de Notificação",
            body="As notificações estão a funcionar corretamente!",
            url="/explorer",
            notification_type="general",
            save_to_db=False
        )
        
        return jsonify({
            'success': True,
            'sent_count': count,
            'message': f'Notificação enviada para {count} dispositivo(s)!'
        })
    except Exception as e:
        logger.warning(f"Test notification error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== END PUSH NOTIFICATIONS API ====================

# ==================== TASTE PREDICTION API ("VAI GOSTAR") ====================

@app.route('/api/taste/profile')
@api_login_required
def get_taste_profile():
    """Get user's taste profile"""
    profile = UserTasteProfile.query.filter_by(user_id=current_user.id).first()
    
    if not profile:
        return jsonify({
            'success': True,
            'has_profile': False,
            'profile': None,
            'message': 'Explora mais livros para construir o teu perfil de gostos!'
        })
    
    return jsonify({
        'success': True,
        'has_profile': True,
        'profile': profile.to_dict()
    })

@app.route('/api/taste/analyze', methods=['POST'])
@api_login_required
def analyze_taste():
    """Analyze user's reading history and build taste profile"""
    try:
        # Get user's analysis history
        history = AnalysisHistory.query.filter_by(user_id=current_user.id).all()
        
        if len(history) < 3:
            return jsonify({
                'success': False,
                'error': 'Precisas de explorar pelo menos 3 livros para gerar o teu perfil de gostos.',
                'books_needed': 3 - len(history)
            })
        
        # Get or create taste profile
        profile = UserTasteProfile.query.filter_by(user_id=current_user.id).first()
        if not profile:
            profile = UserTasteProfile(user_id=current_user.id)
            db.session.add(profile)
        
        # Build list of books explored
        books_map = {}
        for h in history:
            author = h.book_author or 'Desconhecido'
            key = (h.book_title, author)
            if key not in books_map:
                books_map[key] = {
                    'title': h.book_title,
                    'author': author,
                    'aspects': []
                }
            if h.aspect and h.aspect not in books_map[key]['aspects']:
                books_map[key]['aspects'].append(h.aspect)

        books_explored = list(books_map.values())
        
        # Get favorites for additional signal
        favorites = Favorite.query.filter_by(user_id=current_user.id, favorite_type='book').all()
        favorite_books = [f.book_title for f in favorites]
        
        # Use AI to analyze taste profile
        prompt = f"""Analisa o perfil de leitura deste utilizador baseado nos livros que explorou e nos seus favoritos.

LIVROS EXPLORADOS:
{json.dumps(books_explored, indent=2, ensure_ascii=False)}

LIVROS FAVORITOS:
{json.dumps(favorite_books, ensure_ascii=False)}

Gera uma análise detalhada do perfil de gostos literários em formato JSON com esta estrutura EXATA:
{{
    "genres": {{"género1": score, "género2": score}},
    "themes": {{"tema1": score, "tema2": score}},
    "styles": {{"estilo1": score, "estilo2": score}},
    "authors": ["autor1", "autor2"],
    "moods": {{"mood1": score, "mood2": score}},
    "prefers_series": true/false/null,
    "prefers_long_books": true/false/null,
    "prefers_complex_plots": true/false/null,
    "taste_summary": "Resumo em 2-3 frases do perfil de leitor"
}}

Os scores devem ser entre 0.0 e 1.0 (1.0 = muito forte preferência).
Géneros: fantasy, sci-fi, romance, thriller, mystery, horror, literary_fiction, historical, young_adult, etc.
Temas: love, redemption, adventure, power, identity, family, friendship, death, war, etc.
Estilos: descriptive, fast_paced, literary, humorous, dark, emotional, philosophical, etc.
Moods: escape, learn, emotion, excitement, comfort, challenge, etc.

Responde APENAS com o JSON, sem texto adicional."""

        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Clean JSON response
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
        response_text = response_text.strip()
        
        taste_data = json.loads(response_text)
        
        # Update profile
        profile.set_genres(taste_data.get('genres', {}))
        profile.set_themes(taste_data.get('themes', {}))
        profile.preferred_styles = json.dumps(taste_data.get('styles', {}))
        profile.favorite_authors = json.dumps(taste_data.get('authors', []))
        profile.reading_moods = json.dumps(taste_data.get('moods', {}))
        profile.prefers_series = taste_data.get('prefers_series')
        profile.prefers_long_books = taste_data.get('prefers_long_books')
        profile.prefers_complex_plots = taste_data.get('prefers_complex_plots')
        profile.taste_summary = taste_data.get('taste_summary', '')
        profile.books_analyzed = len(history)
        profile.last_updated = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'profile': profile.to_dict(),
            'message': 'Perfil de gostos atualizado com sucesso!'
        })
        
    except json.JSONDecodeError as e:
        return jsonify({'success': False, 'error': 'Erro ao processar resposta da IA'}), 500
    except Exception as e:
        db.session.rollback()
        logger.warning(f"Taste analyze error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/taste/predictions')
@api_login_required
def get_predictions():
    """Get AI predictions of books user will like"""
    # Get existing predictions
    predictions = BookPrediction.query.filter_by(
        user_id=current_user.id
    ).order_by(BookPrediction.match_score.desc()).limit(20).all()
    
    return jsonify({
        'success': True,
        'predictions': [p.to_dict() for p in predictions]
    })

@app.route('/api/taste/predict', methods=['POST'])
@api_login_required
def generate_predictions():
    """Generate new book predictions based on taste profile"""
    try:
        from utils.rate_limiter import check_and_reset_monthly_usage, get_usage_info
        
        # Check and reset monthly usage if needed
        check_and_reset_monthly_usage(current_user)
        usage_info = get_usage_info(current_user)
        if usage_info.get('is_limit_reached'):
            limit = usage_info.get('usage_limit')
            return jsonify({
                'success': False,
                'error': f'Limite mensal de {limit} análises atingido. Aguarda pelo reset ou faz upgrade.',
                'limit_reached': True,
                'usage_info': usage_info
            }), 403
        
        # Get taste profile
        profile = UserTasteProfile.query.filter_by(user_id=current_user.id).first()
        
        if not profile or not profile.taste_summary:
            return jsonify({
                'success': False,
                'error': 'Primeiro precisas de analisar o teu perfil de gostos.',
                'need_analysis': True
            })
        
        # Get books already explored to exclude
        history = AnalysisHistory.query.filter_by(user_id=current_user.id).all()
        explored_titles = [h.book_title.lower() for h in history]
        
        # Get existing predictions to exclude
        existing_predictions = BookPrediction.query.filter_by(user_id=current_user.id).all()
        predicted_titles = [p.book_title.lower() for p in existing_predictions]
        
        # Build prompt for AI
        prompt = f"""Baseado neste perfil de leitor, sugere 10 livros que esta pessoa VAI ADORAR.

PERFIL DE GOSTOS:
- Géneros favoritos: {profile.favorite_genres}
- Temas favoritos: {profile.favorite_themes}
- Estilos preferidos: {profile.preferred_styles}
- Autores favoritos: {profile.favorite_authors}
- Lê para: {profile.reading_moods}
- Resumo: {profile.taste_summary}

LIVROS JÁ EXPLORADOS (NÃO SUGERIR):
{json.dumps(explored_titles[:30], ensure_ascii=False)}

LIVROS JÁ SUGERIDOS (NÃO REPETIR):
{json.dumps(predicted_titles[:30], ensure_ascii=False)}

Sugere 10 livros REAIS e PUBLICADOS que correspondam perfeitamente a este perfil.
Para cada livro, indica a percentagem de match (0-100) e 3 razões específicas.

Responde em JSON com esta estrutura EXATA:
{{
    "predictions": [
        {{
            "title": "Título do Livro",
            "author": "Nome do Autor",
            "match_score": 95,
            "reasons": [
                "Razão 1 específica",
                "Razão 2 específica", 
                "Razão 3 específica"
            ]
        }}
    ]
}}

Ordena por match_score (maior primeiro). Responde APENAS com JSON."""

        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Clean JSON
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
        response_text = response_text.strip()
        
        predictions_data = json.loads(response_text)
        
        # Save predictions
        new_predictions = []
        for pred in predictions_data.get('predictions', []):
            title = pred.get('title', '').strip()
            
            # Skip if already predicted or explored
            if title.lower() in predicted_titles or title.lower() in explored_titles:
                continue
            
            prediction = BookPrediction(
                user_id=current_user.id,
                book_title=title,
                book_author=pred.get('author', ''),
                match_score=pred.get('match_score', 0),
                reasons=json.dumps(pred.get('reasons', []), ensure_ascii=False)
            )
            db.session.add(prediction)
            new_predictions.append(prediction)
        
        # Increment usage
        current_user.usage_count += 1
        db.session.commit()
        
        return jsonify({
            'success': True,
            'predictions': [p.to_dict() for p in new_predictions],
            'count': len(new_predictions),
            'message': f'Encontrámos {len(new_predictions)} livros perfeitos para ti!'
        })
        
    except json.JSONDecodeError:
        return jsonify({'success': False, 'error': 'Erro ao processar resposta da IA'}), 500
    except Exception as e:
        db.session.rollback()
        logger.warning(f"Predictions error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/taste/feedback', methods=['POST'])
@api_login_required
def prediction_feedback():
    """Record user feedback on a prediction"""
    try:
        data = request.get_json()
        prediction_id = data.get('prediction_id')
        feedback = data.get('feedback')  # 'liked', 'disliked', 'neutral'
        
        if not prediction_id or feedback not in ['liked', 'disliked', 'neutral']:
            return jsonify({'success': False, 'error': 'Dados inválidos'}), 400
        
        prediction = BookPrediction.query.filter_by(
            id=prediction_id,
            user_id=current_user.id
        ).first()
        
        if not prediction:
            return jsonify({'success': False, 'error': 'Previsão não encontrada'}), 404
        
        prediction.user_feedback = feedback
        
        # If liked, add to taste profile
        if feedback == 'liked':
            profile = UserTasteProfile.query.filter_by(user_id=current_user.id).first()
            if profile:
                profile.add_liked_book(prediction.book_title, prediction.book_author, 5)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Feedback registado! Isto ajuda a melhorar as sugestões.'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/taste/rate-book', methods=['POST'])
@api_login_required
def rate_book():
    """Rate a book to improve taste profile"""
    try:
        data = request.get_json()
        title = data.get('title', '').strip()
        author = data.get('author', '').strip()
        rating = data.get('rating', 5)  # 1-5
        
        if not title:
            return jsonify({'success': False, 'error': 'Título é obrigatório'}), 400
        
        # Get or create profile
        profile = UserTasteProfile.query.filter_by(user_id=current_user.id).first()
        if not profile:
            profile = UserTasteProfile(user_id=current_user.id)
            db.session.add(profile)
        
        profile.add_liked_book(title, author, rating)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Avaliação de "{title}" guardada!'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/vai-gostar')
@login_required
def vai_gostar_page():
    """Page showing personalized book predictions"""
    profile = UserTasteProfile.query.filter_by(user_id=current_user.id).first()
    predictions = BookPrediction.query.filter_by(
        user_id=current_user.id
    ).order_by(BookPrediction.match_score.desc()).limit(20).all()
    
    # Get analysis count for profile building
    analysis_count = AnalysisHistory.query.filter_by(user_id=current_user.id).count()
    
    return render_template('vai_gostar.html', 
                          profile=profile, 
                          predictions=predictions,
                          analysis_count=analysis_count)

# ==================== END TASTE PREDICTION API ====================

@app.route('/api/support', methods=['POST'])
def submit_support():
    """Handle support form submission"""
    from utils.email_service import send_support_confirmation
    
    try:
        data = request.get_json()
        email = data.get('email', '').strip()
        subject = data.get('subject', 'general')
        message = data.get('message', '').strip()
        
        if not email or not message:
            return jsonify({'success': False, 'error': 'Email e mensagem são obrigatórios'}), 400
        
        # Get user name if authenticated
        user_name = current_user.name if current_user.is_authenticated else email.split('@')[0]
        
        # Send confirmation email to user
        send_support_confirmation(email, user_name, subject)
        
        # Log the support request (in production, save to database or send to support system)
        logger.warning(f"[SUPPORT] From: {email}, Subject: {subject}, Message: {message[:100]}...")
        
        return jsonify({'success': True, 'message': 'Mensagem enviada com sucesso!'})
    except Exception as e:
        logger.warning(f"Support error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== FAVORITES API ====================

@app.route('/api/favorites', methods=['GET'])
@api_login_required
def get_favorites():
    """Get user's favorites"""
    favorite_type = request.args.get('type', 'all')  # 'all', 'book', 'analysis'
    
    query = Favorite.query.filter_by(user_id=current_user.id)
    
    if favorite_type != 'all':
        query = query.filter_by(favorite_type=favorite_type)
    
    favorites = query.order_by(Favorite.created_at.desc()).all()
    
    return jsonify({
        'success': True,
        'favorites': [f.to_dict() for f in favorites],
        'count': len(favorites)
    })

@app.route('/api/favorites/add', methods=['POST'])
@api_login_required
def add_favorite():
    """Add a book or analysis to favorites"""
    try:
        data = request.get_json() or {}
        favorite_type = data.get('type', 'book')  # 'book' or 'analysis'
        book_title = (data.get('book_title') or '').strip()
        book_author = (data.get('book_author') or '').strip() or None
        aspect = data.get('aspect') if favorite_type == 'analysis' else None
        content_preview = data.get('content_preview')
        notes = data.get('notes')
        
        if not book_title:
            return jsonify({'success': False, 'error': 'Título do livro é obrigatório'}), 400
        
        # Check if already favorited
        existing = Favorite.query.filter_by(
            user_id=current_user.id,
            book_title=book_title,
            book_author=book_author,
            favorite_type=favorite_type,
            aspect=aspect
        ).first()
        
        if existing:
            return jsonify({'success': False, 'error': 'Já está nos favoritos', 'already_favorited': True}), 400
        
        favorite = Favorite(
            user_id=current_user.id,
            favorite_type=favorite_type,
            book_title=book_title,
            book_author=book_author,
            aspect=aspect,
            content_preview=content_preview[:500] if content_preview else None,
            notes=notes
        )
        
        db.session.add(favorite)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Adicionado aos favoritos!',
            'favorite': favorite.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        logger.warning(f"Add favorite error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/favorites/remove', methods=['POST'])
@api_login_required
def remove_favorite():
    """Remove from favorites"""
    try:
        data = request.get_json() or {}
        favorite_id = data.get('id')
        
        # Alternative: remove by book info
        book_title = data.get('book_title')
        book_author = data.get('book_author')
        favorite_type = data.get('type', 'book')
        aspect = data.get('aspect')
        
        if favorite_id:
            favorite = Favorite.query.filter_by(id=favorite_id, user_id=current_user.id).first()
        elif book_title:
            favorite = Favorite.query.filter_by(
                user_id=current_user.id,
                book_title=book_title,
                book_author=book_author,
                favorite_type=favorite_type,
                aspect=aspect
            ).first()
        else:
            return jsonify({'success': False, 'error': 'ID ou título do livro é obrigatório'}), 400
        
        if not favorite:
            return jsonify({'success': False, 'error': 'Favorito não encontrado'}), 404
        
        db.session.delete(favorite)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Removido dos favoritos!'})
    except Exception as e:
        db.session.rollback()
        logger.warning(f"Remove favorite error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/character-relationships', methods=['POST'])
def character_relationships():
    """Generate character relationship map data for visualization"""
    try:
        data = request.get_json() or {}
        title = (data.get('title') or '').strip()
        author = (data.get('author') or '').strip()
        language = data.get('language', 'Português')
        
        if not title:
            return jsonify({'success': False, 'error': 'Título é obrigatório'}), 400
        
        # Check usage limits
        if current_user.is_authenticated:
            plan = current_user.plan or 'free'
            limits = {'free': 5, 'pro': 100, 'premium': 500}
            limit = limits.get(plan, 5)
            
            if current_user.usage_count >= limit:
                return jsonify({
                    'success': False, 
                    'error': f'Limite de {limit} análises atingido. Faça upgrade do plano.'
                }), 429
        
        # Build prompt for character relationships
        book_ref = f'"{title}"' + (f' de {author}' if author else '')
        
        prompt = f"""Analisa as relações entre os personagens do livro {book_ref}.

Identifica os personagens principais e as suas relações (família, amizade, romance, rivalidade, mentor, etc.).

Responde APENAS em JSON válido com esta estrutura exata:
{{
    "characters": [
        {{
            "id": "char1",
            "name": "Nome do Personagem",
            "role": "protagonista/antagonista/secundário",
            "description": "Breve descrição (1 frase)",
            "group": 1
        }}
    ],
    "relationships": [
        {{
            "from": "char1",
            "to": "char2",
            "type": "família/amizade/romance/rivalidade/mentor/aliado/inimigo",
            "label": "descrição curta da relação",
            "strength": 3
        }}
    ]
}}

INSTRUÇÕES:
- Inclui 5-12 personagens principais
- O campo "group" agrupa personagens relacionados (1, 2, 3, etc.)
- O campo "strength" vai de 1 (fraca) a 5 (muito forte)
- Tipos de relação: família, amizade, romance, rivalidade, mentor, aliado, inimigo, colega, servo
- Inclui todas as relações importantes entre os personagens
- Responde em {language}. Apenas JSON, sem texto adicional."""

        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        content = response.text.strip()
        
        # Parse JSON response
        import re
        
        # Clean response - remove markdown code blocks if present
        content = re.sub(r'^```json\s*', '', content)
        content = re.sub(r'^```\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        
        try:
            relationship_data = json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                relationship_data = json.loads(json_match.group())
            else:
                return jsonify({'success': False, 'error': 'Erro ao processar resposta da IA'}), 500
        
        # Update usage count
        if current_user.is_authenticated:
            current_user.usage_count += 1
            db.session.commit()
        
        return jsonify({
            'success': True,
            'data': relationship_data
        })
        
    except Exception as e:
        logger.warning(f"Character relationships error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/style-comparison', methods=['POST'])
def style_comparison():
    """Compare book's writing style with famous authors"""
    try:
        data = request.get_json() or {}
        title = (data.get('title') or '').strip()
        author = (data.get('author') or '').strip()
        language = data.get('language', 'Português')
        
        if not title:
            return jsonify({'success': False, 'error': 'Título é obrigatório'}), 400
        
        # Check usage limits
        if current_user.is_authenticated:
            plan = current_user.plan or 'free'
            limits = {'free': 5, 'pro': 100, 'premium': 500}
            limit = limits.get(plan, 5)
            
            if current_user.usage_count >= limit:
                return jsonify({
                    'success': False, 
                    'error': f'Limite de {limit} análises atingido. Faça upgrade do plano.'
                }), 429
        
        book_ref = f'"{title}"' + (f' de {author}' if author else '')
        
        prompt = f"""Analisa o estilo literário do livro {book_ref} e compara-o com autores famosos.

Avalia os seguintes aspectos do estilo:
1. Estrutura narrativa (ponto de vista, tempo verbal, estrutura)
2. Linguagem (vocabulário, complexidade, tom)
3. Técnicas literárias (metáforas, simbolismo, diálogos)
4. Ritmo e pacing
5. Temas e abordagem

Compara com 5-7 autores famosos que tenham estilos similares.

Responde APENAS em JSON válido com esta estrutura:
{{
    "book_title": "{title}",
    "style_summary": "Resumo do estilo em 2-3 frases",
    "style_characteristics": {{
        "narrative_voice": "descrição do narrador e ponto de vista",
        "language_complexity": "simples/moderada/complexa/muito complexa",
        "tone": "tom predominante (ex: melancólico, esperançoso, irónico)",
        "pacing": "lento/moderado/rápido/variável",
        "dialogue_style": "descrição do estilo de diálogos",
        "descriptive_style": "descrição do estilo descritivo"
    }},
    "similar_authors": [
        {{
            "name": "Nome do Autor Famoso",
            "similarity_percentage": 85,
            "nationality": "nacionalidade",
            "era": "época literária",
            "similar_aspects": ["aspecto1", "aspecto2", "aspecto3"],
            "famous_works": ["obra1", "obra2"],
            "explanation": "Explicação de porque são similares (2-3 frases)"
        }}
    ],
    "unique_elements": ["elemento único 1", "elemento único 2", "elemento único 3"],
    "literary_influences": ["influência detectada 1", "influência detectada 2"],
    "recommended_for_fans_of": ["Autor 1", "Autor 2", "Autor 3"]
}}

INSTRUÇÕES:
- Ordena similar_authors por similarity_percentage (maior primeiro)
- similarity_percentage deve ser entre 40 e 95 (nunca 100%)
- Inclui autores de diferentes épocas e nacionalidades se relevante
- Sê específico nas explicações
- Responde em {language}"""

        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        content = response.text.strip()
        
        # Parse JSON response
        import re
        content = re.sub(r'^```json\s*', '', content)
        content = re.sub(r'^```\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        
        try:
            style_data = json.loads(content)
        except json.JSONDecodeError:
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                style_data = json.loads(json_match.group())
            else:
                return jsonify({'success': False, 'error': 'Erro ao processar resposta da IA'}), 500
        
        # Update usage count
        if current_user.is_authenticated:
            current_user.usage_count += 1
            db.session.commit()
        
        return jsonify({
            'success': True,
            'data': style_data
        })
        
    except Exception as e:
        logger.warning(f"Style comparison error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/character-debate', methods=['POST'])
def character_debate():
    """Generate a debate between two characters from a book"""
    try:
        data = request.get_json() or {}
        title = (data.get('title') or '').strip()
        author = (data.get('author') or '').strip()
        character1 = (data.get('character1') or '').strip()
        character2 = (data.get('character2') or '').strip()
        topic = (data.get('topic') or '').strip()
        num_exchanges = min(int(data.get('num_exchanges', 4)), 8)
        language = data.get('language', 'Português')
        
        if not title:
            return jsonify({'success': False, 'error': 'Título é obrigatório'}), 400
        if not character1 or not character2:
            return jsonify({'success': False, 'error': 'Dois personagens são obrigatórios'}), 400
        if not topic:
            return jsonify({'success': False, 'error': 'Tema do debate é obrigatório'}), 400
        
        # Check usage limits
        if current_user.is_authenticated:
            plan = current_user.plan or 'free'
            limits = {'free': 5, 'pro': 100, 'premium': 500}
            limit = limits.get(plan, 5)
            
            if current_user.usage_count >= limit:
                return jsonify({
                    'success': False, 
                    'error': f'Limite de {limit} análises atingido. Faça upgrade do plano.'
                }), 429
        
        book_ref = f'"{title}"' + (f' de {author}' if author else '')
        
        prompt = f"""Cria um debate entre dois personagens do livro {book_ref}.

PERSONAGENS:
- Personagem 1: {character1}
- Personagem 2: {character2}

TEMA DO DEBATE: {topic}

INSTRUÇÕES:
1. Cada personagem deve falar como falaria no livro, mantendo a sua personalidade, vocabulário e forma de expressão
2. O debate deve ter {num_exchanges} trocas (cada troca = uma fala de cada personagem)
3. Os personagens devem defender posições diferentes baseadas nas suas personalidades e experiências no livro
4. Inclui emoções, reações e linguagem corporal entre parênteses quando relevante
5. O debate deve ser interessante, com argumentos válidos de ambos os lados
6. Mantém coerência com os eventos e conhecimentos dos personagens no livro

Responde APENAS em JSON válido com esta estrutura:
{{
    "book_title": "{title}",
    "debate_topic": "{topic}",
    "character1": {{
        "name": "{character1}",
        "position": "Posição/opinião que defende",
        "personality_traits": ["traço1", "traço2", "traço3"]
    }},
    "character2": {{
        "name": "{character2}",
        "position": "Posição/opinião que defende",
        "personality_traits": ["traço1", "traço2", "traço3"]
    }},
    "exchanges": [
        {{
            "round": 1,
            "character1_speech": {{
                "text": "Fala do personagem 1...",
                "emotion": "emoção dominante",
                "action": "ação ou linguagem corporal (opcional)"
            }},
            "character2_speech": {{
                "text": "Resposta do personagem 2...",
                "emotion": "emoção dominante",
                "action": "ação ou linguagem corporal (opcional)"
            }}
        }}
    ],
    "conclusion": {{
        "winner": "nome do personagem que teve argumentos mais fortes (ou 'empate')",
        "summary": "Resumo do debate em 2-3 frases",
        "key_moment": "O momento mais marcante do debate"
    }}
}}

Responde em {language}. Sê criativo e fiel aos personagens!"""

        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        content = response.text.strip()
        
        # Parse JSON response
        import re
        content = re.sub(r'^```json\s*', '', content)
        content = re.sub(r'^```\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        
        try:
            debate_data = json.loads(content)
        except json.JSONDecodeError:
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                debate_data = json.loads(json_match.group())
            else:
                return jsonify({'success': False, 'error': 'Erro ao processar resposta da IA'}), 500
        
        # Update usage count
        if current_user.is_authenticated:
            current_user.usage_count += 1
            db.session.commit()
        
        return jsonify({
            'success': True,
            'data': debate_data
        })
        
    except Exception as e:
        logger.warning(f"Character debate error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/character-trial', methods=['POST'])
def character_trial():
    """Generate a trial simulation for a book character"""
    try:
        data = request.get_json() or {}
        title = (data.get('title') or '').strip()
        author = (data.get('author') or '').strip()
        defendant = (data.get('defendant') or '').strip()
        charge = (data.get('charge') or '').strip()
        language = data.get('language', 'Português')
        
        if not title:
            return jsonify({'success': False, 'error': 'Título é obrigatório'}), 400
        if not defendant:
            return jsonify({'success': False, 'error': 'Réu é obrigatório'}), 400
        if not charge:
            return jsonify({'success': False, 'error': 'Acusação é obrigatória'}), 400
        
        # Check usage limits
        if current_user.is_authenticated:
            plan = current_user.plan or 'free'
            limits = {'free': 5, 'pro': 100, 'premium': 500}
            limit = limits.get(plan, 5)
            
            if current_user.usage_count >= limit:
                return jsonify({
                    'success': False, 
                    'error': f'Limite de {limit} análises atingido. Faça upgrade do plano.'
                }), 429
        
        book_ref = f'"{title}"' + (f' de {author}' if author else '')
        
        prompt = f"""Simula um julgamento do personagem {defendant} do livro {book_ref}.

ACUSAÇÃO: {charge}

Cria um julgamento completo com:
1. Apresentação do caso pelo promotor
2. Defesa do advogado de defesa
3. Testemunhas (outros personagens do livro)
4. Provas e evidências baseadas nos eventos do livro
5. Argumentos finais de ambos os lados

O utilizador será o juiz e decidirá o veredicto no final.

Responde APENAS em JSON válido com esta estrutura:
{{
    "book_title": "{title}",
    "defendant": {{
        "name": "{defendant}",
        "description": "Breve descrição do personagem",
        "role_in_book": "papel no livro"
    }},
    "charge": "{charge}",
    "charge_details": "Descrição detalhada da acusação baseada nos eventos do livro",
    "prosecution": {{
        "prosecutor_name": "Nome do promotor (personagem do livro ou genérico)",
        "opening_statement": "Declaração de abertura do promotor (2-3 frases)",
        "main_arguments": [
            {{
                "argument": "Argumento principal",
                "evidence": "Evidência do livro que suporta",
                "impact": "alto/médio/baixo"
            }}
        ],
        "closing_statement": "Declaração final do promotor"
    }},
    "defense": {{
        "lawyer_name": "Nome do advogado de defesa",
        "opening_statement": "Declaração de abertura da defesa (2-3 frases)",
        "main_arguments": [
            {{
                "argument": "Argumento de defesa",
                "evidence": "Evidência ou contexto que suporta",
                "impact": "alto/médio/baixo"
            }}
        ],
        "closing_statement": "Declaração final da defesa"
    }},
    "witnesses": [
        {{
            "name": "Nome da testemunha (personagem do livro)",
            "relationship": "Relação com o réu",
            "side": "acusação/defesa",
            "testimony": "Testemunho (2-3 frases)",
            "cross_examination_highlight": "Ponto importante do contra-interrogatório"
        }}
    ],
    "key_evidence": [
        {{
            "item": "Descrição da prova",
            "presented_by": "acusação/defesa",
            "significance": "Porque é importante"
        }}
    ],
    "verdict_options": {{
        "guilty": {{
            "consequence": "Consequência se considerado culpado",
            "justification": "Razões para este veredicto"
        }},
        "not_guilty": {{
            "consequence": "Consequência se considerado inocente",
            "justification": "Razões para este veredicto"
        }},
        "mitigated": {{
            "consequence": "Consequência com circunstâncias atenuantes",
            "justification": "Razões para este veredicto"
        }}
    }}
}}

INSTRUÇÕES:
- Usa personagens reais do livro como testemunhas
- Baseia argumentos e provas em eventos reais do livro
- Inclui 3-4 argumentos de cada lado
- Inclui 2-4 testemunhas
- Sê equilibrado - ambos os lados devem ter argumentos válidos
- Responde em {language}"""

        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        content = response.text.strip()
        
        # Parse JSON response
        import re
        content = re.sub(r'^```json\s*', '', content)
        content = re.sub(r'^```\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        
        try:
            trial_data = json.loads(content)
        except json.JSONDecodeError:
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                trial_data = json.loads(json_match.group())
            else:
                return jsonify({'success': False, 'error': 'Erro ao processar resposta da IA'}), 500
        
        # Update usage count
        if current_user.is_authenticated:
            current_user.usage_count += 1
            db.session.commit()
        
        return jsonify({
            'success': True,
            'data': trial_data
        })
        
    except Exception as e:
        logger.warning(f"Character trial error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/character-letter', methods=['POST'])
def character_letter():
    """Generate a letter written by one character to another"""
    try:
        data = request.get_json() or {}
        title = (data.get('title') or '').strip()
        author = (data.get('author') or '').strip()
        sender = (data.get('sender') or '').strip()
        recipient = (data.get('recipient') or '').strip()
        context = (data.get('context') or '').strip()
        tone = (data.get('tone') or 'sincero').strip()
        language = data.get('language', 'Português')
        
        if not title:
            return jsonify({'success': False, 'error': 'Título é obrigatório'}), 400
        if not sender:
            return jsonify({'success': False, 'error': 'Remetente é obrigatório'}), 400
        if not recipient:
            return jsonify({'success': False, 'error': 'Destinatário é obrigatório'}), 400
        
        # Check usage limits
        if current_user.is_authenticated:
            plan = current_user.plan or 'free'
            limits = {'free': 5, 'pro': 100, 'premium': 500}
            limit = limits.get(plan, 5)
            
            if current_user.usage_count >= limit:
                return jsonify({
                    'success': False, 
                    'error': f'Limite de {limit} análises atingido. Faça upgrade do plano.'
                }), 429
        
        book_ref = f'"{title}"' + (f' de {author}' if author else '')
        
        context_instruction = f"\nCONTEXTO/MOMENTO: {context}" if context else ""
        
        prompt = f"""Escreve uma carta do personagem {sender} para {recipient} do livro {book_ref}.

TOM DA CARTA: {tone}{context_instruction}

INSTRUÇÕES:
1. A carta deve ser escrita na voz e estilo do personagem {sender}
2. Usa o vocabulário, expressões e forma de falar característica do personagem
3. Refere eventos, memórias ou situações do livro quando apropriado
4. A carta deve refletir a relação entre os dois personagens
5. Inclui emoções genuínas e detalhes pessoais
6. O tom deve ser {tone}
7. A carta deve ter um início, desenvolvimento e conclusão naturais

Responde APENAS em JSON válido com esta estrutura:
{{
    "book_title": "{title}",
    "sender": {{
        "name": "{sender}",
        "relationship_to_recipient": "descrição da relação"
    }},
    "recipient": {{
        "name": "{recipient}"
    }},
    "letter": {{
        "greeting": "Saudação inicial (ex: Querido/a X, Caro/a X)",
        "opening": "Parágrafo de abertura",
        "body": [
            "Parágrafo 1 do corpo da carta",
            "Parágrafo 2 do corpo da carta",
            "Parágrafo 3 do corpo da carta"
        ],
        "closing": "Parágrafo de encerramento",
        "signature": "Despedida e assinatura",
        "postscript": "P.S. opcional (pode ser null)"
    }},
    "letter_metadata": {{
        "tone": "{tone}",
        "emotional_weight": "leve/moderado/intenso",
        "key_themes": ["tema1", "tema2"],
        "referenced_events": ["evento do livro mencionado"]
    }}
}}

Responde em {language}. Sê criativo e fiel ao personagem!"""

        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        content = response.text.strip()
        
        # Parse JSON response
        import re
        content = re.sub(r'^```json\s*', '', content)
        content = re.sub(r'^```\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        
        try:
            letter_data = json.loads(content)
        except json.JSONDecodeError:
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                letter_data = json.loads(json_match.group())
            else:
                return jsonify({'success': False, 'error': 'Erro ao processar resposta da IA'}), 500
        
        # Update usage count
        if current_user.is_authenticated:
            current_user.usage_count += 1
            db.session.commit()
        
        return jsonify({
            'success': True,
            'data': letter_data
        })
        
    except Exception as e:
        logger.warning(f"Character letter error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/character-diary', methods=['POST'])
def character_diary():
    """Generate secret diary entries from a character's perspective"""
    try:
        data = request.get_json() or {}
        title = (data.get('title') or '').strip()
        author = (data.get('author') or '').strip()
        character = (data.get('character') or '').strip()
        num_entries = min(int(data.get('num_entries', 5)), 8)
        language = data.get('language', 'Português')
        
        if not title:
            return jsonify({'success': False, 'error': 'Título é obrigatório'}), 400
        if not character:
            return jsonify({'success': False, 'error': 'Personagem é obrigatório'}), 400
        
        # Check usage limits
        if current_user.is_authenticated:
            plan = current_user.plan or 'free'
            limits = {'free': 5, 'pro': 100, 'premium': 500}
            limit = limits.get(plan, 5)
            
            if current_user.usage_count >= limit:
                return jsonify({
                    'success': False, 
                    'error': f'Limite de {limit} análises atingido. Faça upgrade do plano.'
                }), 429
        
        book_ref = f'"{title}"' + (f' de {author}' if author else '')
        
        prompt = f"""Cria {num_entries} entradas de diário secreto do personagem {character} do livro {book_ref}.

INSTRUÇÕES:
1. Cada entrada deve corresponder a um momento-chave da história do personagem
2. Escreve na primeira pessoa, como se fosse o próprio personagem
3. Usa o vocabulário, expressões e forma de pensar característica do personagem
4. Inclui pensamentos íntimos, medos, esperanças e reflexões que o personagem nunca partilharia publicamente
5. Cada entrada deve ter uma data/momento identificável da narrativa
6. Mostra a evolução emocional do personagem ao longo das entradas
7. Inclui detalhes pessoais e observações sobre outros personagens
8. As entradas devem revelar o lado mais humano e vulnerável do personagem

Responde APENAS em JSON válido com esta estrutura:
{{
    "book_title": "{title}",
    "character": {{
        "name": "{character}",
        "description": "Breve descrição do personagem",
        "diary_style": "Descrição do estilo de escrita do diário (ex: formal, emotivo, poético, pragmático)"
    }},
    "diary_entries": [
        {{
            "entry_number": 1,
            "date_context": "Momento/data na narrativa (ex: 'Noite antes da batalha', 'Primeiro dia em Hogwarts')",
            "mood": "Estado emocional (ex: ansioso, esperançoso, devastado, determinado)",
            "mood_emoji": "emoji que representa o humor",
            "title": "Título opcional da entrada",
            "content": "Texto completo da entrada do diário (3-5 parágrafos)",
            "secret_revealed": "Um segredo ou pensamento íntimo revelado nesta entrada",
            "mentioned_characters": ["personagens mencionados na entrada"]
        }}
    ],
    "diary_metadata": {{
        "emotional_journey": "Descrição da jornada emocional ao longo das entradas",
        "recurring_themes": ["tema1", "tema2"],
        "character_growth": "Como o personagem evolui ao longo das entradas"
    }}
}}

Responde em {language}. Sê criativo e profundamente fiel à voz interior do personagem!"""

        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        content = response.text.strip()
        
        # Parse JSON response
        import re
        content = re.sub(r'^```json\s*', '', content)
        content = re.sub(r'^```\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        
        try:
            diary_data = json.loads(content)
        except json.JSONDecodeError:
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                diary_data = json.loads(json_match.group())
            else:
                return jsonify({'success': False, 'error': 'Erro ao processar resposta da IA'}), 500
        
        # Update usage count
        if current_user.is_authenticated:
            current_user.usage_count += 1
            db.session.commit()
        
        return jsonify({
            'success': True,
            'data': diary_data
        })
        
    except Exception as e:
        logger.warning(f"Character diary error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/deleted-scenes', methods=['POST'])
def deleted_scenes():
    """Generate scenes that could have existed but aren't in the book"""
    try:
        data = request.get_json() or {}
        title = (data.get('title') or '').strip()
        author = (data.get('author') or '').strip()
        num_scenes = min(int(data.get('num_scenes', 3)), 5)
        scene_type = (data.get('scene_type') or 'mixed').strip()
        language = data.get('language', 'Português')
        
        if not title:
            return jsonify({'success': False, 'error': 'Título é obrigatório'}), 400
        
        # Check usage limits
        if current_user.is_authenticated:
            plan = current_user.plan or 'free'
            limits = {'free': 5, 'pro': 100, 'premium': 500}
            limit = limits.get(plan, 5)
            
            if current_user.usage_count >= limit:
                return jsonify({
                    'success': False, 
                    'error': f'Limite de {limit} análises atingido. Faça upgrade do plano.'
                }), 429
        
        book_ref = f'"{title}"' + (f' de {author}' if author else '')
        
        scene_type_instruction = ""
        if scene_type == 'romantic':
            scene_type_instruction = "Foca em cenas românticas ou de desenvolvimento de relações."
        elif scene_type == 'action':
            scene_type_instruction = "Foca em cenas de ação, aventura ou conflito."
        elif scene_type == 'comedy':
            scene_type_instruction = "Foca em cenas humorísticas ou momentos leves."
        elif scene_type == 'dramatic':
            scene_type_instruction = "Foca em cenas dramáticas e emocionalmente intensas."
        elif scene_type == 'backstory':
            scene_type_instruction = "Foca em cenas de backstory e passado dos personagens."
        
        prompt = f"""Cria {num_scenes} "cenas deletadas" do livro {book_ref} - cenas que poderiam ter existido mas não estão no livro original.

{scene_type_instruction}

INSTRUÇÕES:
1. Cada cena deve ser coerente com o universo, personagens e tom do livro
2. As cenas devem preencher lacunas narrativas ou explorar momentos "off-screen"
3. Mantém o estilo de escrita do autor original
4. Inclui diálogos autênticos dos personagens
5. Cada cena deve ter um propósito narrativo claro
6. As cenas devem parecer genuínas, como se realmente tivessem sido cortadas do livro

Responde APENAS em JSON válido com esta estrutura:
{{
    "book_title": "{title}",
    "deleted_scenes": [
        {{
            "scene_number": 1,
            "title": "Título da cena",
            "placement": "Onde esta cena se encaixaria na narrativa (ex: 'Entre o capítulo 5 e 6', 'Antes do clímax')",
            "characters_involved": ["personagem1", "personagem2"],
            "setting": "Local e momento onde a cena acontece",
            "scene_type": "romântica/ação/comédia/dramática/backstory",
            "why_deleted": "Razão fictícia pela qual a cena foi 'cortada' (ex: 'Atrasava o ritmo', 'Revelava demais')",
            "content": "Texto completo da cena com narração e diálogos (3-5 parágrafos)",
            "impact_if_included": "Como esta cena teria afetado a história se incluída",
            "emotional_tone": "Tom emocional da cena"
        }}
    ],
    "director_notes": {{
        "overall_theme": "Tema comum das cenas deletadas",
        "what_they_reveal": "O que estas cenas revelam sobre os personagens/história",
        "recommendation": "Recomendação sobre se deveriam ter sido incluídas"
    }}
}}

Responde em {language}. Sê criativo e fiel ao estilo do livro original!"""

        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        content = response.text.strip()
        
        # Parse JSON response
        import re
        content = re.sub(r'^```json\s*', '', content)
        content = re.sub(r'^```\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        
        try:
            scenes_data = json.loads(content)
        except json.JSONDecodeError:
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                scenes_data = json.loads(json_match.group())
            else:
                return jsonify({'success': False, 'error': 'Erro ao processar resposta da IA'}), 500
        
        # Update usage count
        if current_user.is_authenticated:
            current_user.usage_count += 1
            db.session.commit()
        
        return jsonify({
            'success': True,
            'data': scenes_data
        })
        
    except Exception as e:
        logger.warning(f"Deleted scenes error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/book-glossary', methods=['POST'])
def book_glossary():
    """Generate automatic glossary with contextual definitions"""
    try:
        data = request.get_json() or {}
        title = (data.get('title') or '').strip()
        author = (data.get('author') or '').strip()
        category = (data.get('category') or 'all').strip()
        language = data.get('language', 'Português')
        
        if not title:
            return jsonify({'success': False, 'error': 'Título é obrigatório'}), 400
        
        # Check usage limits
        if current_user.is_authenticated:
            plan = current_user.plan or 'free'
            limits = {'free': 5, 'pro': 100, 'premium': 500}
            limit = limits.get(plan, 5)
            
            if current_user.usage_count >= limit:
                return jsonify({
                    'success': False, 
                    'error': f'Limite de {limit} análises atingido. Faça upgrade do plano.'
                }), 429
        
        book_ref = f'"{title}"' + (f' de {author}' if author else '')
        
        category_instruction = ""
        if category == 'historical':
            category_instruction = "Foca em termos históricos, datas, eventos e figuras históricas."
        elif category == 'literary':
            category_instruction = "Foca em termos literários, técnicas narrativas e referências culturais."
        elif category == 'scientific':
            category_instruction = "Foca em termos científicos, técnicos e conceitos especializados."
        elif category == 'mythological':
            category_instruction = "Foca em referências mitológicas, lendas e simbolismo."
        elif category == 'geographical':
            category_instruction = "Foca em locais, geografia e contexto espacial."
        elif category == 'linguistic':
            category_instruction = "Foca em expressões arcaicas, idiomáticas e vocabulário específico."
        
        prompt = f"""Cria um glossário automático para o livro {book_ref} com termos difíceis, históricos ou especializados que um leitor pode não conhecer.

{category_instruction}

INSTRUÇÕES:
1. Identifica 12-15 termos importantes do livro que merecem explicação
2. Para cada termo, fornece uma definição contextualizada ao livro
3. Explica porque o termo é relevante para a compreensão da obra
4. Inclui a categoria do termo (histórico, literário, científico, etc.)
5. Se aplicável, indica onde o termo aparece ou é mais relevante no livro
6. Ordena os termos por ordem alfabética

Responde APENAS em JSON válido com esta estrutura:
{{
    "book_title": "{title}",
    "glossary_info": {{
        "total_terms": 15,
        "categories_covered": ["histórico", "literário", "científico"],
        "difficulty_level": "intermediário/avançado"
    }},
    "terms": [
        {{
            "term": "Nome do termo",
            "pronunciation": "Pronúncia fonética (se relevante)",
            "category": "histórico/literário/científico/mitológico/geográfico/linguístico",
            "definition": "Definição geral do termo",
            "context_in_book": "Como o termo é usado ou relevante neste livro específico",
            "example_usage": "Exemplo de uso ou citação do livro (se aplicável)",
            "related_terms": ["termo relacionado 1", "termo relacionado 2"],
            "importance": "alta/média/baixa"
        }}
    ],
    "reading_tips": {{
        "historical_context": "Contexto histórico importante para entender o livro",
        "recommended_knowledge": "Conhecimentos prévios úteis para a leitura",
        "common_misconceptions": "Equívocos comuns sobre termos do livro"
    }}
}}

Responde em {language}. Sê preciso e educativo nas definições!"""

        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        content = response.text.strip()
        
        # Parse JSON response
        import re
        content = re.sub(r'^```json\s*', '', content)
        content = re.sub(r'^```\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        
        try:
            glossary_data = json.loads(content)
        except json.JSONDecodeError:
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                glossary_data = json.loads(json_match.group())
            else:
                return jsonify({'success': False, 'error': 'Erro ao processar resposta da IA'}), 500
        
        # Update usage count
        if current_user.is_authenticated:
            current_user.usage_count += 1
            db.session.commit()
        
        return jsonify({
            'success': True,
            'data': glossary_data
        })
        
    except Exception as e:
        logger.warning(f"Book glossary error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/historical-context', methods=['POST'])
def historical_context():
    """Generate expanded historical context for a book's time period"""
    try:
        data = request.get_json() or {}
        title = (data.get('title') or '').strip()
        author = (data.get('author') or '').strip()
        focus_area = (data.get('focus_area') or 'all').strip()
        language = data.get('language', 'Português')
        
        if not title:
            return jsonify({'success': False, 'error': 'Título é obrigatório'}), 400
        
        # Check usage limits
        if current_user.is_authenticated:
            plan = current_user.plan or 'free'
            limits = {'free': 5, 'pro': 100, 'premium': 500}
            limit = limits.get(plan, 5)
            
            if current_user.usage_count >= limit:
                return jsonify({
                    'success': False, 
                    'error': f'Limite de {limit} análises atingido. Faça upgrade do plano.'
                }), 429
        
        book_ref = f'"{title}"' + (f' de {author}' if author else '')
        
        focus_instruction = ""
        if focus_area == 'political':
            focus_instruction = "Foca em eventos políticos, guerras, revoluções e mudanças de poder."
        elif focus_area == 'social':
            focus_instruction = "Foca em movimentos sociais, costumes, classes sociais e vida quotidiana."
        elif focus_area == 'cultural':
            focus_instruction = "Foca em arte, literatura, música, filosofia e movimentos culturais."
        elif focus_area == 'scientific':
            focus_instruction = "Foca em descobertas científicas, invenções e avanços tecnológicos."
        elif focus_area == 'economic':
            focus_instruction = "Foca em economia, comércio, industrialização e condições de trabalho."
        
        prompt = f"""Cria um contexto histórico expandido para o livro {book_ref}, detalhando os eventos reais da época em que a história se passa.

{focus_instruction}

INSTRUÇÕES:
1. Identifica o período histórico em que o livro se passa
2. Lista os principais eventos históricos reais dessa época
3. Explica como esses eventos influenciam ou se relacionam com a narrativa
4. Inclui figuras históricas relevantes
5. Descreve o contexto social, político e cultural
6. Mostra como o autor usou a história real na ficção

Responde APENAS em JSON válido com esta estrutura:
{{
    "book_title": "{title}",
    "time_period": {{
        "start_year": "ano de início",
        "end_year": "ano de fim",
        "era_name": "Nome da era/período (ex: Era Vitoriana, Renascimento)",
        "location": "Local/região principal"
    }},
    "historical_events": [
        {{
            "event_name": "Nome do evento histórico",
            "date": "Data ou período",
            "description": "Descrição do evento",
            "relevance_to_book": "Como este evento se relaciona com a história do livro",
            "impact_level": "alto/médio/baixo",
            "category": "político/social/cultural/científico/económico/militar"
        }}
    ],
    "historical_figures": [
        {{
            "name": "Nome da figura histórica",
            "role": "Papel/cargo",
            "period": "Período de atividade",
            "connection_to_story": "Conexão com a narrativa (direta/indireta/contextual)",
            "brief_bio": "Breve biografia relevante"
        }}
    ],
    "social_context": {{
        "class_structure": "Descrição da estrutura de classes sociais",
        "daily_life": "Como era a vida quotidiana",
        "gender_roles": "Papéis de género da época",
        "education": "Sistema educacional",
        "religion": "Papel da religião"
    }},
    "cultural_context": {{
        "art_movements": "Movimentos artísticos da época",
        "literature": "Tendências literárias",
        "music": "Música e entretenimento",
        "philosophy": "Correntes filosóficas"
    }},
    "how_author_used_history": {{
        "historical_accuracy": "Nível de precisão histórica do autor",
        "creative_liberties": "Liberdades criativas tomadas",
        "themes_from_era": "Temas da época explorados no livro"
    }},
    "recommended_reading": [
        {{
            "title": "Título de livro/recurso recomendado",
            "type": "livro/documentário/artigo",
            "why_relevant": "Porque é relevante para entender melhor"
        }}
    ]
}}

Responde em {language}. Sê historicamente preciso e educativo!"""

        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        content = response.text.strip()
        
        # Parse JSON response
        import re
        content = re.sub(r'^```json\s*', '', content)
        content = re.sub(r'^```\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        
        try:
            context_data = json.loads(content)
        except json.JSONDecodeError:
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                context_data = json.loads(json_match.group())
            else:
                return jsonify({'success': False, 'error': 'Erro ao processar resposta da IA'}), 500
        
        # Update usage count
        if current_user.is_authenticated:
            current_user.usage_count += 1
            db.session.commit()
        
        return jsonify({
            'success': True,
            'data': context_data
        })
        
    except Exception as e:
        logger.warning(f"Historical context error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/study-guide', methods=['POST'])
def study_guide():
    """Generate structured study guide for students"""
    try:
        data = request.get_json() or {}
        title = (data.get('title') or '').strip()
        author = (data.get('author') or '').strip()
        level = (data.get('level') or 'secondary').strip()
        language = data.get('language', 'Português')
        
        if not title:
            return jsonify({'success': False, 'error': 'Título é obrigatório'}), 400
        
        # Check usage limits
        if current_user.is_authenticated:
            plan = current_user.plan or 'free'
            limits = {'free': 5, 'pro': 100, 'premium': 500}
            limit = limits.get(plan, 5)
            
            if current_user.usage_count >= limit:
                return jsonify({
                    'success': False, 
                    'error': f'Limite de {limit} análises atingido. Faça upgrade do plano.'
                }), 429
        
        book_ref = f'"{title}"' + (f' de {author}' if author else '')
        
        level_instruction = ""
        if level == 'basic':
            level_instruction = "Adapta para alunos do ensino básico (10-14 anos). Usa linguagem simples e exemplos claros."
        elif level == 'secondary':
            level_instruction = "Adapta para alunos do ensino secundário (15-18 anos). Inclui análise literária moderada."
        elif level == 'university':
            level_instruction = "Adapta para estudantes universitários. Inclui análise crítica aprofundada e referências académicas."
        
        prompt = f"""Cria um guia de estudo completo e estruturado para o livro {book_ref}.

{level_instruction}

INSTRUÇÕES:
1. Cria um resumo executivo claro e conciso
2. Identifica os pontos-chave que um estudante deve memorizar
3. Analisa personagens principais com suas características
4. Explica os temas centrais da obra
5. Fornece perguntas de estudo para revisão
6. Inclui citações importantes com análise
7. Sugere tópicos para redações/ensaios

Responde APENAS em JSON válido com esta estrutura:
{{
    "book_title": "{title}",
    "author": "{author}",
    "study_level": "{level}",
    "executive_summary": {{
        "overview": "Resumo geral do livro em 3-4 frases",
        "genre": "Género literário",
        "publication_year": "Ano de publicação",
        "setting": "Cenário temporal e espacial",
        "narrative_style": "Estilo narrativo (1ª pessoa, 3ª pessoa, etc.)"
    }},
    "key_points": [
        {{
            "point": "Ponto-chave importante",
            "explanation": "Explicação breve",
            "importance": "alta/média"
        }}
    ],
    "characters": [
        {{
            "name": "Nome do personagem",
            "role": "protagonista/antagonista/secundário",
            "description": "Descrição física e psicológica",
            "arc": "Evolução do personagem",
            "key_quotes": ["citação relevante do personagem"],
            "relationships": "Relações com outros personagens"
        }}
    ],
    "themes": [
        {{
            "theme": "Nome do tema",
            "description": "Descrição do tema",
            "examples_in_book": "Exemplos de como aparece no livro",
            "relevance": "Relevância atual do tema"
        }}
    ],
    "plot_structure": {{
        "exposition": "Apresentação inicial",
        "rising_action": "Desenvolvimento/conflito crescente",
        "climax": "Clímax da história",
        "falling_action": "Ação decrescente",
        "resolution": "Resolução/desfecho"
    }},
    "literary_devices": [
        {{
            "device": "Nome do recurso literário",
            "example": "Exemplo do livro",
            "effect": "Efeito pretendido"
        }}
    ],
    "important_quotes": [
        {{
            "quote": "Citação do livro",
            "speaker": "Quem disse/narrador",
            "context": "Contexto da citação",
            "analysis": "Análise do significado"
        }}
    ],
    "study_questions": [
        {{
            "question": "Pergunta de estudo",
            "type": "compreensão/análise/reflexão",
            "suggested_answer_points": ["ponto 1", "ponto 2"]
        }}
    ],
    "essay_topics": [
        {{
            "topic": "Tema para redação",
            "difficulty": "fácil/médio/difícil",
            "key_points_to_cover": ["ponto 1", "ponto 2"]
        }}
    ],
    "vocabulary": [
        {{
            "word": "Palavra/expressão",
            "definition": "Definição",
            "context": "Contexto no livro"
        }}
    ]
}}

Responde em {language}. Sê educativo e útil para estudantes!"""

        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        content = response.text.strip()
        
        # Parse JSON response
        import re
        content = re.sub(r'^```json\s*', '', content)
        content = re.sub(r'^```\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        
        try:
            guide_data = json.loads(content)
        except json.JSONDecodeError:
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                guide_data = json.loads(json_match.group())
            else:
                return jsonify({'success': False, 'error': 'Erro ao processar resposta da IA'}), 500
        
        # Update usage count
        if current_user.is_authenticated:
            current_user.usage_count += 1
            db.session.commit()
        
        return jsonify({
            'success': True,
            'data': guide_data
        })
        
    except Exception as e:
        logger.warning(f"Study guide error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/geographic-map', methods=['POST'])
def geographic_map():
    """Generate geographic locations of events in a book"""
    try:
        data = request.get_json() or {}
        title = (data.get('title') or '').strip()
        author = (data.get('author') or '').strip()
        language = data.get('language', 'Português')
        
        if not title:
            return jsonify({'success': False, 'error': 'Título é obrigatório'}), 400
        
        # Check usage limits
        if current_user.is_authenticated:
            plan = current_user.plan or 'free'
            limits = {'free': 5, 'pro': 100, 'premium': 500}
            limit = limits.get(plan, 5)
            
            if current_user.usage_count >= limit:
                return jsonify({
                    'success': False, 
                    'error': f'Limite de {limit} análises atingido. Faça upgrade do plano.'
                }), 429
        
        book_ref = f'"{title}"' + (f' de {author}' if author else '')
        
        prompt = f"""Identifica todas as localizações geográficas reais mencionadas ou onde ocorrem eventos no livro {book_ref}.

INSTRUÇÕES:
1. Lista todos os locais reais (cidades, países, regiões) onde a história se passa
2. Para cada local, fornece coordenadas geográficas aproximadas
3. Descreve os eventos importantes que ocorrem em cada local
4. Indica se o local é real ou fictício baseado em lugar real
5. Organiza os locais por ordem de aparição ou importância na narrativa

Responde APENAS em JSON válido com esta estrutura:
{{
    "book_title": "{title}",
    "is_geographically_based": true,
    "main_region": "Região/país principal onde se passa a história",
    "time_period": "Época em que se passa",
    "locations": [
        {{
            "name": "Nome do local",
            "type": "cidade/país/região/edifício/rua",
            "real_or_fictional": "real/fictício/baseado em real",
            "coordinates": {{
                "lat": 41.1579,
                "lng": -8.6291
            }},
            "country": "País",
            "description": "Descrição do local no contexto do livro",
            "events": [
                {{
                    "event": "Descrição do evento",
                    "importance": "alta/média/baixa",
                    "chapter": "Capítulo ou momento (se conhecido)"
                }}
            ],
            "characters_present": ["Personagem 1", "Personagem 2"],
            "atmosphere": "Descrição da atmosfera/ambiente do local",
            "historical_note": "Nota histórica sobre o local (se relevante)"
        }}
    ],
    "journey": {{
        "has_journey": true,
        "journey_type": "linear/circular/múltiplo",
        "total_distance_km": "Distância aproximada percorrida",
        "route_description": "Descrição do percurso dos personagens"
    }},
    "geographic_themes": [
        {{
            "theme": "Tema geográfico (ex: contraste urbano/rural)",
            "description": "Como este tema aparece no livro"
        }}
    ],
    "map_notes": "Notas adicionais sobre a geografia do livro"
}}

Se o livro se passa num mundo completamente fictício sem base geográfica real, indica is_geographically_based como false e fornece uma explicação.

Responde em {language}. Sê preciso com as coordenadas geográficas!"""

        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        content = response.text.strip()
        
        # Parse JSON response
        import re
        content = re.sub(r'^```json\s*', '', content)
        content = re.sub(r'^```\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        
        try:
            map_data = json.loads(content)
        except json.JSONDecodeError:
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                map_data = json.loads(json_match.group())
            else:
                return jsonify({'success': False, 'error': 'Erro ao processar resposta da IA'}), 500
        
        # Update usage count
        if current_user.is_authenticated:
            current_user.usage_count += 1
            db.session.commit()
        
        return jsonify({
            'success': True,
            'data': map_data
        })
        
    except Exception as e:
        logger.warning(f"Geographic map error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/rewrite-scene', methods=['POST'])
def rewrite_scene():
    """Rewrite a scene from a book in a different style"""
    try:
        data = request.get_json() or {}
        title = (data.get('title') or '').strip()
        author = (data.get('author') or '').strip()
        scene_description = (data.get('scene_description') or '').strip()
        new_style = (data.get('new_style') or 'comedy').strip()
        language = data.get('language', 'Português')
        
        if not title:
            return jsonify({'success': False, 'error': 'Título é obrigatório'}), 400
        if not scene_description:
            return jsonify({'success': False, 'error': 'Descrição da cena é obrigatória'}), 400
        
        # Check usage limits
        if current_user.is_authenticated:
            plan = current_user.plan or 'free'
            limits = {'free': 5, 'pro': 100, 'premium': 500}
            limit = limits.get(plan, 5)
            
            if current_user.usage_count >= limit:
                return jsonify({
                    'success': False, 
                    'error': f'Limite de {limit} análises atingido. Faça upgrade do plano.'
                }), 429
        
        book_ref = f'"{title}"' + (f' de {author}' if author else '')
        
        style_instructions = {
            'comedy': 'Reescreve como uma comédia hilariante com humor, piadas, situações absurdas e timing cómico. Adiciona mal-entendidos engraçados e diálogos espirituosos.',
            'horror': 'Reescreve como terror psicológico com atmosfera sinistra, tensão crescente, elementos sobrenaturais ou ameaçadores. Cria medo e suspense.',
            'romance': 'Reescreve como romance apaixonado com tensão romântica, olhares intensos, emoções profundas e momentos de conexão íntima entre personagens.',
            'action': 'Reescreve como cena de ação intensa com adrenalina, movimento rápido, perigo iminente e sequências cinematográficas emocionantes.',
            'noir': 'Reescreve no estilo film noir com narração cínica, atmosfera sombria, personagens moralmente ambíguos e diálogos afiados.',
            'fairy_tale': 'Reescreve como conto de fadas encantado com magia, elementos fantásticos, linguagem poética e moral da história.',
            'sci_fi': 'Reescreve como ficção científica futurista com tecnologia avançada, conceitos científicos e ambientação espacial ou distópica.',
            'musical': 'Reescreve como se fosse um musical da Broadway com momentos onde personagens cantam, coreografias descritas e números musicais.',
            'documentary': 'Reescreve como documentário narrado com tom informativo, factos, entrevistas fictícias e análise objetiva dos eventos.',
            'shakespearean': 'Reescreve no estilo de Shakespeare com linguagem elisabetana, monólogos dramáticos, versos poéticos e tragédia clássica.'
        }
        
        style_instruction = style_instructions.get(new_style, style_instructions['comedy'])
        
        style_names = {
            'comedy': 'Comédia',
            'horror': 'Terror',
            'romance': 'Romance',
            'action': 'Ação',
            'noir': 'Film Noir',
            'fairy_tale': 'Conto de Fadas',
            'sci_fi': 'Ficção Científica',
            'musical': 'Musical',
            'documentary': 'Documentário',
            'shakespearean': 'Shakespeariano'
        }
        
        prompt = f"""Reescreve uma cena do livro {book_ref} num estilo completamente diferente.

CENA ORIGINAL A REESCREVER:
{scene_description}

NOVO ESTILO: {style_names.get(new_style, 'Comédia')}

INSTRUÇÕES:
{style_instruction}

REGRAS:
1. Mantém os mesmos personagens e o mesmo evento central
2. Transforma completamente o tom, atmosfera e abordagem
3. Adapta os diálogos ao novo estilo
4. Adiciona elementos típicos do género escolhido
5. Mantém a essência da cena mas com uma nova perspetiva
6. Sê criativo e divertido na transformação

Responde APENAS em JSON válido com esta estrutura:
{{
    "book_title": "{title}",
    "original_scene": "{scene_description}",
    "new_style": "{new_style}",
    "style_name": "{style_names.get(new_style, 'Comédia')}",
    "rewritten_scene": {{
        "title": "Título criativo para a cena reescrita",
        "setting": "Descrição do cenário adaptado ao novo estilo",
        "content": "A cena completa reescrita no novo estilo (mínimo 300 palavras)",
        "key_changes": [
            "Mudança principal 1",
            "Mudança principal 2",
            "Mudança principal 3"
        ],
        "style_elements_used": [
            "Elemento do género usado 1",
            "Elemento do género usado 2"
        ]
    }},
    "comparison": {{
        "original_tone": "Tom da cena original",
        "new_tone": "Tom da cena reescrita",
        "what_was_preserved": "O que foi mantido da cena original",
        "what_was_transformed": "O que foi transformado"
    }},
    "fun_fact": "Uma observação divertida sobre a transformação"
}}

Responde em {language}. Sê criativo e faz uma transformação memorável!"""

        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        content = response.text.strip()
        
        # Parse JSON response
        import re
        content = re.sub(r'^```json\s*', '', content)
        content = re.sub(r'^```\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        
        try:
            scene_data = json.loads(content)
        except json.JSONDecodeError:
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                scene_data = json.loads(json_match.group())
            else:
                return jsonify({'success': False, 'error': 'Erro ao processar resposta da IA'}), 500
        
        # Update usage count
        if current_user.is_authenticated:
            current_user.usage_count += 1
            db.session.commit()
        
        return jsonify({
            'success': True,
            'data': scene_data
        })
        
    except Exception as e:
        logger.warning(f"Rewrite scene error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/alternative-perspective', methods=['POST'])
def alternative_perspective():
    """Retell a scene from another character's point of view"""
    try:
        data = request.get_json() or {}
        title = (data.get('title') or '').strip()
        author = (data.get('author') or '').strip()
        scene_description = (data.get('scene_description') or '').strip()
        character_name = (data.get('character_name') or '').strip()
        language = data.get('language', 'Português')
        
        if not title:
            return jsonify({'success': False, 'error': 'Título é obrigatório'}), 400
        if not scene_description:
            return jsonify({'success': False, 'error': 'Descrição da cena é obrigatória'}), 400
        if not character_name:
            return jsonify({'success': False, 'error': 'Nome do personagem é obrigatório'}), 400
        
        # Check usage limits
        if current_user.is_authenticated:
            plan = current_user.plan or 'free'
            limits = {'free': 5, 'pro': 100, 'premium': 500}
            limit = limits.get(plan, 5)
            
            if current_user.usage_count >= limit:
                return jsonify({
                    'success': False, 
                    'error': f'Limite de {limit} análises atingido. Faça upgrade do plano.'
                }), 429
        
        book_ref = f'"{title}"' + (f' de {author}' if author else '')
        
        prompt = f"""Reconta uma cena do livro {book_ref} do ponto de vista de um personagem diferente.

CENA ORIGINAL:
{scene_description}

PERSONAGEM PARA A NOVA PERSPETIVA: {character_name}

INSTRUÇÕES:
1. Reconta a mesma cena, mas agora vista pelos olhos de {character_name}
2. Usa a primeira pessoa (eu, mim, meu)
3. Inclui os pensamentos internos, emoções e perceções deste personagem
4. Mostra o que este personagem vê, ouve e sente durante a cena
5. Revela informações que só este personagem saberia
6. Mantém a personalidade e voz única do personagem
7. Adiciona detalhes que o narrador original não teria acesso

Responde APENAS em JSON válido com esta estrutura:
{{
    "book_title": "{title}",
    "original_scene": "{scene_description}",
    "character": {{
        "name": "{character_name}",
        "role_in_scene": "Papel do personagem na cena original",
        "relationship_to_protagonist": "Relação com o protagonista",
        "emotional_state_before": "Estado emocional antes da cena"
    }},
    "retold_scene": {{
        "title": "Título criativo para a cena recontada",
        "opening_thoughts": "Pensamentos do personagem no início da cena",
        "content": "A cena completa recontada na primeira pessoa (mínimo 400 palavras)",
        "closing_thoughts": "Reflexões finais do personagem após a cena",
        "internal_conflict": "Conflito interno que o personagem experimenta"
    }},
    "new_revelations": [
        {{
            "revelation": "Algo novo que descobrimos com esta perspetiva",
            "significance": "Porque é significativo"
        }}
    ],
    "hidden_emotions": [
        {{
            "emotion": "Emoção escondida",
            "trigger": "O que causou esta emoção",
            "how_hidden": "Como o personagem escondeu isto dos outros"
        }}
    ],
    "what_others_missed": "O que os outros personagens não perceberam sobre {character_name} nesta cena",
    "comparison": {{
        "original_narrator": "Quem narra originalmente",
        "what_changes": "O que muda com esta nova perspetiva",
        "new_understanding": "Nova compreensão que ganhamos"
    }},
    "character_voice": {{
        "speech_patterns": "Padrões de fala característicos",
        "unique_observations": "Observações únicas deste personagem",
        "biases": "Preconceitos ou vieses do personagem que afetam a narrativa"
    }}
}}

Responde em {language}. Sê fiel à voz e personalidade do personagem!"""

        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        content = response.text.strip()
        
        # Parse JSON response
        import re
        content = re.sub(r'^```json\s*', '', content)
        content = re.sub(r'^```\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        
        try:
            perspective_data = json.loads(content)
        except json.JSONDecodeError:
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                perspective_data = json.loads(json_match.group())
            else:
                return jsonify({'success': False, 'error': 'Erro ao processar resposta da IA'}), 500
        
        # Update usage count
        if current_user.is_authenticated:
            current_user.usage_count += 1
            db.session.commit()
        
        return jsonify({
            'success': True,
            'data': perspective_data
        })
        
    except Exception as e:
        logger.warning(f"Alternative perspective error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/prequel-generator', methods=['POST'])
def prequel_generator():
    """Generate what happened before the book started"""
    try:
        data = request.get_json() or {}
        title = (data.get('title') or '').strip()
        author = (data.get('author') or '').strip()
        focus = (data.get('focus') or 'all').strip()
        language = data.get('language', 'Português')
        
        if not title:
            return jsonify({'success': False, 'error': 'Título é obrigatório'}), 400
        
        # Check usage limits
        if current_user.is_authenticated:
            plan = current_user.plan or 'free'
            limits = {'free': 5, 'pro': 100, 'premium': 500}
            limit = limits.get(plan, 5)
            
            if current_user.usage_count >= limit:
                return jsonify({
                    'success': False, 
                    'error': f'Limite de {limit} análises atingido. Faça upgrade do plano.'
                }), 429
        
        book_ref = f'"{title}"' + (f' de {author}' if author else '')
        
        focus_instructions = {
            'all': 'Cobre todos os aspectos: protagonista, antagonista, mundo e eventos que levaram ao início do livro.',
            'protagonist': 'Foca na história de vida do protagonista antes do livro começar.',
            'antagonist': 'Foca na origem e motivações do antagonista/vilão.',
            'world': 'Foca na história do mundo/cenário antes dos eventos do livro.',
            'relationships': 'Foca em como as relações entre personagens se formaram.'
        }
        
        focus_instruction = focus_instructions.get(focus, focus_instructions['all'])
        
        prompt = f"""Cria uma história prequel para o livro {book_ref}, explicando o que aconteceu antes do livro começar.

FOCO: {focus_instruction}

INSTRUÇÕES:
1. Imagina os eventos que levaram ao início do livro
2. Desenvolve as origens dos personagens principais
3. Explica como o mundo/cenário chegou ao estado em que está no início do livro
4. Cria conexões lógicas com os eventos do livro original
5. Mantém consistência com o tom e estilo do autor original

Responde APENAS em JSON válido com esta estrutura:
{{
    "book_title": "{title}",
    "prequel_title": "Título criativo para a prequel",
    "time_before": "Quanto tempo antes do livro se passa esta história",
    "synopsis": "Sinopse da prequel em 2-3 parágrafos",
    "chapters": [
        {{
            "chapter_number": 1,
            "title": "Título do capítulo",
            "summary": "Resumo do que acontece neste capítulo",
            "key_events": ["Evento 1", "Evento 2"],
            "characters_involved": ["Personagem 1", "Personagem 2"]
        }}
    ],
    "character_origins": [
        {{
            "name": "Nome do personagem",
            "role_in_book": "Papel no livro original",
            "backstory": "História de origem detalhada",
            "formative_events": ["Evento formativo 1", "Evento formativo 2"],
            "how_became_who_they_are": "Como se tornou quem é no início do livro"
        }}
    ],
    "world_history": {{
        "setting": "Descrição do cenário na prequel",
        "major_events": [
            {{
                "event": "Evento histórico importante",
                "when": "Quando aconteceu",
                "impact": "Impacto nos eventos do livro"
            }}
        ],
        "how_world_changed": "Como o mundo mudou até ao início do livro"
    }},
    "seeds_of_conflict": [
        {{
            "conflict": "Semente de conflito",
            "origin": "Como começou",
            "how_grows": "Como evolui para o conflito do livro"
        }}
    ],
    "connections_to_book": [
        {{
            "element_in_book": "Elemento do livro original",
            "origin_in_prequel": "Origem na prequel",
            "significance": "Significado da conexão"
        }}
    ],
    "opening_scene": {{
        "title": "Título da cena de abertura",
        "content": "Texto narrativo da primeira cena da prequel (mínimo 200 palavras)",
        "mood": "Atmosfera da cena"
    }},
    "closing_scene": {{
        "title": "Título da cena final",
        "content": "Texto narrativo da última cena, que conecta diretamente ao início do livro (mínimo 150 palavras)",
        "transition": "Como esta cena leva ao início do livro original"
    }}
}}

Responde em {language}. Sê criativo mas mantém coerência com o livro original!"""

        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        content = response.text.strip()
        
        # Parse JSON response
        import re
        content = re.sub(r'^```json\s*', '', content)
        content = re.sub(r'^```\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        
        try:
            prequel_data = json.loads(content)
        except json.JSONDecodeError:
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                prequel_data = json.loads(json_match.group())
            else:
                return jsonify({'success': False, 'error': 'Erro ao processar resposta da IA'}), 500
        
        # Update usage count
        if current_user.is_authenticated:
            current_user.usage_count += 1
            db.session.commit()
        
        return jsonify({
            'success': True,
            'data': prequel_data
        })
        
    except Exception as e:
        logger.warning(f"Prequel generator error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/crossover', methods=['POST'])
def crossover():
    """Generate a crossover story mixing characters from two different books"""
    try:
        data = request.get_json() or {}
        book1_title = (data.get('book1_title') or '').strip()
        book1_author = (data.get('book1_author') or '').strip()
        book2_title = (data.get('book2_title') or '').strip()
        book2_author = (data.get('book2_author') or '').strip()
        scenario = (data.get('scenario') or 'meeting').strip()
        language = data.get('language', 'Português')
        
        if not book1_title or not book2_title:
            return jsonify({'success': False, 'error': 'Títulos dos dois livros são obrigatórios'}), 400
        
        # Check usage limits
        if current_user.is_authenticated:
            plan = current_user.plan or 'free'
            limits = {'free': 5, 'pro': 100, 'premium': 500}
            limit = limits.get(plan, 5)
            
            if current_user.usage_count >= limit:
                return jsonify({
                    'success': False, 
                    'error': f'Limite de {limit} análises atingido. Faça upgrade do plano.'
                }), 429
        
        book1_ref = f'"{book1_title}"' + (f' de {book1_author}' if book1_author else '')
        book2_ref = f'"{book2_title}"' + (f' de {book2_author}' if book2_author else '')
        
        scenario_instructions = {
            'meeting': 'Os personagens encontram-se pela primeira vez. Como reagiriam uns aos outros?',
            'adventure': 'Os personagens embarcam numa aventura juntos. Que desafios enfrentam?',
            'conflict': 'Os personagens entram em conflito. Quem venceria e porquê?',
            'romance': 'Desenvolve uma tensão romântica entre personagens dos dois universos.',
            'mystery': 'Os personagens trabalham juntos para resolver um mistério.',
            'comedy': 'Cria situações cómicas com os personagens fora do seu elemento.'
        }
        
        scenario_instruction = scenario_instructions.get(scenario, scenario_instructions['meeting'])
        
        prompt = f"""Cria uma história crossover misturando personagens de dois livros diferentes:

LIVRO 1: {book1_ref}
LIVRO 2: {book2_ref}

CENÁRIO: {scenario_instruction}

INSTRUÇÕES:
1. Seleciona 2-3 personagens principais de cada livro
2. Cria um cenário onde os dois universos se encontram
3. Mantém as personalidades fiéis aos livros originais
4. Desenvolve interações interessantes entre personagens
5. Cria diálogos autênticos para cada personagem
6. Explora como os diferentes mundos/regras colidem

Responde APENAS em JSON válido com esta estrutura:
{{
    "crossover_title": "Título criativo para o crossover",
    "tagline": "Frase de efeito para o crossover",
    "book1": {{
        "title": "{book1_title}",
        "characters_selected": [
            {{
                "name": "Nome do personagem",
                "role": "Papel no livro original",
                "personality_traits": ["traço1", "traço2"],
                "skills": ["habilidade1", "habilidade2"]
            }}
        ],
        "world_elements": ["Elemento do mundo 1", "Elemento 2"]
    }},
    "book2": {{
        "title": "{book2_title}",
        "characters_selected": [
            {{
                "name": "Nome do personagem",
                "role": "Papel no livro original",
                "personality_traits": ["traço1", "traço2"],
                "skills": ["habilidade1", "habilidade2"]
            }}
        ],
        "world_elements": ["Elemento do mundo 1", "Elemento 2"]
    }},
    "crossover_setup": {{
        "how_worlds_collide": "Como os dois universos se encontram",
        "setting": "Onde e quando a história se passa",
        "initial_conflict": "O que desencadeia a interação"
    }},
    "character_dynamics": [
        {{
            "character1": "Personagem do livro 1",
            "character2": "Personagem do livro 2",
            "dynamic": "aliados/rivais/romântico/mentor-aprendiz",
            "chemistry": "Descrição da química entre eles",
            "potential_conflict": "Possível fonte de conflito",
            "potential_bond": "Possível fonte de ligação"
        }}
    ],
    "story": {{
        "synopsis": "Sinopse da história crossover em 2-3 parágrafos",
        "key_scenes": [
            {{
                "scene_number": 1,
                "title": "Título da cena",
                "description": "O que acontece",
                "characters_involved": ["Personagem 1", "Personagem 2"],
                "highlight_moment": "Momento mais marcante"
            }}
        ],
        "climax": "Descrição do clímax da história",
        "resolution": "Como a história termina"
    }},
    "sample_dialogue": [
        {{
            "context": "Contexto da conversa",
            "exchanges": [
                {{
                    "character": "Nome",
                    "line": "Fala do personagem",
                    "action": "Ação ou expressão (opcional)"
                }}
            ]
        }}
    ],
    "fun_matchups": [
        {{
            "matchup": "Personagem A vs Personagem B",
            "category": "combate/debate/corrida/etc",
            "winner": "Quem venceria",
            "reasoning": "Porquê"
        }}
    ],
    "what_if_scenarios": [
        {{
            "scenario": "E se...",
            "outcome": "O que aconteceria"
        }}
    ],
    "fan_service_moments": ["Momento épico 1", "Momento épico 2"]
}}

Responde em {language}. Sê criativo e divertido!"""

        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        content = response.text.strip()
        
        # Parse JSON response
        import re
        content = re.sub(r'^```json\s*', '', content)
        content = re.sub(r'^```\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        
        try:
            crossover_data = json.loads(content)
        except json.JSONDecodeError:
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                crossover_data = json.loads(json_match.group())
            else:
                return jsonify({'success': False, 'error': 'Erro ao processar resposta da IA'}), 500
        
        # Update usage count
        if current_user.is_authenticated:
            current_user.usage_count += 1
            db.session.commit()
        
        return jsonify({
            'success': True,
            'data': crossover_data
        })
        
    except Exception as e:
        logger.warning(f"Crossover error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/quote-of-day', methods=['POST'])
def quote_of_day():
    """Generate a shareable quote image from a book"""
    try:
        data = request.get_json() or {}
        title = (data.get('title') or '').strip()
        author = (data.get('author') or '').strip()
        theme = (data.get('theme') or 'inspirational').strip()
        language = data.get('language', 'Português')
        
        if not title:
            return jsonify({'success': False, 'error': 'Título é obrigatório'}), 400
        
        # Check usage limits
        if current_user.is_authenticated:
            plan = current_user.plan or 'free'
            limits = {'free': 5, 'pro': 100, 'premium': 500}
            limit = limits.get(plan, 5)
            
            if current_user.usage_count >= limit:
                return jsonify({
                    'success': False, 
                    'error': f'Limite de {limit} análises atingido. Faça upgrade do plano.'
                }), 429
        
        book_ref = f'"{title}"' + (f' de {author}' if author else '')
        
        theme_instructions = {
            'inspirational': 'Citações inspiradoras e motivacionais que elevam o espírito.',
            'love': 'Citações sobre amor, paixão e relacionamentos.',
            'wisdom': 'Citações de sabedoria, filosofia e reflexão profunda.',
            'humor': 'Citações engraçadas, espirituosas e com humor.',
            'dark': 'Citações sombrias, melancólicas ou sobre a condição humana.',
            'courage': 'Citações sobre coragem, bravura e superação.',
            'friendship': 'Citações sobre amizade e lealdade.',
            'life': 'Citações sobre a vida, morte e o significado da existência.'
        }
        
        theme_instruction = theme_instructions.get(theme, theme_instructions['inspirational'])
        
        prompt = f"""Seleciona ou cria citações memoráveis do livro {book_ref}.

TEMA: {theme_instruction}

INSTRUÇÕES:
1. Fornece 5 citações diferentes do livro
2. Cada citação deve ser impactante e partilhável
3. Inclui o contexto de cada citação
4. Sugere cores e estilos visuais para cada citação

Responde APENAS em JSON válido com esta estrutura:
{{
    "book_title": "{title}",
    "author": "{author}",
    "theme": "{theme}",
    "quotes": [
        {{
            "quote": "A citação completa",
            "character": "Quem disse (ou 'Narrador')",
            "context": "Contexto breve da citação no livro",
            "mood": "Emoção/tom da citação",
            "visual_style": {{
                "background_gradient": ["#cor1", "#cor2"],
                "text_color": "#cor",
                "accent_color": "#cor",
                "font_style": "serif/sans-serif/script",
                "suggested_emoji": "emoji que representa a citação"
            }},
            "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3"]
        }}
    ],
    "book_aesthetic": {{
        "primary_color": "#cor principal do livro",
        "secondary_color": "#cor secundária",
        "mood": "Atmosfera geral do livro",
        "visual_elements": ["elemento visual 1", "elemento visual 2"]
    }}
}}

Responde em {language}. As citações devem ser fiéis ao livro!"""

        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        content = response.text.strip()
        
        # Parse JSON response
        import re
        content = re.sub(r'^```json\s*', '', content)
        content = re.sub(r'^```\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        
        try:
            quote_data = json.loads(content)
        except json.JSONDecodeError:
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                quote_data = json.loads(json_match.group())
            else:
                return jsonify({'success': False, 'error': 'Erro ao processar resposta da IA'}), 500
        
        # Update usage count
        if current_user.is_authenticated:
            current_user.usage_count += 1
            db.session.commit()
        
        return jsonify({
            'success': True,
            'data': quote_data
        })
        
    except Exception as e:
        logger.warning(f"Quote of day error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/sentiment-analysis', methods=['POST'])
def sentiment_analysis():
    """Analyze emotional journey throughout a book"""
    try:
        data = request.get_json() or {}
        title = (data.get('title') or '').strip()
        author = (data.get('author') or '').strip()
        language = data.get('language', 'Português')
        
        if not title:
            return jsonify({'success': False, 'error': 'Título é obrigatório'}), 400
        
        # Check usage limits
        if current_user.is_authenticated:
            plan = current_user.plan or 'free'
            limits = {'free': 5, 'pro': 100, 'premium': 500}
            limit = limits.get(plan, 5)
            
            if current_user.usage_count >= limit:
                return jsonify({
                    'success': False, 
                    'error': f'Limite de {limit} análises atingido. Faça upgrade do plano.'
                }), 429
        
        # Build prompt for sentiment analysis
        book_ref = f'"{title}"' + (f' de {author}' if author else '')
        
        prompt = f"""Analisa a jornada emocional do livro {book_ref}.

Divide o livro em 8-10 momentos/secções principais e para cada um fornece:
1. Nome da secção/momento (ex: "Início", "Conflito", "Clímax", etc.)
2. Pontuação emocional de -10 (muito negativo/triste) a +10 (muito positivo/alegre)
3. Emoções dominantes (1-3 palavras)
4. Breve descrição do que acontece (1 frase)

Responde APENAS em JSON válido com esta estrutura exata:
{{
    "book_title": "{title}",
    "overall_tone": "descrição do tom geral em 1-2 frases",
    "emotional_arc": "tipo de arco emocional (ex: redenção, tragédia, crescimento, etc.)",
    "moments": [
        {{
            "section": "Nome da Secção",
            "position": 1,
            "score": 5,
            "emotions": ["esperança", "curiosidade"],
            "description": "O protagonista inicia a sua jornada..."
        }}
    ],
    "peak_positive": {{
        "section": "nome",
        "score": 8,
        "description": "momento mais positivo"
    }},
    "peak_negative": {{
        "section": "nome",
        "score": -7,
        "description": "momento mais negativo"
    }},
    "emotional_range": 15
}}

Responde em {language}. Apenas JSON, sem texto adicional."""

        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        content = response.text.strip()
        
        # Parse JSON response
        import json
        import re
        
        # Clean response - remove markdown code blocks if present
        content = re.sub(r'^```json\s*', '', content)
        content = re.sub(r'^```\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        
        try:
            sentiment_data = json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                sentiment_data = json.loads(json_match.group())
            else:
                return jsonify({'success': False, 'error': 'Erro ao processar resposta da IA'}), 500
        
        # Update usage count
        if current_user.is_authenticated:
            current_user.usage_count += 1
            db.session.commit()
        
        return jsonify({
            'success': True,
            'data': sentiment_data
        })
        
    except Exception as e:
        logger.warning(f"Sentiment analysis error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/favorites/check', methods=['GET'])
@api_login_required
def check_favorite():
    """Check if a book/analysis is favorited"""
    book_title = (request.args.get('book_title') or '').strip()
    book_author = (request.args.get('book_author') or '').strip() or None
    favorite_type = request.args.get('type', 'book')
    aspect = request.args.get('aspect')
    
    if not book_title:
        return jsonify({'success': False, 'error': 'Título é obrigatório'}), 400
    
    favorite = Favorite.query.filter_by(
        user_id=current_user.id,
        book_title=book_title,
        book_author=book_author,
        favorite_type=favorite_type,
        aspect=aspect
    ).first()
    
    return jsonify({
        'success': True,
        'is_favorited': favorite is not None,
        'favorite': favorite.to_dict() if favorite else None
    })

@app.route('/api/favorites/<int:favorite_id>/notes', methods=['PUT'])
@api_login_required
def update_favorite_notes(favorite_id):
    """Update notes on a favorite"""
    try:
        favorite = Favorite.query.filter_by(id=favorite_id, user_id=current_user.id).first()
        
        if not favorite:
            return jsonify({'success': False, 'error': 'Favorito não encontrado'}), 404
        
        data = request.get_json()
        favorite.notes = data.get('notes', '')
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Notas atualizadas!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/favorites')
@login_required
def favorites_page():
    """Favorites page"""
    favorites = Favorite.query.filter_by(user_id=current_user.id)\
        .order_by(Favorite.created_at.desc()).all()
    
    # Group by type
    book_favorites = [f for f in favorites if f.favorite_type == 'book']
    analysis_favorites = [f for f in favorites if f.favorite_type == 'analysis']
    
    return render_template('favorites.html', 
        favorites=favorites,
        book_favorites=book_favorites,
        analysis_favorites=analysis_favorites
    )

@app.route('/history')
@login_required
def reading_history():
    """Reading history timeline page"""
    from collections import OrderedDict, defaultdict
    
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    # Get all analyses for user
    analyses = AnalysisHistory.query.filter_by(user_id=current_user.id)\
        .order_by(AnalysisHistory.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    # Group by date
    timeline = OrderedDict()
    aspect_labels = {
        'info': 'Informação', 'summary': 'Resumo', 'characters': 'Personagens',
        'themes': 'Temas', 'world': 'Mundo', 'style': 'Estilo', 'quotes': 'Citações',
        'discussion': 'Discussão', 'similar': 'Similares', 'trivia': 'Curiosidades',
        'timeline': 'Cronologia', 'symbolism': 'Simbolismo', 'adaptation': 'Adaptações',
        'playlist': 'Playlist', 'trailer': 'Trailer', 'cover': 'Capa', 'casting': 'Casting',
        'chat': 'Chat', 'quiz': 'Quiz', 'interview': 'Entrevista',
        'continue': 'Continuação', 'alternate': 'Final Alt.'
    }
    
    for analysis in analyses.items:
        date_key = analysis.created_at.strftime('%d de %B de %Y')
        # Portuguese month names
        date_key = date_key.replace('January', 'Janeiro').replace('February', 'Fevereiro')\
            .replace('March', 'Março').replace('April', 'Abril').replace('May', 'Maio')\
            .replace('June', 'Junho').replace('July', 'Julho').replace('August', 'Agosto')\
            .replace('September', 'Setembro').replace('October', 'Outubro')\
            .replace('November', 'Novembro').replace('December', 'Dezembro')
        
        if date_key not in timeline:
            timeline[date_key] = []
        
        timeline[date_key].append({
            'id': analysis.id,
            'book_title': analysis.book_title,
            'book_author': analysis.book_author,
            'aspect': analysis.aspect,
            'aspect_label': aspect_labels.get(analysis.aspect, analysis.aspect),
            'response_preview': analysis.response_preview[:150] + '...' if analysis.response_preview and len(analysis.response_preview) > 150 else analysis.response_preview,
            'time': analysis.created_at.strftime('%H:%M')
        })
    
    # Calculate stats
    total_analyses = AnalysisHistory.query.filter_by(user_id=current_user.id).count()
    total_books = db.session.query(AnalysisHistory.book_title)\
        .filter_by(user_id=current_user.id).distinct().count()
    
    # Most used aspect
    aspect_counts = defaultdict(int)
    all_analyses = AnalysisHistory.query.filter_by(user_id=current_user.id).all()
    for a in all_analyses:
        aspect_counts[a.aspect] += 1
    
    favorite_aspect = 'N/A'
    if aspect_counts:
        most_used = max(aspect_counts, key=aspect_counts.get)
        favorite_aspect = aspect_labels.get(most_used, most_used)
    
    # Calculate streak (consecutive days with activity)
    streak_days = 0
    if all_analyses:
        dates = sorted(set(a.created_at.date() for a in all_analyses), reverse=True)
        from datetime import date, timedelta
        today = date.today()
        
        if dates and (dates[0] == today or dates[0] == today - timedelta(days=1)):
            streak_days = 1
            for i in range(1, len(dates)):
                if dates[i] == dates[i-1] - timedelta(days=1):
                    streak_days += 1
                else:
                    break
    
    stats = {
        'total_analyses': total_analyses,
        'total_books': total_books,
        'favorite_aspect': favorite_aspect,
        'streak_days': streak_days
    }
    
    return render_template('reading_history.html',
        timeline=timeline,
        stats=stats,
        has_more=analyses.has_next,
        current_page=page
    )

@app.route('/compare')
def compare_books_page():
    """Book comparison page"""
    return render_template('compare_books.html')

@app.route('/api/compare-books', methods=['POST'])
def compare_books_api():
    """API to compare two books using AI"""
    from utils.rate_limiter import check_and_reset_monthly_usage, get_usage_info
    
    try:
        data = request.get_json() or {}
        book1 = data.get('book1', {})
        book2 = data.get('book2', {})
        compare_type = data.get('compare_type', 'complete')
        
        book1_title = (book1.get('title') or '').strip()
        book1_author = (book1.get('author') or '').strip()
        book2_title = (book2.get('title') or '').strip()
        book2_author = (book2.get('author') or '').strip()
        
        if not book1_title or not book2_title:
            return jsonify({'success': False, 'error': 'Títulos de ambos os livros são obrigatórios'}), 400
        
        # Check usage limits for authenticated users
        if current_user.is_authenticated:
            check_and_reset_monthly_usage(current_user)
            usage_info = get_usage_info(current_user)
            
            if usage_info['usage_count'] >= usage_info['usage_limit']:
                return jsonify({
                    'success': False,
                    'error': 'Limite mensal de análises atingido',
                    'upgrade_required': True
                }), 429
            
            # Increment usage
            current_user.usage_count += 1
            db.session.commit()
        
        # Build comparison prompt
        book1_str = f'"{book1_title}"' + (f' de {book1_author}' if book1_author else '')
        book2_str = f'"{book2_title}"' + (f' de {book2_author}' if book2_author else '')
        
        type_prompts = {
            'complete': f"""Faz uma análise comparativa completa entre {book1_str} e {book2_str}.

Estrutura a resposta com:
## Visão Geral
Breve introdução às duas obras e seu contexto histórico/literário.

## Temas Principais
Compara os temas centrais de cada obra, identificando semelhanças e diferenças.

## Personagens
Compara os protagonistas e personagens principais - suas motivações, arcos de desenvolvimento e simbolismo.

## Estilo Narrativo
Analisa as diferenças e semelhanças no estilo de escrita, narração e técnicas literárias.

## Mensagem e Impacto
Que mensagens cada obra transmite? Como influenciaram a literatura e cultura?

## Conclusão
Síntese final da comparação com recomendação de qual ler primeiro e porquê.""",

            'themes': f"""Compara detalhadamente os TEMAS de {book1_str} e {book2_str}.

Analisa:
- Temas principais de cada obra
- Temas em comum entre as duas
- Como cada autor aborda temas semelhantes de forma diferente
- Subtemas e motivos recorrentes
- Relevância dos temas para a época e para hoje
- Simbolismo associado aos temas""",

            'characters': f"""Compara os PERSONAGENS de {book1_str} e {book2_str}.

Analisa:
- Protagonistas: personalidade, motivações, evolução
- Antagonistas: natureza do conflito
- Personagens secundários importantes
- Relações entre personagens
- Arquétipos utilizados
- Semelhanças e diferenças entre personagens das duas obras""",

            'style': f"""Compara o ESTILO LITERÁRIO de {book1_str} e {book2_str}.

Analisa:
- Tipo de narração (1ª/3ª pessoa, omnisciente, etc.)
- Tom e atmosfera
- Uso de linguagem e vocabulário
- Estrutura narrativa
- Técnicas literárias (flashbacks, simbolismo, etc.)
- Ritmo e pacing
- Diálogos vs descrição"""
        }
        
        prompt = type_prompts.get(compare_type, type_prompts['complete'])
        prompt += "\n\nResponde em português de Portugal. Sê detalhado mas conciso."
        
        # Call Gemini API
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        content = response.text.strip()
        
        # Save to analysis history if authenticated
        if current_user.is_authenticated:
            try:
                analysis = AnalysisHistory(
                    user_id=current_user.id,
                    book_title=f"{book1_title} vs {book2_title}",
                    book_author=f"{book1_author or 'N/A'} / {book2_author or 'N/A'}",
                    aspect='compare',
                    language='pt-pt',
                    response_preview=content[:500] if content else None
                )
                db.session.add(analysis)
                db.session.commit()
            except Exception as e:
                logger.warning(f"Error saving comparison history: {e}")
        
        return jsonify({
            'success': True,
            'content': content,
            'book1': {'title': book1_title, 'author': book1_author},
            'book2': {'title': book2_title, 'author': book2_author}
        })
        
    except Exception as e:
        logger.warning(f"Compare books error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/recommendations')
@login_required
def recommendations_page():
    """Personalized recommendations page"""
    from collections import Counter
    
    # Get user's reading history
    analyses = AnalysisHistory.query.filter_by(user_id=current_user.id).all()
    
    # Build reading profile
    books = list(set(a.book_title for a in analyses))
    authors = list(set(a.book_author for a in analyses if a.book_author))
    aspects = [a.aspect for a in analyses]
    
    # Determine reading style based on most used aspects
    aspect_counts = Counter(aspects)
    if aspect_counts:
        top_aspect = aspect_counts.most_common(1)[0][0]
        style_map = {
            'characters': 'Analítico',
            'themes': 'Reflexivo',
            'summary': 'Prático',
            'quiz': 'Interativo',
            'chat': 'Explorador',
            'interview': 'Criativo'
        }
        reading_style = style_map.get(top_aspect, 'Curioso')
    else:
        reading_style = 'Iniciante'
    
    profile = {
        'total_books': len(books),
        'favorite_genres': [],  # Would need genre data
        'favorite_authors': authors[:5],
        'reading_style': reading_style,
        'recent_books': books[:5]
    }
    
    return render_template('recommendations.html', profile=profile)

@app.route('/api/recommendations', methods=['POST'])
@api_login_required
def get_recommendations():
    """API to generate personalized book recommendations"""
    from utils.rate_limiter import check_and_reset_monthly_usage, get_usage_info
    from collections import Counter
    
    try:
        data = request.get_json() or {}
        rec_type = data.get('type', 'similar')
        
        # Check usage limits
        check_and_reset_monthly_usage(current_user)
        usage_info = get_usage_info(current_user)
        
        if usage_info['usage_count'] >= usage_info['usage_limit']:
            return jsonify({
                'success': False,
                'error': 'Limite mensal de análises atingido',
                'upgrade_required': True
            }), 429
        
        # Get user's reading history
        analyses = AnalysisHistory.query.filter_by(user_id=current_user.id)\
            .order_by(AnalysisHistory.created_at.desc()).all()
        
        if not analyses:
            return jsonify({
                'success': False,
                'error': 'Precisas de explorar alguns livros primeiro para receber recomendações personalizadas'
            }), 400
        
        # Build context from history
        books = list(set(a.book_title for a in analyses))
        authors = list(set(a.book_author for a in analyses if a.book_author))
        aspects = Counter(a.aspect for a in analyses)
        
        books_str = ', '.join(books[:10])
        authors_str = ', '.join(authors[:5]) if authors else 'vários autores'
        
        # Build prompt based on recommendation type
        type_prompts = {
            'similar': f"""Com base no histórico de leitura deste utilizador, recomenda 5 livros SIMILARES.

Livros explorados: {books_str}
Autores: {authors_str}

Recomenda livros com temas, estilos ou géneros semelhantes aos que o utilizador já demonstrou interesse.""",

            'expand': f"""Com base no histórico de leitura deste utilizador, recomenda 5 livros para EXPANDIR os horizontes literários.

Livros explorados: {books_str}
Autores: {authors_str}

Recomenda livros de géneros ou estilos DIFERENTES mas que possam agradar com base nos padrões de leitura. Sugere algo fora da zona de conforto mas acessível.""",

            'classics': f"""Com base no histórico de leitura deste utilizador, recomenda 5 CLÁSSICOS da literatura.

Livros explorados: {books_str}
Autores: {authors_str}

Recomenda clássicos literários (obras consagradas) que se alinhem com os interesses demonstrados. Inclui clássicos de diferentes épocas e culturas.""",

            'hidden': f"""Com base no histórico de leitura deste utilizador, recomenda 5 PÉROLAS ESCONDIDAS.

Livros explorados: {books_str}
Autores: {authors_str}

Recomenda livros menos conhecidos mas excelentes - obras subestimadas, autores emergentes, ou livros que merecem mais atenção. Evita bestsellers óbvios."""
        }
        
        prompt = type_prompts.get(rec_type, type_prompts['similar'])
        prompt += """

Para CADA livro recomendado, responde EXATAMENTE neste formato JSON (array de 5 objetos):
[
  {
    "title": "Título do Livro",
    "author": "Nome do Autor",
    "reason": "Explicação breve (1-2 frases) de porque este livro é recomendado",
    "tags": ["tag1", "tag2", "tag3"],
    "match_score": 85
  }
]

O match_score deve ser um número de 70 a 98 indicando o quão bem o livro combina com o perfil.
As tags devem ser 2-4 palavras descritivas (género, tom, tema).
Responde APENAS com o JSON válido, sem texto adicional."""

        # Call Gemini API
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        content = response.text.strip()
        
        # Parse JSON response
        import json
        # Clean up response if needed
        if content.startswith('```'):
            content = content.split('```')[1]
            if content.startswith('json'):
                content = content[4:]
        content = content.strip()
        
        try:
            recommendations = json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                recommendations = json.loads(json_match.group())
            else:
                return jsonify({'success': False, 'error': 'Erro ao processar recomendações'}), 500
        
        # Increment usage
        current_user.usage_count += 1
        db.session.commit()
        
        # Save to history
        try:
            analysis = AnalysisHistory(
                user_id=current_user.id,
                book_title='Recomendações Personalizadas',
                book_author=rec_type,
                aspect='recommendations',
                language='pt-pt',
                response_preview=f"Recomendados: {', '.join(r['title'] for r in recommendations[:3])}"
            )
            db.session.add(analysis)
            db.session.commit()
        except Exception as e:
            logger.warning(f"Error saving recommendations history: {e}")
        
        return jsonify({
            'success': True,
            'recommendations': recommendations,
            'type': rec_type
        })
        
    except Exception as e:
        logger.warning(f"Recommendations error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/export/pdf', methods=['POST'])
@api_login_required
def export_pdf():
    """Export analyses to PDF"""
    from utils.export_service import generate_pdf, get_aspect_label
    
    try:
        data = request.get_json() or {}
        book_title = (data.get('book_title') or '').strip()
        book_author = (data.get('book_author') or '').strip()
        analyses_data = data.get('analyses', [])
        
        if not book_title:
            return jsonify({'success': False, 'error': 'Título do livro é obrigatório'}), 400
        
        if not analyses_data:
            return jsonify({'success': False, 'error': 'Nenhuma análise para exportar'}), 400
        
        # Format analyses
        analyses = []
        for a in analyses_data:
            analyses.append({
                'aspect': a.get('aspect', ''),
                'aspect_label': get_aspect_label(a.get('aspect', '')),
                'content': a.get('content', ''),
                'created_at': a.get('created_at', '')
            })
        
        # Generate PDF
        pdf_buffer = generate_pdf(
            book_title=book_title,
            book_author=book_author,
            analyses=analyses,
            user_name=current_user.name
        )
        
        # Return PDF file
        from flask import send_file
        filename = f"analise_{book_title.replace(' ', '_')}.pdf"
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.warning(f"PDF export error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/export/epub', methods=['POST'])
@api_login_required
def export_epub():
    """Export analyses to EPUB"""
    from utils.export_service import generate_epub, get_aspect_label
    
    try:
        data = request.get_json() or {}
        book_title = (data.get('book_title') or '').strip()
        book_author = (data.get('book_author') or '').strip()
        analyses_data = data.get('analyses', [])
        
        if not book_title:
            return jsonify({'success': False, 'error': 'Título do livro é obrigatório'}), 400
        
        if not analyses_data:
            return jsonify({'success': False, 'error': 'Nenhuma análise para exportar'}), 400
        
        # Format analyses
        analyses = []
        for a in analyses_data:
            analyses.append({
                'aspect': a.get('aspect', ''),
                'aspect_label': get_aspect_label(a.get('aspect', '')),
                'content': a.get('content', ''),
                'created_at': a.get('created_at', '')
            })
        
        # Generate EPUB
        epub_buffer = generate_epub(
            book_title=book_title,
            book_author=book_author,
            analyses=analyses,
            user_name=current_user.name
        )
        
        # Return EPUB file
        from flask import send_file
        filename = f"analise_{book_title.replace(' ', '_')}.epub"
        return send_file(
            epub_buffer,
            mimetype='application/epub+zip',
            as_attachment=True,
            download_name=filename
        )
        
    except ImportError:
        return jsonify({'success': False, 'error': 'Exportação EPUB não disponível'}), 500
    except Exception as e:
        logger.warning(f"EPUB export error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/export/history', methods=['POST'])
@api_login_required
def export_history():
    """Export user's analysis history to PDF or EPUB"""
    from utils.export_service import generate_pdf, generate_epub, get_aspect_label
    
    try:
        data = request.get_json() or {}
        export_format = data.get('format', 'pdf')
        book_filter = (data.get('book_title') or '').strip()
        
        # Get user's analyses
        query = AnalysisHistory.query.filter_by(user_id=current_user.id)
        
        if book_filter:
            query = query.filter(AnalysisHistory.book_title.ilike(f'%{book_filter}%'))
        
        analyses_db = query.order_by(AnalysisHistory.created_at.desc()).limit(50).all()
        
        if not analyses_db:
            return jsonify({'success': False, 'error': 'Nenhuma análise encontrada'}), 400
        
        # Group by book
        books = {}
        for a in analyses_db:
            key = a.book_title
            if key not in books:
                books[key] = {
                    'title': a.book_title,
                    'author': a.book_author,
                    'analyses': []
                }
            books[key]['analyses'].append({
                'aspect': a.aspect,
                'aspect_label': get_aspect_label(a.aspect),
                'content': a.response_preview or '',
                'created_at': a.created_at.strftime('%d/%m/%Y %H:%M') if a.created_at else ''
            })
        
        # For now, export first book or all as combined
        if book_filter and len(books) == 1:
            book_data = list(books.values())[0]
            book_title = book_data['title']
            book_author = book_data['author']
            analyses = book_data['analyses']
        else:
            book_title = 'Histórico de Análises'
            book_author = current_user.name
            analyses = []
            for book_data in books.values():
                analyses.append({
                    'aspect': 'book_header',
                    'aspect_label': f"📖 {book_data['title']}",
                    'content': f"Autor: {book_data['author'] or 'Desconhecido'}\n\n" + 
                               '\n\n'.join([f"**{a['aspect_label']}**\n{a['content']}" for a in book_data['analyses']]),
                    'created_at': ''
                })
        
        # Generate file
        if export_format == 'epub':
            buffer = generate_epub(book_title, book_author, analyses, current_user.name)
            mimetype = 'application/epub+zip'
            ext = 'epub'
        else:
            buffer = generate_pdf(book_title, book_author, analyses, current_user.name)
            mimetype = 'application/pdf'
            ext = 'pdf'
        
        from flask import send_file
        filename = f"historico_analises.{ext}"
        return send_file(
            buffer,
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.warning(f"History export error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== REFERRAL/AFFILIATE ROUTES ====================

from models.book import Referral, ReferralSignup
import secrets
import config

@app.route('/referral')
@login_required
def referral_page():
    """Referral program dashboard"""
    referral = Referral.query.filter_by(referrer_id=current_user.id).first()
    signups = []
    if referral:
        signups = referral.referral_signups.order_by(ReferralSignup.created_at.desc()).limit(10).all()
    
    return render_template('referral.html', 
                          referral=referral, 
                          signups=signups,
                          app_url=config.APP_URL)

@app.route('/api/referral/generate', methods=['POST'])
@api_login_required
def generate_referral_code():
    """Generate a unique referral code for the user"""
    try:
        # Check if user already has a referral code
        existing = Referral.query.filter_by(referrer_id=current_user.id).first()
        if existing:
            return jsonify({'success': True, 'code': existing.referral_code})
        
        # Generate unique code
        while True:
            code = secrets.token_urlsafe(6).upper()[:8]
            if not Referral.query.filter_by(referral_code=code).first():
                break
        
        # Create referral entry
        referral = Referral(
            referrer_id=current_user.id,
            referral_code=code
        )
        db.session.add(referral)
        db.session.commit()
        
        return jsonify({'success': True, 'code': code})
        
    except Exception as e:
        logger.warning(f"Generate referral error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/r/<code>')
def referral_redirect(code):
    """Handle referral link clicks"""
    referral = Referral.query.filter_by(referral_code=code, is_active=True).first()
    
    if referral:
        # Increment click count
        referral.clicks += 1
        db.session.commit()
        
        # Store referral code in session for registration
        session['referral_code'] = code
    
    # Redirect to registration page
    return redirect(url_for('register'))

@app.route('/api/referral/stats')
@api_login_required
def get_referral_stats():
    """Get referral statistics for current user"""
    try:
        referral = Referral.query.filter_by(referrer_id=current_user.id).first()
        
        if not referral:
            return jsonify({'success': False, 'error': 'Nenhum código de referência encontrado'})
        
        return jsonify({
            'success': True,
            'stats': referral.to_dict()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def process_referral_signup(user, referral_code):
    """Process a new signup from a referral link"""
    if not referral_code:
        return
    
    referral = Referral.query.filter_by(referral_code=referral_code, is_active=True).first()
    if not referral:
        return
    
    # Don't allow self-referral
    if referral.referrer_id == user.id:
        return
    
    try:
        # Create signup record
        signup = ReferralSignup(
            referral_id=referral.id,
            referred_user_id=user.id,
            status='signed_up'
        )
        db.session.add(signup)
        
        # Update referral stats
        referral.signups += 1
        referral.last_referral_at = datetime.utcnow()
        
        # Give bonus to referred user (10 extra analyses)
        user.usage_count = max(0, user.usage_count - 10)  # Subtract from usage = more available
        signup.referred_reward_given = True
        
        db.session.commit()
        
    except Exception as e:
        logger.warning(f"Process referral signup error: {e}")
        db.session.rollback()

@app.route('/enterprise')
def enterprise_page():
    """Enterprise/Schools pricing page"""
    return render_template('enterprise.html')

# ==================== MARKETPLACE ROUTES ====================

from models.book import PromptTemplate, PromptPurchase

@app.route('/marketplace')
def marketplace_page():
    """Marketplace main page"""
    # Get stats
    stats = {
        'total_templates': PromptTemplate.query.filter_by(is_active=True).count(),
        'total_creators': db.session.query(db.func.count(db.func.distinct(PromptTemplate.creator_id))).scalar() or 0,
        'free_templates': PromptTemplate.query.filter_by(is_active=True, price=0).count(),
        'total_downloads': db.session.query(db.func.sum(PromptTemplate.downloads)).scalar() or 0
    }
    
    # Get featured templates
    featured = PromptTemplate.query.filter_by(is_active=True, is_featured=True)\
        .order_by(PromptTemplate.downloads.desc()).limit(3).all()
    
    # Get all templates
    templates = PromptTemplate.query.filter_by(is_active=True)\
        .order_by(PromptTemplate.downloads.desc()).all()
    
    return render_template('marketplace.html', 
                          stats=stats, 
                          featured=featured, 
                          templates=templates)

@app.route('/marketplace/create')
@login_required
def marketplace_create_page():
    """Create new template page"""
    return render_template('marketplace_create.html')

@app.route('/marketplace/my-templates')
@login_required
def marketplace_my_templates():
    """User's templates page"""
    templates = PromptTemplate.query.filter_by(creator_id=current_user.id)\
        .order_by(PromptTemplate.created_at.desc()).all()
    
    purchases = PromptPurchase.query.filter_by(user_id=current_user.id)\
        .order_by(PromptPurchase.purchased_at.desc()).all()
    
    # Calculate earnings
    total_earnings = 0
    for t in templates:
        total_earnings += sum(p.amount_paid * 0.7 for p in t.purchases)  # 70% to creator
    
    return render_template('marketplace_my_templates.html',
                          templates=templates,
                          purchases=purchases,
                          total_earnings=total_earnings)

@app.route('/api/marketplace/create', methods=['POST'])
@api_login_required
def create_template():
    """Create a new prompt template"""
    try:
        data = request.get_json() or {}
        
        title = (data.get('title') or '').strip()
        category = (data.get('category') or '').strip()
        description = (data.get('description') or '').strip()
        prompt_template = (data.get('prompt_template') or '').strip()
        example_output = (data.get('example_output') or '').strip()
        price = float(data.get('price', 0))
        
        if not title or not category or not prompt_template:
            return jsonify({'success': False, 'error': 'Campos obrigatórios em falta'}), 400
        
        if price < 0 or price > 50:
            return jsonify({'success': False, 'error': 'Preço inválido (0-50€)'}), 400
        
        template = PromptTemplate(
            creator_id=current_user.id,
            title=title,
            category=category,
            description=description,
            prompt_template=prompt_template,
            example_output=example_output,
            price=price
        )
        db.session.add(template)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'template_id': template.id
        })
        
    except Exception as e:
        logger.warning(f"Create template error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/marketplace/template/<int:template_id>')
def get_template(template_id):
    """Get template details"""
    try:
        template = PromptTemplate.query.get(template_id)
        if not template or not template.is_active:
            return jsonify({'success': False, 'error': 'Template não encontrado'}), 404
        
        # Check if user owns this template
        owned = False
        if current_user.is_authenticated:
            if template.creator_id == current_user.id:
                owned = True
            elif template.price == 0:
                owned = True
            else:
                purchase = PromptPurchase.query.filter_by(
                    user_id=current_user.id,
                    template_id=template_id
                ).first()
                owned = purchase is not None
        
        return jsonify({
            'success': True,
            'template': template.to_dict(),
            'owned': owned
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/marketplace/buy/<int:template_id>', methods=['POST'])
@api_login_required
def buy_template(template_id):
    """Purchase a template"""
    try:
        template = PromptTemplate.query.get(template_id)
        if not template or not template.is_active:
            return jsonify({'success': False, 'error': 'Template não encontrado'}), 404
        
        if template.price == 0:
            return jsonify({'success': False, 'error': 'Este template é gratuito'}), 400
        
        # Check if already purchased
        existing = PromptPurchase.query.filter_by(
            user_id=current_user.id,
            template_id=template_id
        ).first()
        
        if existing:
            return jsonify({'success': False, 'error': 'Já compraste este template'}), 400
        
        # Create purchase (in real app, would integrate with Stripe)
        purchase = PromptPurchase(
            user_id=current_user.id,
            template_id=template_id,
            amount_paid=template.price
        )
        db.session.add(purchase)
        
        # Update download count
        template.downloads += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Template comprado com sucesso'
        })
        
    except Exception as e:
        logger.warning(f"Buy template error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/marketplace/use/<int:template_id>', methods=['POST'])
@api_login_required
def use_template(template_id):
    """Get template prompt for use"""
    try:
        template = PromptTemplate.query.get(template_id)
        if not template or not template.is_active:
            return jsonify({'success': False, 'error': 'Template não encontrado'}), 404
        
        # Check access
        has_access = False
        if template.creator_id == current_user.id:
            has_access = True
        elif template.price == 0:
            has_access = True
            template.downloads += 1
        else:
            purchase = PromptPurchase.query.filter_by(
                user_id=current_user.id,
                template_id=template_id
            ).first()
            has_access = purchase is not None
        
        if not has_access:
            return jsonify({'success': False, 'error': 'Não tens acesso a este template'}), 403
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'prompt_template': template.prompt_template
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/enterprise/contact', methods=['POST'])
def enterprise_contact():
    """Handle enterprise contact form submissions"""
    try:
        data = request.get_json() or {}
        
        organization = (data.get('organization') or '').strip()
        contact_name = (data.get('contact_name') or '').strip()
        email = (data.get('email') or '').strip()
        phone = (data.get('phone') or '').strip()
        role = (data.get('role') or '').strip()
        user_count = (data.get('user_count') or '').strip()
        plan_type = (data.get('plan_type') or '').strip()
        message = (data.get('message') or '').strip()
        
        if not organization or not contact_name or not email or not user_count:
            return jsonify({'success': False, 'error': 'Campos obrigatórios em falta'}), 400
        
        # Log the enterprise inquiry
        logger.warning(f"Enterprise Inquiry: {organization} - {contact_name} ({email}) - {user_count} users - Plan: {plan_type}")
        
        # Send notification email (if email service is configured)
        try:
            from utils.email_service import send_email
            subject = f"[Enterprise] Novo pedido de {organization}"
            body = f"""
            Nova consulta de licenças em volume:
            
            Organização: {organization}
            Contacto: {contact_name}
            Cargo: {role}
            Email: {email}
            Telefone: {phone}
            Nº Utilizadores: {user_count}
            Plano: {plan_type}
            
            Mensagem:
            {message}
            """
            # send_email('enterprise@almadelivro.pt', subject, body)
        except Exception as e:
            logger.warning(f"Error sending enterprise notification: {e}")
        
        return jsonify({
            'success': True,
            'message': 'Pedido recebido com sucesso'
        })
        
    except Exception as e:
        logger.warning(f"Enterprise contact error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def process_referral_conversion(user, subscription_amount):
    """Process a referral conversion when user subscribes"""
    try:
        # Find if this user was referred
        signup = ReferralSignup.query.filter_by(
            referred_user_id=user.id,
            status='signed_up'
        ).first()
        
        if not signup:
            return
        
        referral = signup.referral
        
        # Calculate commission
        commission = subscription_amount * referral.commission_rate
        
        # Update signup
        signup.status = 'converted'
        signup.converted_at = datetime.utcnow()
        signup.commission_amount = commission
        
        # Update referral stats
        referral.conversions += 1
        referral.total_earnings += commission
        referral.pending_earnings += commission
        
        # Give bonus to referrer (10 extra analyses)
        referrer = User.query.get(referral.referrer_id)
        if referrer and not signup.referrer_reward_given:
            referrer.usage_count = max(0, referrer.usage_count - 10)
            signup.referrer_reward_given = True
        
        db.session.commit()
        
    except Exception as e:
        logger.warning(f"Process referral conversion error: {e}")
        db.session.rollback()

# ==================== AUTHENTICATION ROUTES ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('book_explorer_page'))
    
    from forms import LoginForm
    form = LoginForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user and bcrypt.check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember.data)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            next_page = request.args.get('next')
            flash('Login efetuado com sucesso!', 'success')
            return redirect(next_page if next_page else url_for('book_explorer_page'))
        else:
            flash('Email ou password incorretos.', 'error')
    
    return render_template('auth/login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page"""
    if current_user.is_authenticated:
        return redirect(url_for('book_explorer_page'))
    
    from forms import RegisterForm
    form = RegisterForm()
    
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(
            name=form.name.data,
            email=form.email.data.lower(),
            password_hash=hashed_password
        )
        db.session.add(user)
        db.session.commit()
        
        # Process referral if exists
        referral_code = session.pop('referral_code', None)
        if referral_code:
            process_referral_signup(user, referral_code)
        
        # Send welcome email
        try:
            from utils.email_service import send_welcome_email
            send_welcome_email(user.email, user.name)
        except Exception as e:
            logger.warning(f"Error sending welcome email: {e}")
        
        # Track signup in analytics
        try:
            from utils.analytics import tracker
            tracker.track_signup(user.id)
        except Exception as e:
            logger.warning(f"Analytics error: {e}")
        
        flash('Conta criada com sucesso! Pode agora fazer login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('auth/register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    """Logout user"""
    logout_user()
    flash('Sessão terminada.', 'info')
    return redirect(url_for('book_explorer_page'))

@app.route('/profile')
@login_required
def profile():
    """User profile page"""
    return render_template('auth/profile.html')

# ==================== END AUTHENTICATION ROUTES ====================

# ==================== DISABLED: BOOK CREATION AND LIBRARY ROUTES ====================
# These routes have been disabled - app now focuses only on Book Explorer functionality

# @app.route('/generate', methods=['POST']) - DISABLED
# @app.route('/books') - DISABLED  
# @app.route('/api/books') - DISABLED

# Redirect old routes to explorer
@app.route('/books')
def list_books():
    """Redirect to explorer - library feature disabled"""
    return redirect(url_for('book_explorer_page'))

# DISABLED: Individual book routes (library feature removed)
# @app.route('/book/<int:book_id>') - DISABLED
# @app.route('/api/book/<int:book_id>') - DISABLED
# @app.route('/download/<int:book_id>') - DISABLED
# @app.route('/download/<int:book_id>/md') - DISABLED
# @app.route('/delete/<int:book_id>') - DISABLED
# @app.route('/download/<int:book_id>/pdf') - DISABLED
# @app.route('/download/<int:book_id>/epub') - DISABLED

@app.route('/book/<int:book_id>')
def view_book(book_id):
    """Redirect to explorer - library feature disabled"""
    return redirect(url_for('book_explorer_page'))

# ==================== EXPLORER FEATURES (ACTIVE) ====================

# Keep download routes for explorer export functionality
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

@app.route('/my-dashboard')
@login_required
def user_dashboard():
    """User dashboard with personal statistics, analysis history, and account management"""
    from collections import defaultdict
    from datetime import timedelta
    from utils.rate_limiter import get_next_reset_date
    
    # Get user's analysis history
    analyses = AnalysisHistory.query.filter_by(user_id=current_user.id)\
        .order_by(AnalysisHistory.created_at.desc())\
        .limit(50).all()
    
    # Calculate statistics
    total_analyses = AnalysisHistory.query.filter_by(user_id=current_user.id).count()
    unique_books = db.session.query(AnalysisHistory.book_title)\
        .filter_by(user_id=current_user.id)\
        .distinct().count()
    
    # Usage by type
    usage_by_type = defaultdict(int)
    aspect_labels = {
        'info': 'Informação', 'summary': 'Resumo', 'characters': 'Personagens',
        'themes': 'Temas', 'world': 'Mundo', 'style': 'Estilo', 'quotes': 'Citações',
        'discussion': 'Discussão', 'similar': 'Similares', 'trivia': 'Curiosidades',
        'timeline': 'Cronologia', 'symbolism': 'Simbolismo', 'adaptation': 'Adaptações',
        'playlist': 'Playlist', 'trailer': 'Trailer', 'cover': 'Capa', 'casting': 'Casting',
        'chat': 'Chat', 'quiz': 'Quiz', 'interview': 'Entrevista',
        'continue': 'Continuação', 'alternate': 'Final Alt.'
    }
    
    all_analyses = AnalysisHistory.query.filter_by(user_id=current_user.id).all()
    for a in all_analyses:
        label = aspect_labels.get(a.aspect, a.aspect)
        usage_by_type[label] += 1
    
    # Days until reset
    next_reset = get_next_reset_date()
    days_until_reset = (next_reset - datetime.utcnow()).days
    
    stats = {
        'total_analyses': total_analyses,
        'unique_books': unique_books
    }
    
    return render_template('user_dashboard.html',
        analyses=[a.to_dict() for a in analyses],
        stats=stats,
        usage_by_type=dict(usage_by_type),
        days_until_reset=days_until_reset
    )

# DISABLED: Reading mode for created books (library feature removed)
@app.route('/read/<int:book_id>')
def read_book_page(book_id):
    """Redirect to explorer - library feature disabled"""
    return redirect(url_for('book_explorer_page'))

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

# DISABLED: Book editing (library feature removed)
@app.route('/edit/<int:book_id>')
def edit_book_page(book_id):
    """Redirect to explorer - library feature disabled"""
    return redirect(url_for('book_explorer_page'))

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

        model = genai.GenerativeModel("gemini-2.5-flash")
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

        model = genai.GenerativeModel("gemini-2.5-flash")
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
        logger.warning(f"JSON Decode Error: {e}")
        logger.warning(f"Response text: {response_text[:500]}")
        return jsonify({
            'success': True,
            'themes': [{'title': 'Tema sugerido', 'description': response_text[:200] if response_text else 'Erro ao processar resposta', 'appeal': ''}]
        })
    except Exception as e:
        logger.warning(f"Error in suggest_themes: {e}")
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

        model = genai.GenerativeModel("gemini-2.5-flash")
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

        model = genai.GenerativeModel("gemini-2.5-flash")
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

        model = genai.GenerativeModel("gemini-2.5-flash")
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

        model = genai.GenerativeModel("gemini-2.5-flash")
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

        model = genai.GenerativeModel("gemini-2.5-flash")
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
        model = genai.GenerativeModel("gemini-2.5-flash")
        
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

        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        answer = response.text.strip()
        
        return jsonify({
            'success': True,
            'answer': answer,
            'question': question
        })
        
    except Exception as e:
        logger.warning(f"Chat error: {e}")
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
    from utils.rate_limiter import check_and_reset_monthly_usage, get_usage_info
    
    try:
        data = request.get_json()
        title = data.get('title', '').strip()
        author = data.get('author', '').strip()
        aspect = data.get('aspect', 'info')
        question = data.get('question', '')
        history = data.get('history', [])
        language = data.get('language', 'pt-pt')
        
        # Feature access control based on plan
        premium_features = ['quiz', 'interview', 'author_interview', 'continue', 'alternate']
        feature_map = {
            'quiz': 'quiz',
            'interview': 'interview',
            'author_interview': 'interview',
            'continue': 'continue_story',
            'alternate': 'alternate_ending'
        }
        
        if current_user.is_authenticated:
            # Check and reset monthly usage if needed
            check_and_reset_monthly_usage(current_user)
            
            # Get plan config
            plan_config = current_user.get_plan_config()
            limit = plan_config['limits']['analyses_per_month']
            
            # Check usage limit
            if current_user.usage_count >= limit:
                return jsonify({
                    'success': False, 
                    'error': f'Limite mensal de {limit} análises atingido. Faça upgrade para continuar.',
                    'upgrade_required': True,
                    'usage_info': get_usage_info(current_user)
                }), 429
            
            # Check feature access for premium features
            if aspect in premium_features:
                feature_key = feature_map.get(aspect, aspect)
                if not plan_config['features'].get(feature_key, False):
                    return jsonify({
                        'success': False,
                        'error': 'Esta funcionalidade requer plano Pro ou Premium.',
                        'upgrade_required': True,
                        'feature': aspect,
                        'current_plan': current_user.plan
                    }), 403
            
            # Increment usage counter
            current_user.usage_count += 1
            db.session.commit()
        else:
            # Anonymous users: check if premium feature
            if aspect in premium_features:
                return jsonify({
                    'success': False,
                    'error': 'Faça login e subscreva um plano para aceder a esta funcionalidade.',
                    'login_required': True
                }), 401
        
        # Language configuration
        lang_names = {
            'pt-pt': 'português de Portugal',
            'pt-br': 'português do Brasil',
            'en': 'inglês',
            'fr': 'francês',
            'de': 'alemão',
            'it': 'italiano'
        }
        lang_name = lang_names.get(language, 'português')
        
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

Responde de forma concisa em {lang_name}.""",

            'summary': f"""Faz um resumo completo e detalhado do livro {book_ref}.
Inclui:
- Contexto inicial
- Desenvolvimento da história
- Principais acontecimentos
- Conclusão (com spoilers)

Escreve em {lang_name}, de forma clara e organizada.""",

            'characters': f"""Analisa os personagens principais do livro {book_ref}.
Para cada personagem inclui:
- Nome e papel na história
- Características físicas e psicológicas
- Motivações e objetivos
- Arco de desenvolvimento
- Relações com outros personagens

Organiza por personagem. Escreve em {lang_name}.""",

            'themes': f"""Analisa os temas e mensagens do livro {book_ref}.
Inclui:
- Temas principais
- Temas secundários
- Mensagens e lições
- Críticas sociais (se aplicável)
- Relevância atual

Escreve em {lang_name} de forma profunda mas acessível.""",

            'world': f"""Descreve o mundo e cenário do livro {book_ref}.
Inclui:
- Localização geográfica
- Período temporal/época
- Contexto histórico e social
- Atmosfera e ambiente
- Regras do mundo (se fantasia/ficção científica)

Escreve em {lang_name} com detalhes imersivos.""",

            'style': f"""Analisa o estilo literário do livro {book_ref}.
Inclui:
- Tipo de narrador
- Estrutura narrativa
- Linguagem e tom
- Técnicas literárias utilizadas
- Influências do autor
- Comparação com outras obras

Escreve em {lang_name} de forma técnica mas acessível.""",

            'quotes': f"""Lista as citações mais famosas e marcantes do livro {book_ref}.
Para cada citação:
- A frase exata (ou aproximada)
- Contexto em que aparece
- Significado e importância

Inclui pelo menos 5-8 citações memoráveis. Escreve em {lang_name}.""",

            'discussion': f"""Cria questões de discussão para um clube do livro sobre {book_ref}.
Inclui:
- Perguntas sobre personagens
- Perguntas sobre temas
- Perguntas sobre decisões morais
- Perguntas de reflexão pessoal
- Perguntas de comparação com a realidade

Cria 10-12 perguntas provocadoras. Escreve em {lang_name}.""",

            'similar': f"""Recomenda livros similares a {book_ref}.
Para cada recomendação inclui:
- Título e autor
- Porquê é similar
- Breve sinopse

Recomenda 6-8 livros. Organiza por relevância. Escreve em {lang_name}.""",

            'trivia': f"""Partilha curiosidades interessantes sobre o livro {book_ref}.
Inclui:
- Factos sobre a escrita/publicação
- Curiosidades sobre o autor
- Impacto cultural
- Controvérsias (se existirem)
- Records e prémios
- Factos pouco conhecidos

Lista 8-10 curiosidades. Escreve em {lang_name}.""",

            'timeline': f"""Cria uma cronologia dos eventos do livro {book_ref}.
Lista os principais acontecimentos em ordem:
- Eventos do passado (backstory)
- Eventos principais da narrativa
- Consequências e epílogo

Organiza de forma clara com datas/momentos. Escreve em {lang_name}.""",

            'symbolism': f"""Analisa o simbolismo no livro {book_ref}.
Inclui:
- Símbolos principais e seus significados
- Metáforas recorrentes
- Elementos alegóricos
- Cores, objetos ou lugares simbólicos
- Interpretações

Explica cada símbolo em detalhe. Escreve em {lang_name}.""",

            'adaptation': f"""Lista as adaptações do livro {book_ref}.
Inclui:
- Filmes
- Séries de TV
- Peças de teatro
- Audiobooks notáveis
- Outras adaptações

Para cada uma: ano, realizador/produtor, elenco principal, recepção.
Escreve em {lang_name}.""",

            'chapter_summaries': f"""Cria um resumo detalhado de CADA CAPÍTULO do livro {book_ref}.

Para cada capítulo inclui:
- **Número/Nome do capítulo**
- **Resumo** (3-5 parágrafos com os eventos principais)
- **Personagens presentes** nesse capítulo
- **Locais** onde decorre a ação
- **Eventos-chave** que acontecem
- **Importância** para a história geral

Se o livro tiver muitos capítulos, foca nos mais importantes ou agrupa por partes/secções.
Organiza de forma clara e sequencial.
Inclui SPOILERS - este é um resumo completo.

Escreve em {lang_name} de forma detalhada e organizada.""",

            'psychological': f"""Faz uma ANÁLISE PSICOLÓGICA PROFUNDA dos personagens principais do livro {book_ref}.

Para cada personagem principal, analisa:

🧠 **PERFIL PSICOLÓGICO**
- Tipo de personalidade (MBTI aproximado ou descrição)
- Traços dominantes de carácter
- Mecanismos de defesa utilizados
- Padrões de comportamento

💔 **TRAUMAS E FERIDAS**
- Traumas de infância ou passado
- Feridas emocionais não resolvidas
- Como esses traumas afetam as suas ações
- Momentos de gatilho na história

🎭 **ARQUÉTIPOS DE JUNG**
- Arquétipo principal (Herói, Sombra, Anima/Animus, Mentor, etc.)
- Arquétipos secundários
- Jornada de individuação do personagem
- Confronto com a Sombra

🔮 **MOTIVAÇÕES INCONSCIENTES**
- Desejos ocultos
- Medos profundos
- Necessidades não satisfeitas
- O que realmente move o personagem (além do óbvio)

🔄 **EVOLUÇÃO PSICOLÓGICA**
- Estado mental no início
- Transformações ao longo da história
- Momentos de crise/crescimento
- Estado mental no final

Analisa 3-5 personagens principais com profundidade.
Escreve em {lang_name} de forma técnica mas acessível.""",

            'influences': f"""Analisa as INFLUÊNCIAS LITERÁRIAS do livro {book_ref}.

📚 **OBRAS QUE INFLUENCIARAM**
Para cada influência identificada:
- Título e autor da obra influenciadora
- Elementos específicos que foram influenciados
- Comparação direta de passagens/temas similares
- Grau de influência (forte, moderada, subtil)

✍️ **INFLUÊNCIAS DO AUTOR**
- Autores que o escritor admitiu admirar
- Movimentos literários que o influenciaram
- Contexto cultural e histórico da época
- Experiências pessoais refletidas na obra

🔗 **INTERTEXTUALIDADE**
- Referências diretas a outras obras
- Alusões e citações
- Diálogos com a tradição literária
- Subversões de convenções de género

🌳 **ÁRVORE GENEALÓGICA LITERÁRIA**
- Predecessores diretos (obras que abriram caminho)
- Contemporâneos com temas similares
- Sucessores (obras que este livro influenciou)

📖 **TRADIÇÃO E INOVAÇÃO**
- O que o livro herdou da tradição
- O que trouxe de novo/original
- Como se posiciona no cânone literário

Identifica pelo menos 5-8 influências significativas.
Escreve em {lang_name} de forma académica mas acessível.""",

            'cultural_impact': f"""Analisa o IMPACTO CULTURAL do livro {book_ref} na sociedade.

🌍 **IMPACTO SOCIAL**
- Mudanças de mentalidade que provocou
- Debates públicos que gerou
- Movimentos sociais que inspirou
- Tabus que quebrou ou questionou

🗣️ **INFLUÊNCIA NA LINGUAGEM**
- Expressões que entraram no vocabulário comum
- Conceitos que o livro popularizou
- Neologismos criados
- Frases que se tornaram icónicas

🎬 **INFLUÊNCIA NA CULTURA POP**
- Referências em filmes, séries, músicas
- Paródias e homenagens
- Memes e cultura da internet
- Merchandising e produtos derivados

📚 **INFLUÊNCIA LITERÁRIA**
- Géneros que ajudou a definir ou popularizar
- Autores que influenciou diretamente
- Obras derivadas (fanfiction, spin-offs)
- Impacto no mercado editorial

🏛️ **IMPACTO POLÍTICO E HISTÓRICO**
- Influência em políticas públicas
- Uso como ferramenta de propaganda ou resistência
- Censura ou controvérsias
- Papel em momentos históricos

📊 **LEGADO DURADOURO**
- Relevância atual (décadas depois)
- Presença em currículos escolares
- Adaptações contínuas
- Comunidades de fãs ativas

Analisa o impacto desde a publicação até hoje.
Escreve em {lang_name} de forma abrangente e documentada.""",

            'critical_reception': f"""Analisa a RECEPÇÃO CRÍTICA do livro {book_ref} ao longo do tempo.

📰 **RECEPÇÃO NA ÉPOCA DE PUBLICAÇÃO**
- Primeiras críticas (positivas e negativas)
- Reação do público leitor
- Vendas iniciais
- Controvérsias imediatas
- Citações de críticos da época

🏆 **PRÉMIOS E RECONHECIMENTOS**
- Prémios literários ganhos
- Nomeações importantes
- Listas de "melhores livros"
- Reconhecimentos académicos

📊 **EVOLUÇÃO DA OPINIÃO CRÍTICA**
- Como a perceção mudou ao longo das décadas
- Reavaliações críticas importantes
- Descoberta ou redescoberta por novas gerações
- Mudanças de status (de ignorado a clássico, ou vice-versa)

👨‍🏫 **ANÁLISE ACADÉMICA**
- Principais interpretações académicas
- Escolas de pensamento que o estudaram
- Teses e dissertações sobre a obra
- Debates académicos que gerou

⚖️ **CRÍTICAS POSITIVAS VS NEGATIVAS**
**Elogios mais comuns:**
- [Lista dos pontos mais elogiados]

**Críticas mais comuns:**
- [Lista das críticas recorrentes]

🌐 **RECEPÇÃO INTERNACIONAL**
- Diferenças de recepção por país/cultura
- Traduções e seu impacto
- Adaptação a diferentes contextos culturais

📈 **SITUAÇÃO ATUAL**
- Opinião crítica contemporânea
- Rating médio em plataformas (Goodreads, etc.)
- Posição atual no cânone literário
- Relevância para leitores de hoje

Inclui citações de críticos quando possível.
Escreve em {lang_name} de forma equilibrada e informativa.""",

            'poem': f"""Cria um POEMA ORIGINAL inspirado no livro {book_ref}.

🎭 **POEMA PRINCIPAL**
Escreve um poema longo e elaborado (20-40 versos) que capture:
- A essência e atmosfera do livro
- Os temas principais
- As emoções centrais
- Referências subtis a personagens e eventos

📝 **ESTILO**
- Usa linguagem poética rica e evocativa
- Inclui metáforas e imagens relacionadas com o livro
- Mantém um ritmo e musicalidade
- Pode rimar ou ser verso livre

✨ **VARIAÇÕES**
Também cria:
1. **Soneto** (14 versos) sobre o tema central
2. **Haiku** (3 versos: 5-7-5 sílabas) sobre o momento mais marcante
3. **Epigrama** (4 versos) com uma reflexão filosófica do livro

Escreve em {lang_name} com sensibilidade poética.""",

            'haiku': f"""Cria um HAIKU para CADA CAPÍTULO do livro {book_ref}.

🍃 **FORMATO HAIKU**
Cada haiku deve ter exatamente 3 linhas:
- Linha 1: 5 sílabas
- Linha 2: 7 sílabas  
- Linha 3: 5 sílabas

📖 **PARA CADA CAPÍTULO**
**Capítulo [X]: [Nome do Capítulo]**
```
[Linha 1 - 5 sílabas]
[Linha 2 - 7 sílabas]
[Linha 3 - 5 sílabas]
```
*[Breve explicação do que o haiku captura]*

---

🎯 **INSTRUÇÕES**
- Cada haiku deve capturar a essência desse capítulo específico
- Usa imagens da natureza quando possível (tradição japonesa)
- Evoca a emoção ou momento-chave do capítulo
- Mantém a contagem silábica rigorosa

Se o livro tiver muitos capítulos, foca nos 10-15 mais importantes.
Escreve em {lang_name}.""",

            'recipes': f"""Cria um LIVRO DE RECEITAS inspirado em {book_ref}.

🍽️ **RECEITAS MENCIONADAS NO LIVRO**
Se existirem comidas/bebidas mencionadas na história:
- Nome do prato
- Contexto em que aparece no livro
- Receita completa (ingredientes + preparação)
- Dica de apresentação

🍳 **RECEITAS INSPIRADAS**
Cria 5-8 receitas originais que combinam com a atmosfera do livro:

Para cada receita:
**🥘 [Nome Criativo da Receita]**
*Inspiração: [Personagem/Cena/Tema que inspirou]*

**Ingredientes:**
- [Lista completa com quantidades]

**Preparação:**
1. [Passos detalhados]

**🍷 Harmonização:** [Bebida que acompanha]
**⏱️ Tempo:** [Preparação + Cozedura]
**👥 Porções:** [Número de pessoas]

---

🎨 **MENU TEMÁTICO**
Sugere um menu completo para um jantar temático do livro:
- Entrada
- Prato principal
- Sobremesa
- Bebidas

Escreve em {lang_name} com detalhes práticos.""",

            'fan_letter': f"""Escreve uma CARTA DE FÃ emocionante ao autor de {book_ref}.

💌 **CARTA PRINCIPAL**
Escreve uma carta sincera e emotiva como se fosses um leitor apaixonado:

Querido/a [Nome do Autor],

[Carta com 4-6 parágrafos incluindo:]
- Como descobriste o livro
- O impacto que teve na tua vida
- Personagens ou passagens favoritas
- Como o livro te mudou ou ensinou algo
- Perguntas que gostarias de fazer ao autor
- Agradecimento final

Com admiração,
Um leitor dedicado

---

✍️ **VARIAÇÕES**
Também escreve:

1. **Carta de uma criança** (se apropriado para o livro)
2. **Carta de um académico** - mais formal e analítica
3. **Carta de agradecimento** - focada num momento específico em que o livro ajudou

📝 **PERGUNTAS AO AUTOR**
Lista 5 perguntas que os fãs gostariam de fazer ao autor sobre:
- Processo criativo
- Inspirações
- Personagens
- Decisões narrativas
- Futuro/continuações

Escreve em {lang_name} com emoção genuína.""",

            'travel_guide': f"""Cria um GUIA DE VIAGEM completo pelos locais do livro {book_ref}.

✈️ **INTRODUÇÃO**
Breve apresentação da "rota literária" e porque vale a pena visitar estes locais.

🗺️ **LOCAIS PRINCIPAIS**
Para cada local importante do livro:

**📍 [Nome do Local]**
- **No livro:** [O que acontece aqui na história]
- **Na realidade:** [Se existe/existiu, informações reais]
- **Como chegar:** [Transportes e acessos]
- **O que ver:** [Pontos de interesse relacionados]
- **Melhor época:** [Quando visitar]
- **Dica do viajante:** [Sugestão especial]

---

🏨 **ROTEIRO SUGERIDO**

**Dia 1: [Título]**
- Manhã: [Atividade]
- Tarde: [Atividade]
- Noite: [Atividade]

**Dia 2: [Título]**
[Continuar...]

---

🍴 **ONDE COMER**
Restaurantes e cafés que combinam com a atmosfera do livro ou que existem nos locais.

🛏️ **ONDE FICAR**
Hotéis ou alojamentos temáticos ou próximos dos locais.

📸 **FOTOS OBRIGATÓRIAS**
Lista de spots para fotografar que recriam cenas do livro.

📚 **DICAS LITERÁRIAS**
- Levar o livro para ler nos locais
- Tours literários organizados (se existirem)
- Museus ou exposições relacionadas

⚠️ **NOTA:** Se os locais são fictícios, sugere locais reais que inspiraram o autor ou que têm atmosfera similar.

Escreve em {lang_name} como um guia de viagem profissional.""",

            'essay': f"""Escreve um ENSAIO ACADÉMICO modelo sobre o livro {book_ref}.

📝 **ESTRUTURA DO ENSAIO**

**TÍTULO**
[Título académico apropriado]

**RESUMO/ABSTRACT** (150-200 palavras)
Síntese do argumento principal e conclusões.

**1. INTRODUÇÃO**
- Contextualização do autor e obra
- Apresentação da tese/argumento central
- Estrutura do ensaio

**2. DESENVOLVIMENTO**

*2.1 Contexto Histórico-Literário*
- Época de publicação
- Movimento literário
- Influências do autor

*2.2 Análise Temática*
- Temas principais
- Subtemas relevantes
- Mensagens implícitas

*2.3 Análise Formal*
- Estrutura narrativa
- Técnicas literárias
- Estilo e linguagem

*2.4 Personagens e Simbolismo*
- Análise dos personagens principais
- Elementos simbólicos
- Significados ocultos

**3. CONCLUSÃO**
- Síntese dos argumentos
- Relevância atual da obra
- Contribuição para a literatura

**REFERÊNCIAS BIBLIOGRÁFICAS**
[Lista de obras citadas em formato académico]

---

📚 **NOTAS**
- Usa linguagem académica formal
- Inclui citações do texto (inventadas mas plausíveis)
- Segue normas de escrita académica
- Extensão: aproximadamente 1500-2000 palavras

Escreve em {lang_name} com rigor académico.""",

            'flashcards': f"""Cria um conjunto de FLASHCARDS de estudo para o livro {book_ref}.

🃏 **FORMATO DOS FLASHCARDS**
Para cada cartão:
```
📌 FRENTE: [Pergunta ou termo]
📖 VERSO: [Resposta ou definição]
```

---

**📚 INFORMAÇÕES BÁSICAS** (5 cartões)
Autor, data, género, contexto, etc.

**👥 PERSONAGENS** (8-10 cartões)
Um cartão por personagem principal com características.

**📖 ENREDO** (8-10 cartões)
Eventos principais em ordem cronológica.

**💡 TEMAS** (5-6 cartões)
Temas principais e sua manifestação na obra.

**🔮 SÍMBOLOS** (4-5 cartões)
Elementos simbólicos e seus significados.

**💬 CITAÇÕES** (5-6 cartões)
Citações importantes e seu contexto/significado.

**📝 ANÁLISE LITERÁRIA** (5-6 cartões)
Técnicas narrativas, estilo, estrutura.

**🎯 PERGUNTAS DE EXAME** (5-6 cartões)
Perguntas típicas de testes/exames sobre a obra.

---

**TOTAL: 45-50 flashcards**

Organiza por categoria com separadores claros.
Escreve em {lang_name} de forma concisa e memorável.""",

            'mind_map': f"""Cria um MAPA MENTAL textual detalhado do livro {book_ref}.

🧩 **ESTRUTURA DO MAPA MENTAL**

```
                            📚 {book_ref}
                                  │
        ┌─────────────┬──────────┼──────────┬─────────────┐
        │             │          │          │             │
   👥 PERSONAGENS  📖 ENREDO  💡 TEMAS  🌍 CENÁRIO  ✍️ ESTILO
        │             │          │          │             │
       ...           ...        ...        ...           ...
```

---

**👥 PERSONAGENS**
```
👥 PERSONAGENS
├── 🦸 Protagonista
│   ├── Nome: [...]
│   ├── Características: [...]
│   ├── Motivação: [...]
│   └── Arco: [...]
├── 😈 Antagonista
│   ├── Nome: [...]
│   └── [...]
├── 🤝 Aliados
│   ├── [Personagem 1]
│   └── [Personagem 2]
└── 👤 Secundários
    └── [...]
```

**📖 ENREDO**
```
📖 ENREDO
├── 🎬 Exposição
│   └── [...]
├── ⬆️ Desenvolvimento
│   ├── Conflito 1: [...]
│   ├── Conflito 2: [...]
│   └── [...]
├── 🔥 Clímax
│   └── [...]
├── ⬇️ Resolução
│   └── [...]
└── 🎭 Desfecho
    └── [...]
```

**💡 TEMAS**
```
💡 TEMAS
├── 🎯 Tema Principal
│   ├── [Descrição]
│   └── Manifestações: [...]
├── 📌 Temas Secundários
│   ├── [Tema 2]
│   ├── [Tema 3]
│   └── [...]
└── 💭 Mensagens
    └── [...]
```

**🌍 CENÁRIO**
```
🌍 CENÁRIO
├── 📍 Locais
│   ├── [Local 1]
│   └── [Local 2]
├── ⏰ Época
│   └── [...]
└── 🎨 Atmosfera
    └── [...]
```

**✍️ ESTILO**
```
✍️ ESTILO
├── 📝 Narrador
│   └── [Tipo]
├── 🗣️ Linguagem
│   └── [Características]
├── 🎭 Técnicas
│   ├── [Técnica 1]
│   └── [Técnica 2]
└── 🔮 Simbolismo
    ├── [Símbolo 1]: [Significado]
    └── [Símbolo 2]: [Significado]
```

**🔗 CONEXÕES**
```
🔗 CONEXÕES IMPORTANTES
├── [Personagem] ←→ [Tema]
├── [Símbolo] ←→ [Significado]
└── [Evento] ←→ [Consequência]
```

Usa ASCII art para criar a estrutura visual.
Escreve em {lang_name} de forma clara e organizada."""
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

Sê informativo, preciso e responde sempre em {lang_name}.
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
6. Responde em {lang_name}
{history_text}
Pergunta do entrevistador: {question}

Resposta de {character}:"""

        elif aspect == 'author_interview':
            # Author interview mode - chat with the author
            author_name = author if author else "o autor"
            history_text = ""
            if history:
                history_text = "\n\nConversa anterior:\n"
                for msg in history[-6:]:
                    role = "Entrevistador" if msg.get('role') == 'user' else author_name
                    history_text += f"{role}: {msg.get('content', '')}\n"
            
            prompt = f"""És {author_name}, o autor do livro {book_ref}.
Responde às perguntas COMO SE FOSSES o próprio autor numa entrevista.

CONTEXTO SOBRE O AUTOR:
- Usa o conhecimento real sobre a biografia, estilo e obras de {author_name}
- Se não souberes informações específicas, improvisa de forma coerente com o que se sabe
- Mantém o tom e personalidade que o autor demonstra em entrevistas reais

INSTRUÇÕES:
1. Responde SEMPRE na primeira pessoa, como {author_name}
2. Fala sobre o processo criativo, inspirações e decisões ao escrever {book_ref}
3. Partilha anedotas e histórias sobre a escrita do livro
4. Discute os temas, personagens e mensagens que quiseste transmitir
5. Menciona outras obras tuas quando relevante
6. Sê autêntico ao estilo de comunicação do autor
7. Se perguntarem sobre a tua vida pessoal, responde de forma apropriada
8. Responde em {lang_name}
{history_text}
Pergunta do entrevistador: {question}

Resposta de {author_name}:"""

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

            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(prompt)
            text = response.text.strip()
            
            if text.startswith('```'):
                text = text.split('\n', 1)[1].rsplit('```', 1)[0]
            
            import json
            questions = json.loads(text)
            
            # Save quiz to analysis history
            if current_user.is_authenticated:
                try:
                    analysis = AnalysisHistory(
                        user_id=current_user.id,
                        book_title=title,
                        book_author=author if author else None,
                        aspect='quiz',
                        language=language,
                        response_preview=f"Quiz com {len(questions)} perguntas"
                    )
                    db.session.add(analysis)
                    db.session.commit()
                except Exception as hist_error:
                    logger.warning(f"Error saving quiz history: {hist_error}")
            
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
        
        # Check cache for static aspects (not interactive ones)
        cacheable_aspects = ['info', 'summary', 'characters', 'themes', 'world', 'style', 'quotes', 'similar', 'trivia', 'timeline', 'symbolism', 'adaptation', 'psychological', 'influences', 'cultural_impact', 'critical_reception', 'poem', 'haiku', 'recipes', 'fan_letter', 'travel_guide', 'essay', 'flashcards', 'mind_map']
        content = None
        
        if aspect in cacheable_aspects:
            content = get_cached_ai_response(title, author, aspect, language)
            if content:
                logger.debug(f"Cache hit for {aspect}: {title}")
        
        if not content:
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(prompt)
            content = response.text.strip()
            
            # Cache static responses for 1 hour
            if aspect in cacheable_aspects:
                cache_ai_response(title, author, aspect, language, content, timeout=3600)
        
        # Save to analysis history for authenticated users
        if current_user.is_authenticated:
            try:
                analysis = AnalysisHistory(
                    user_id=current_user.id,
                    book_title=title,
                    book_author=author if author else None,
                    aspect=aspect,
                    language=language,
                    response_preview=content[:500] if content else None
                )
                db.session.add(analysis)
                db.session.commit()
            except Exception as hist_error:
                logger.warning(f"Error saving analysis history: {hist_error}")
                # Don't fail the request if history save fails
        
        result = {'success': True, 'content': content}
        
        # For info aspect, try to extract genre
        if aspect == 'info':
            result['genre'] = content.split('\n')[0] if content else ''
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Explorer error: {e}")
        return jsonify({'success': False, 'error': 'Erro ao processar pedido. Tente novamente.'}), 500

# ==================== PUBLIC DOMAIN BOOK READING ====================

from utils.gutenberg import check_book_availability, get_book_text, search_gutenberg, is_public_domain

@app.route('/api/book/check-availability', methods=['POST'])
def check_book_reading_availability():
    """Check if a book is available for free reading (public domain)"""
    try:
        data = request.get_json() or {}
        title = (data.get('title') or '').strip()
        author = (data.get('author') or '').strip()
        
        if not title:
            return jsonify({'success': False, 'error': 'Título obrigatório'}), 400
        
        result = check_book_availability(title, author)
        
        return jsonify({
            'success': True,
            **result
        })
        
    except Exception as e:
        logger.warning(f"Check availability error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/book/read', methods=['POST'])
def get_book_for_reading():
    """Get full book text for reading (public domain only)"""
    try:
        data = request.get_json() or {}
        gutenberg_id = data.get('gutenberg_id')
        title = (data.get('title') or '').strip()
        author = (data.get('author') or '').strip()
        
        # If no ID provided, search for it
        if not gutenberg_id:
            availability = check_book_availability(title, author)
            if not availability.get('available'):
                return jsonify({
                    'success': False,
                    'error': availability.get('message', 'Livro não disponível para leitura gratuita')
                }), 404
            gutenberg_id = availability.get('gutenberg_id')
        
        if not gutenberg_id:
            return jsonify({'success': False, 'error': 'Livro não encontrado'}), 404
        
        # Get the book text
        result = get_book_text(gutenberg_id)
        
        if not result.get('success'):
            return jsonify({
                'success': False,
                'error': result.get('error', 'Erro ao obter texto do livro')
            }), 500
        
        return jsonify({
            'success': True,
            'text': result['text'],
            'chapters': result['chapters'],
            'metadata': result['metadata'],
            'word_count': result['word_count'],
            'source': result['source']
        })
        
    except Exception as e:
        logger.warning(f"Get book text error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/read-book')
def read_public_book_page():
    """Reading page for public domain books"""
    title = request.args.get('title', '')
    author = request.args.get('author', '')
    gutenberg_id = request.args.get('id', '')
    
    return render_template('read_public_book.html', 
                         title=title, 
                         author=author,
                         gutenberg_id=gutenberg_id)


@app.route('/api/gutenberg/search', methods=['GET'])
def search_gutenberg_books():
    """Search Project Gutenberg for books"""
    try:
        query = request.args.get('q', '').strip()
        language = request.args.get('lang', 'en')
        
        if not query:
            return jsonify({'success': False, 'error': 'Query obrigatória'}), 400
        
        results = search_gutenberg(query, language=language)
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        logger.warning(f"Gutenberg search error: {e}")
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

        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        
        return jsonify({
            'success': True,
            'response': response.text.strip(),
            'character': character_name
        })
        
    except Exception as e:
        logger.warning(f"Interview error: {e}")
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

        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        
        import json
        text = response.text.strip()
        # Clean up response
        if text.startswith('```'):
            text = text.split('\n', 1)[1].rsplit('```', 1)[0]
        
        char_list = json.loads(text)
        return jsonify({'success': True, 'characters': char_list})
        
    except Exception as e:
        logger.warning(f"Characters list error: {e}")
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

        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        
        return jsonify({
            'success': True,
            'continuation': response.text.strip(),
            'type': continuation_type
        })
        
    except Exception as e:
        logger.warning(f"Continue story error: {e}")
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

        model = genai.GenerativeModel("gemini-2.5-flash")
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
        logger.warning(f"Quiz JSON error: {e}")
        return jsonify({'success': False, 'error': 'Erro ao gerar quiz. Tente novamente.'}), 500
    except Exception as e:
        logger.warning(f"Quiz error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== ADMIN DASHBOARD ====================

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Admin dashboard with metrics"""
    from sqlalchemy import func
    from datetime import timedelta
    
    # Date ranges
    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # User metrics
    total_users = User.query.count()
    users_today = User.query.filter(func.date(User.created_at) == today).count()
    users_week = User.query.filter(User.created_at >= week_ago).count()
    users_month = User.query.filter(User.created_at >= month_ago).count()
    
    # Users by plan
    users_free = User.query.filter_by(plan='free').count()
    users_pro = User.query.filter_by(plan='pro').count()
    users_premium = User.query.filter_by(plan='premium').count()
    
    # Active users (logged in last 7 days)
    active_users = User.query.filter(User.last_login >= week_ago).count()
    
    # Book/Analysis metrics
    total_books = Book.query.count()
    total_analyses = AnalysisHistory.query.count() if AnalysisHistory else 0
    
    # Most analyzed books (by title from AnalysisHistory)
    top_books = db.session.query(
        AnalysisHistory.book_title.label('title'),
        AnalysisHistory.book_author.label('theme'),
        func.count(AnalysisHistory.id).label('analysis_count')
    ).group_by(AnalysisHistory.book_title, AnalysisHistory.book_author)\
     .order_by(func.count(AnalysisHistory.id).desc())\
     .limit(10).all() if AnalysisHistory else []
    
    # Most used features
    feature_counts = db.session.query(
        AnalysisHistory.aspect.label('analysis_type'),
        func.count(AnalysisHistory.id).label('count')
    ).group_by(AnalysisHistory.aspect)\
     .order_by(func.count(AnalysisHistory.id).desc())\
     .limit(10).all() if AnalysisHistory else []
    
    # Conversion metrics
    conversion_rate = round((users_pro + users_premium) / total_users * 100, 2) if total_users > 0 else 0
    
    # Recent users
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    
    # Usage stats (total usage across all users)
    total_usage = db.session.query(func.sum(User.usage_count)).scalar() or 0
    
    # Daily registrations for chart (last 30 days)
    daily_registrations = db.session.query(
        func.date(User.created_at).label('date'),
        func.count(User.id).label('count')
    ).filter(User.created_at >= month_ago)\
     .group_by(func.date(User.created_at))\
     .order_by(func.date(User.created_at)).all()
    
    return render_template('admin/dashboard.html',
        total_users=total_users,
        users_today=users_today,
        users_week=users_week,
        users_month=users_month,
        users_free=users_free,
        users_pro=users_pro,
        users_premium=users_premium,
        active_users=active_users,
        total_books=total_books,
        total_analyses=total_analyses,
        top_books=top_books,
        feature_counts=feature_counts,
        conversion_rate=conversion_rate,
        recent_users=recent_users,
        total_usage=total_usage,
        daily_registrations=daily_registrations
    )

@app.route('/api/admin/metrics')
@admin_required
def admin_metrics_api():
    """API endpoint for admin metrics (for AJAX updates)"""
    from sqlalchemy import func
    from datetime import timedelta
    
    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)
    
    return jsonify({
        'success': True,
        'metrics': {
            'total_users': User.query.count(),
            'active_users': User.query.filter(User.last_login >= week_ago).count(),
            'total_books': Book.query.count(),
            'users_by_plan': {
                'free': User.query.filter_by(plan='free').count(),
                'pro': User.query.filter_by(plan='pro').count(),
                'premium': User.query.filter_by(plan='premium').count()
            }
        }
    })

@app.route('/api/admin/users')
@admin_required
def admin_users_api():
    """Search and list users"""
    from sqlalchemy import func, or_
    
    search = request.args.get('search', '').strip()
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    plan_filter = request.args.get('plan', '')
    
    query = User.query
    
    if search:
        query = query.filter(or_(
            User.email.ilike(f'%{search}%'),
            User.name.ilike(f'%{search}%')
        ))
    
    if plan_filter:
        query = query.filter_by(plan=plan_filter)
    
    total = query.count()
    users = query.order_by(User.created_at.desc()).offset((page-1)*per_page).limit(per_page).all()
    
    return jsonify({
        'success': True,
        'users': [u.to_dict() for u in users],
        'total': total,
        'page': page,
        'pages': (total + per_page - 1) // per_page
    })

@app.route('/api/admin/user/<int:user_id>', methods=['GET', 'PUT', 'DELETE'])
@admin_required
def admin_user_detail(user_id):
    """Get, update or delete a user"""
    user = User.query.get_or_404(user_id)
    
    if request.method == 'GET':
        return jsonify({'success': True, 'user': user.to_dict()})
    
    elif request.method == 'PUT':
        data = request.json
        if 'plan' in data:
            user.plan = data['plan']
        if 'is_active' in data:
            user.is_active = data['is_active']
        if 'is_admin' in data:
            user.is_admin = data['is_admin']
        if 'usage_count' in data:
            user.usage_count = data['usage_count']
        db.session.commit()
        return jsonify({'success': True, 'message': 'Utilizador atualizado'})
    
    elif request.method == 'DELETE':
        if user.is_admin:
            return jsonify({'success': False, 'error': 'Não pode eliminar um admin'}), 400
        db.session.delete(user)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Utilizador eliminado'})

@app.route('/api/admin/daily-usage')
@admin_required
def admin_daily_usage():
    """Get daily usage stats for chart"""
    from sqlalchemy import func
    from datetime import timedelta
    
    days = int(request.args.get('days', 30))
    start_date = datetime.utcnow().date() - timedelta(days=days)
    
    daily_analyses = db.session.query(
        func.date(AnalysisHistory.created_at).label('date'),
        func.count(AnalysisHistory.id).label('count')
    ).filter(AnalysisHistory.created_at >= start_date)\
     .group_by(func.date(AnalysisHistory.created_at))\
     .order_by(func.date(AnalysisHistory.created_at)).all()
    
    return jsonify({
        'success': True,
        'data': [{'date': str(d.date), 'count': d.count} for d in daily_analyses]
    })

# ==================== PUSH NOTIFICATIONS API ====================

VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY', 'BPYVgcwG299uWv3SpiSs5DIiAyFZhX0N9vaDMYZDIqT6MdiMs7fzoOFI-MUD4xRp8vJjzmFhS3wK_31_J8E2scM')
VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY', 'MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQg/pRTL66oMme+8V9GPYNcIb3SnCUk2URRWG5n5g4pKNqhRANCAAT2FYHMBtvfblr90qYkrOQyIgMhWYV9Dfb2gzGGQyKk+jHYjLO386DhSPjFA+MUafLyY85hYUt8Cv99fyfBNrHD')
VAPID_CLAIMS = {'sub': 'mailto:admin@bookcreatorai.com'}

@app.route('/api/notifications/vapid-key')
def notifications_vapid_key():
    return jsonify({'success': True, 'publicKey': VAPID_PUBLIC_KEY})

@app.route('/api/notifications/subscribe', methods=['POST'])
@login_required
def notifications_subscribe():
    data = request.get_json()
    subscription = data.get('subscription', {})
    endpoint = subscription.get('endpoint')
    if not endpoint:
        return jsonify({'success': False, 'error': 'No endpoint'})
    existing = PushSubscription.query.filter_by(user_id=current_user.id, endpoint=endpoint).first()
    if not existing:
        sub = PushSubscription(
            user_id=current_user.id,
            endpoint=endpoint,
            p256dh_key=subscription.get('keys', {}).get('p256dh', ''),
            auth_key=subscription.get('keys', {}).get('auth', '')
        )
        db.session.add(sub)
        db.session.commit()
    return jsonify({'success': True})

@app.route('/api/notifications/unsubscribe', methods=['POST'])
@login_required
def notifications_unsubscribe():
    data = request.get_json()
    endpoint = data.get('endpoint')
    if endpoint:
        PushSubscription.query.filter_by(user_id=current_user.id, endpoint=endpoint).delete()
        db.session.commit()
    return jsonify({'success': True})

@app.route('/api/notifications/preferences', methods=['POST'])
@login_required
def notifications_preferences():
    return jsonify({'success': True})

@app.route('/api/admin/revenue')
@admin_required
def admin_revenue():
    """Get revenue metrics"""
    from models.book import PLAN_CONFIG
    
    users_pro = User.query.filter_by(plan='pro', subscription_status='active').count()
    users_premium = User.query.filter_by(plan='premium', subscription_status='active').count()
    
    mrr_pro = users_pro * PLAN_CONFIG['pro']['price_monthly']
    mrr_premium = users_premium * PLAN_CONFIG['premium']['price_monthly']
    mrr_total = mrr_pro + mrr_premium
    
    total_paying = users_pro + users_premium
    total_users = User.query.count()
    arpu = mrr_total / total_users if total_users > 0 else 0
    
    return jsonify({
        'success': True,
        'revenue': {
            'mrr': round(mrr_total, 2),
            'mrr_pro': round(mrr_pro, 2),
            'mrr_premium': round(mrr_premium, 2),
            'paying_users': total_paying,
            'arpu': round(arpu, 2),
            'arr': round(mrr_total * 12, 2)
        }
    })

@app.route('/api/admin/export-csv')
@admin_required
def admin_export_csv():
    """Export users to CSV"""
    import csv
    from io import StringIO
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['ID', 'Nome', 'Email', 'Plano', 'Uso', 'Status', 'Criado', 'Último Login'])
    
    # Data
    users = User.query.order_by(User.created_at.desc()).all()
    for u in users:
        writer.writerow([
            u.id,
            u.name,
            u.email,
            u.plan,
            u.usage_count,
            'Ativo' if u.is_active else 'Inativo',
            u.created_at.strftime('%Y-%m-%d %H:%M'),
            u.last_login.strftime('%Y-%m-%d %H:%M') if u.last_login else 'Nunca'
        ])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=utilizadores.csv'}
    )

@app.route('/api/admin/send-notification', methods=['POST'])
@admin_required
def admin_send_notification():
    """Send notification to all users or specific user"""
    data = request.json
    title = data.get('title', '')
    message = data.get('message', '')
    user_id = data.get('user_id')  # Optional, if None sends to all
    
    if not title or not message:
        return jsonify({'success': False, 'error': 'Título e mensagem são obrigatórios'}), 400
    
    try:
        if user_id:
            # Send to specific user
            subscriptions = PushSubscription.query.filter_by(user_id=user_id, is_active=True).all()
        else:
            # Send to all
            subscriptions = PushSubscription.query.filter_by(is_active=True).all()
        
        sent_count = 0
        for sub in subscriptions:
            try:
                notification = Notification(
                    user_id=sub.user_id,
                    title=title,
                    message=message,
                    notification_type='admin'
                )
                db.session.add(notification)
                sent_count += 1
            except:
                pass
        
        db.session.commit()
        return jsonify({'success': True, 'sent': sent_count})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/growth')
@admin_required
def admin_growth():
    """Get month-over-month growth comparison"""
    from sqlalchemy import func
    from datetime import timedelta
    
    today = datetime.utcnow().date()
    this_month_start = today.replace(day=1)
    last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
    last_month_end = this_month_start - timedelta(days=1)
    
    # Users this month vs last month
    users_this_month = User.query.filter(User.created_at >= this_month_start).count()
    users_last_month = User.query.filter(
        User.created_at >= last_month_start,
        User.created_at < this_month_start
    ).count()
    
    # Analyses this month vs last month
    analyses_this_month = AnalysisHistory.query.filter(AnalysisHistory.created_at >= this_month_start).count()
    analyses_last_month = AnalysisHistory.query.filter(
        AnalysisHistory.created_at >= last_month_start,
        AnalysisHistory.created_at < this_month_start
    ).count()
    
    # Calculate growth percentages
    user_growth = ((users_this_month - users_last_month) / users_last_month * 100) if users_last_month > 0 else 100
    analysis_growth = ((analyses_this_month - analyses_last_month) / analyses_last_month * 100) if analyses_last_month > 0 else 100
    
    return jsonify({
        'success': True,
        'growth': {
            'users_this_month': users_this_month,
            'users_last_month': users_last_month,
            'user_growth': round(user_growth, 1),
            'analyses_this_month': analyses_this_month,
            'analyses_last_month': analyses_last_month,
            'analysis_growth': round(analysis_growth, 1)
        }
    })

@app.route('/api/admin/promo-codes', methods=['GET', 'POST'])
@admin_required
def admin_promo_codes():
    """List or create promo codes"""
    if request.method == 'GET':
        codes = PromoCode.query.order_by(PromoCode.created_at.desc()).all()
        return jsonify({'success': True, 'codes': [c.to_dict() for c in codes]})
    
    elif request.method == 'POST':
        data = request.json
        code = data.get('code', '').upper().strip()
        
        if not code:
            return jsonify({'success': False, 'error': 'Código é obrigatório'}), 400
        
        if PromoCode.query.filter_by(code=code).first():
            return jsonify({'success': False, 'error': 'Código já existe'}), 400
        
        valid_until = None
        if data.get('valid_until'):
            valid_until = datetime.strptime(data['valid_until'], '%Y-%m-%d')
        
        promo = PromoCode(
            code=code,
            discount_percent=int(data.get('discount_percent', 10)),
            discount_type=data.get('discount_type', 'percent'),
            max_uses=int(data.get('max_uses', 100)),
            valid_until=valid_until,
            applies_to=data.get('applies_to', 'all'),
            created_by=current_user.id
        )
        db.session.add(promo)
        db.session.commit()
        
        return jsonify({'success': True, 'code': promo.to_dict()})

@app.route('/api/admin/promo-codes/<int:code_id>', methods=['PUT', 'DELETE'])
@admin_required
def admin_promo_code_detail(code_id):
    """Update or delete a promo code"""
    promo = PromoCode.query.get_or_404(code_id)
    
    if request.method == 'PUT':
        data = request.json
        if 'is_active' in data:
            promo.is_active = data['is_active']
        if 'max_uses' in data:
            promo.max_uses = data['max_uses']
        db.session.commit()
        return jsonify({'success': True, 'code': promo.to_dict()})
    
    elif request.method == 'DELETE':
        db.session.delete(promo)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Código eliminado'})

@app.route('/api/admin/errors')
@admin_required
def admin_errors():
    """Get error logs"""
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    
    query = ErrorLog.query.order_by(ErrorLog.created_at.desc())
    total = query.count()
    errors = query.offset((page-1)*per_page).limit(per_page).all()
    
    return jsonify({
        'success': True,
        'errors': [e.to_dict() for e in errors],
        'total': total,
        'page': page
    })

@app.route('/api/admin/errors/<int:error_id>', methods=['PUT', 'DELETE'])
@admin_required
def admin_error_detail(error_id):
    """Mark error as resolved or delete"""
    error = ErrorLog.query.get_or_404(error_id)
    
    if request.method == 'PUT':
        error.is_resolved = True
        db.session.commit()
        return jsonify({'success': True})
    
    elif request.method == 'DELETE':
        db.session.delete(error)
        db.session.commit()
        return jsonify({'success': True})

@app.route('/api/admin/users-by-language')
@admin_required
def admin_users_by_language():
    """Get users grouped by preferred language"""
    from sqlalchemy import func
    
    # Count analyses by language as proxy for user language preference
    lang_counts = db.session.query(
        AnalysisHistory.language,
        func.count(func.distinct(AnalysisHistory.user_id)).label('count')
    ).group_by(AnalysisHistory.language).all()
    
    return jsonify({
        'success': True,
        'languages': [{'language': l.language or 'pt-pt', 'count': l.count} for l in lang_counts]
    })

# Error handler to log errors
@app.errorhandler(500)
def handle_500_error(e):
    try:
        error_log = ErrorLog(
            error_type='500 Internal Server Error',
            error_message=str(e),
            endpoint=request.path if request else None,
            user_id=current_user.id if current_user.is_authenticated else None,
            ip_address=request.remote_addr if request else None,
            user_agent=request.user_agent.string if request else None
        )
        db.session.add(error_log)
        db.session.commit()
    except:
        pass
    return jsonify({'error': 'Internal server error'}), 500

# ==================== ADVANCED ADMIN APIs ====================

@app.route('/api/admin/analytics')
@admin_required
def admin_analytics():
    """Get advanced analytics: churn, retention, funnel"""
    from sqlalchemy import func
    from datetime import timedelta
    
    today = datetime.utcnow().date()
    month_ago = today - timedelta(days=30)
    week_ago = today - timedelta(days=7)
    
    # Churn rate (users who canceled subscription)
    total_ever_paid = User.query.filter(User.plan.in_(['pro', 'premium'])).count() + \
                      User.query.filter(User.subscription_status == 'canceled').count()
    canceled = User.query.filter_by(subscription_status='canceled').count()
    churn_rate = (canceled / total_ever_paid * 100) if total_ever_paid > 0 else 0
    
    # Retention (users who logged in last 7 days / total active users)
    total_active = User.query.filter_by(is_active=True).count()
    returned = User.query.filter(User.last_login >= week_ago, User.is_active == True).count()
    retention_rate = (returned / total_active * 100) if total_active > 0 else 0
    
    # Conversion funnel
    total_users = User.query.count()
    free_users = User.query.filter_by(plan='free').count()
    pro_users = User.query.filter_by(plan='pro').count()
    premium_users = User.query.filter_by(plan='premium').count()
    
    return jsonify({
        'success': True,
        'analytics': {
            'churn_rate': round(churn_rate, 2),
            'retention_rate': round(retention_rate, 2),
            'funnel': {
                'total': total_users,
                'free': free_users,
                'pro': pro_users,
                'premium': premium_users,
                'free_to_pro': round((pro_users / free_users * 100) if free_users > 0 else 0, 2),
                'pro_to_premium': round((premium_users / pro_users * 100) if pro_users > 0 else 0, 2)
            }
        }
    })

@app.route('/api/admin/payments')
@admin_required
def admin_payments():
    """Get payment history from SubscriptionHistory"""
    page = int(request.args.get('page', 1))
    per_page = 20
    
    payments = SubscriptionHistory.query.order_by(SubscriptionHistory.created_at.desc())\
        .offset((page-1)*per_page).limit(per_page).all()
    total = SubscriptionHistory.query.count()
    
    return jsonify({
        'success': True,
        'payments': [p.to_dict() for p in payments],
        'total': total,
        'page': page
    })

@app.route('/api/admin/revenue-forecast')
@admin_required
def admin_revenue_forecast():
    """Forecast revenue based on trends"""
    from sqlalchemy import func
    from datetime import timedelta
    
    # Current MRR
    users_pro = User.query.filter_by(plan='pro', subscription_status='active').count()
    users_premium = User.query.filter_by(plan='premium', subscription_status='active').count()
    current_mrr = users_pro * PLAN_CONFIG['pro']['price_monthly'] + users_premium * PLAN_CONFIG['premium']['price_monthly']
    
    # Growth rate (new paying users this month vs last month)
    today = datetime.utcnow().date()
    this_month = today.replace(day=1)
    last_month = (this_month - timedelta(days=1)).replace(day=1)
    
    new_this_month = User.query.filter(
        User.created_at >= this_month,
        User.plan.in_(['pro', 'premium'])
    ).count()
    new_last_month = User.query.filter(
        User.created_at >= last_month,
        User.created_at < this_month,
        User.plan.in_(['pro', 'premium'])
    ).count()
    
    growth_rate = ((new_this_month - new_last_month) / new_last_month) if new_last_month > 0 else 0.1
    
    # Forecast next 6 months
    forecast = []
    mrr = current_mrr
    for i in range(1, 7):
        mrr = mrr * (1 + growth_rate * 0.5)  # Conservative growth
        forecast.append({'month': i, 'mrr': round(mrr, 2)})
    
    return jsonify({
        'success': True,
        'forecast': {
            'current_mrr': round(current_mrr, 2),
            'growth_rate': round(growth_rate * 100, 2),
            'next_6_months': forecast
        }
    })

@app.route('/api/admin/email-templates', methods=['GET', 'POST'])
@admin_required
def admin_email_templates():
    """Manage email templates"""
    if request.method == 'GET':
        templates = EmailTemplate.query.order_by(EmailTemplate.created_at.desc()).all()
        return jsonify({'success': True, 'templates': [t.to_dict() for t in templates]})
    
    elif request.method == 'POST':
        data = request.json
        template = EmailTemplate(
            name=data.get('name'),
            subject=data.get('subject'),
            body=data.get('body'),
            template_type=data.get('template_type', 'general'),
            created_by=current_user.id
        )
        db.session.add(template)
        db.session.commit()
        return jsonify({'success': True, 'template': template.to_dict()})

@app.route('/api/admin/email-templates/<int:template_id>', methods=['DELETE'])
@admin_required
def admin_email_template_delete(template_id):
    template = EmailTemplate.query.get_or_404(template_id)
    db.session.delete(template)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/admin/scheduled-notifications', methods=['GET', 'POST'])
@admin_required
def admin_scheduled_notifications():
    """Manage scheduled notifications"""
    if request.method == 'GET':
        notifs = ScheduledNotification.query.order_by(ScheduledNotification.scheduled_for.desc()).all()
        return jsonify({'success': True, 'notifications': [n.to_dict() for n in notifs]})
    
    elif request.method == 'POST':
        data = request.json
        scheduled_for = datetime.strptime(data.get('scheduled_for'), '%Y-%m-%dT%H:%M')
        notif = ScheduledNotification(
            title=data.get('title'),
            message=data.get('message'),
            scheduled_for=scheduled_for,
            target_segment=data.get('target_segment', 'all'),
            created_by=current_user.id
        )
        db.session.add(notif)
        db.session.commit()
        return jsonify({'success': True, 'notification': notif.to_dict()})

@app.route('/api/admin/scheduled-notifications/<int:notif_id>', methods=['DELETE'])
@admin_required
def admin_scheduled_notification_delete(notif_id):
    notif = ScheduledNotification.query.get_or_404(notif_id)
    db.session.delete(notif)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/admin/goals', methods=['GET', 'POST'])
@admin_required
def admin_goals():
    """Manage admin goals"""
    if request.method == 'GET':
        # Update current values
        goals = AdminGoal.query.filter_by(is_completed=False).all()
        for goal in goals:
            if goal.goal_type == 'users':
                goal.current_value = User.query.count()
            elif goal.goal_type == 'revenue':
                users_pro = User.query.filter_by(plan='pro', subscription_status='active').count()
                users_premium = User.query.filter_by(plan='premium', subscription_status='active').count()
                goal.current_value = int(users_pro * PLAN_CONFIG['pro']['price_monthly'] + users_premium * PLAN_CONFIG['premium']['price_monthly'])
            elif goal.goal_type == 'analyses':
                goal.current_value = AnalysisHistory.query.count()
            
            if goal.current_value >= goal.target_value and not goal.is_completed:
                goal.is_completed = True
                goal.completed_at = datetime.utcnow()
        db.session.commit()
        
        all_goals = AdminGoal.query.order_by(AdminGoal.created_at.desc()).all()
        return jsonify({'success': True, 'goals': [g.to_dict() for g in all_goals]})
    
    elif request.method == 'POST':
        data = request.json
        deadline = datetime.strptime(data.get('deadline'), '%Y-%m-%d') if data.get('deadline') else None
        goal = AdminGoal(
            title=data.get('title'),
            goal_type=data.get('goal_type'),
            target_value=int(data.get('target_value')),
            deadline=deadline
        )
        db.session.add(goal)
        db.session.commit()
        return jsonify({'success': True, 'goal': goal.to_dict()})

@app.route('/api/admin/goals/<int:goal_id>', methods=['DELETE'])
@admin_required
def admin_goal_delete(goal_id):
    goal = AdminGoal.query.get_or_404(goal_id)
    db.session.delete(goal)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/admin/login-logs')
@admin_required
def admin_login_logs():
    """Get login history"""
    page = int(request.args.get('page', 1))
    per_page = 30
    
    logs = LoginLog.query.order_by(LoginLog.created_at.desc())\
        .offset((page-1)*per_page).limit(per_page).all()
    total = LoginLog.query.count()
    
    # Enrich with user info
    result = []
    for log in logs:
        data = log.to_dict()
        user = User.query.get(log.user_id)
        data['user_email'] = user.email if user else 'Desconhecido'
        result.append(data)
    
    return jsonify({'success': True, 'logs': result, 'total': total})

@app.route('/api/admin/blocked-ips', methods=['GET', 'POST'])
@admin_required
def admin_blocked_ips():
    """Manage blocked IPs"""
    if request.method == 'GET':
        ips = BlockedIP.query.order_by(BlockedIP.blocked_at.desc()).all()
        return jsonify({'success': True, 'ips': [ip.to_dict() for ip in ips]})
    
    elif request.method == 'POST':
        data = request.json
        ip = data.get('ip_address')
        if BlockedIP.query.filter_by(ip_address=ip).first():
            return jsonify({'success': False, 'error': 'IP já bloqueado'}), 400
        
        expires_at = None
        if data.get('expires_at'):
            expires_at = datetime.strptime(data['expires_at'], '%Y-%m-%d')
        
        blocked = BlockedIP(
            ip_address=ip,
            reason=data.get('reason'),
            blocked_by=current_user.id,
            expires_at=expires_at
        )
        db.session.add(blocked)
        db.session.commit()
        return jsonify({'success': True, 'ip': blocked.to_dict()})

@app.route('/api/admin/blocked-ips/<int:ip_id>', methods=['DELETE'])
@admin_required
def admin_blocked_ip_delete(ip_id):
    ip = BlockedIP.query.get_or_404(ip_id)
    db.session.delete(ip)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/admin/admins', methods=['GET', 'POST'])
@admin_required
def admin_manage_admins():
    """Manage admin users"""
    if request.method == 'GET':
        admins = User.query.filter_by(is_admin=True).all()
        return jsonify({'success': True, 'admins': [{'id': a.id, 'name': a.name, 'email': a.email} for a in admins]})
    
    elif request.method == 'POST':
        data = request.json
        user = User.query.filter_by(email=data.get('email')).first()
        if not user:
            return jsonify({'success': False, 'error': 'Utilizador não encontrado'}), 404
        user.is_admin = True
        db.session.commit()
        return jsonify({'success': True, 'message': f'{user.name} é agora admin'})

@app.route('/api/admin/admins/<int:user_id>', methods=['DELETE'])
@admin_required
def admin_remove_admin(user_id):
    if user_id == current_user.id:
        return jsonify({'success': False, 'error': 'Não pode remover-se a si próprio'}), 400
    user = User.query.get_or_404(user_id)
    user.is_admin = False
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/admin/export-pdf')
@admin_required
def admin_export_pdf():
    """Generate PDF report"""
    from io import BytesIO
    
    # Simple HTML to PDF approach
    total_users = User.query.count()
    users_pro = User.query.filter_by(plan='pro').count()
    users_premium = User.query.filter_by(plan='premium').count()
    total_analyses = AnalysisHistory.query.count()
    
    mrr = users_pro * PLAN_CONFIG['pro']['price_monthly'] + users_premium * PLAN_CONFIG['premium']['price_monthly']
    
    html_content = f"""
    <html>
    <head><title>Relatório Admin - Alma do Livro</title>
    <style>body{{font-family:Arial;padding:40px;}}h1{{color:#8b5cf6;}}table{{width:100%;border-collapse:collapse;margin:20px 0;}}th,td{{border:1px solid #ddd;padding:12px;text-align:left;}}th{{background:#8b5cf6;color:white;}}</style>
    </head>
    <body>
    <h1>📊 Relatório Admin - Alma do Livro</h1>
    <p>Gerado em: {datetime.utcnow().strftime('%d/%m/%Y %H:%M')}</p>
    <h2>Métricas Principais</h2>
    <table>
    <tr><th>Métrica</th><th>Valor</th></tr>
    <tr><td>Total de Utilizadores</td><td>{total_users}</td></tr>
    <tr><td>Utilizadores Pro</td><td>{users_pro}</td></tr>
    <tr><td>Utilizadores Premium</td><td>{users_premium}</td></tr>
    <tr><td>Total de Análises</td><td>{total_analyses}</td></tr>
    <tr><td>MRR (Receita Mensal)</td><td>€{mrr:.2f}</td></tr>
    <tr><td>ARR (Receita Anual)</td><td>€{mrr*12:.2f}</td></tr>
    </table>
    </body></html>
    """
    
    return Response(
        html_content,
        mimetype='text/html',
        headers={'Content-Disposition': 'attachment; filename=relatorio_admin.html'}
    )

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
