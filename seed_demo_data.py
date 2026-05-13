"""
Script para criar dados de demonstração para gravação de vídeo.
Cria um utilizador demo com plano Pro e histórico de análises atrativo.

Uso: python seed_demo_data.py
"""

import os
import sys
from datetime import datetime, timedelta

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, bcrypt
from models.book import db, User, AnalysisHistory, Favorite

# Configuração do utilizador demo
DEMO_USER = {
    'email': 'demo@almadolivro.pt',
    'password': 'Demo2024!',
    'name': 'Maria Silva',
    'plan': 'pro',  # Para mostrar todas as funcionalidades
    'usage_count': 23,  # Uso moderado para parecer real
}

# Livros para o histórico de análises (variedade atrativa)
DEMO_BOOKS = [
    {
        'title': '1984',
        'author': 'George Orwell',
        'aspects': ['summary', 'characters', 'themes', 'symbolism', 'quiz'],
        'preview_summary': 'Em 1984, George Orwell apresenta-nos um futuro distópico onde o totalitarismo atinge o seu extremo. Winston Smith, funcionário do Ministério da Verdade, vive sob a vigilância constante do Grande Irmão...',
        'preview_characters': 'Winston Smith é o protagonista, um homem de 39 anos que trabalha no Ministério da Verdade, alterando registos históricos. Julia é uma jovem rebelde que se torna sua amante. O Grande Irmão é a figura omnipresente do Partido...',
    },
    {
        'title': 'O Senhor dos Anéis: A Irmandade do Anel',
        'author': 'J.R.R. Tolkien',
        'aspects': ['summary', 'world', 'characters', 'playlist'],
        'preview_summary': 'Frodo Baggins, um jovem hobbit da comarca, herda de seu tio Bilbo um anel misterioso. Gandalf, o feiticeiro cinzento, descobre que este é o Um Anel, forjado pelo Senhor das Trevas Sauron...',
        'preview_world': 'A Terra-Média é um continente fictício repleto de raças distintas: Hobbits no Shire, Elfos em Rivendell e Lothlórien, Anões nas Montanhas Nebulosas, e Homens em Gondor e Rohan...',
    },
    {
        'title': 'Harry Potter e a Pedra Filosofal',
        'author': 'J.K. Rowling',
        'aspects': ['summary', 'characters', 'quiz', 'interview', 'casting'],
        'preview_summary': 'Harry Potter descobre no seu 11º aniversário que é um feiticeiro. Hagrid leva-o para Hogwarts, a escola de magia e feitiçaria, onde faz amigos como Ron e Hermione...',
        'preview_characters': 'Harry Potter é o menino que sobreviveu, marcado com uma cicatriz em forma de raio. Hermione Granger é a aluna brilhante de origem muggle. Ron Weasley vem de uma família de feiticeiros...',
    },
    {
        'title': 'Cem Anos de Solidão',
        'author': 'Gabriel García Márquez',
        'aspects': ['summary', 'themes', 'style', 'quotes'],
        'preview_summary': 'A saga da família Buendía ao longo de sete gerações em Macondo, uma cidade fictícia fundada por José Arcadio Buendía. A narrativa entrelaça realismo mágico com a história da Colômbia...',
        'preview_themes': 'O tema central é a solidão que afeta cada membro da família Buendía. O tempo circular, o destino inevitável, e a repetição de nomes e comportamentos através das gerações...',
    },
    {
        'title': 'Crime e Castigo',
        'author': 'Fiódor Dostoiévski',
        'aspects': ['summary', 'characters', 'themes', 'symbolism'],
        'preview_summary': 'Raskólnikov, um ex-estudante pobre em São Petersburgo, comete o assassinato de uma velha usurária. O romance explora sua luta psicológica com a culpa e a busca por redenção...',
        'preview_themes': 'Dostoiévski explora a teoria do super-homem de Raskólnikov - a ideia de que alguns indivíduos extraordinários estão acima da lei moral convencional...',
    },
    {
        'title': 'Os Lusíadas',
        'author': 'Luís de Camões',
        'aspects': ['summary', 'style', 'symbolism', 'trivia'],
        'preview_summary': 'Epopeia que narra a viagem de Vasco da Gama à Índia, entrelaçando história com mitologia. Os deuses do Olimpo interferem na jornada dos navegadores portugueses...',
        'preview_style': 'Camões utiliza a oitava rima, estrofe de oito versos decassílabos com esquema rimático ABABABCC. O estilo elevado segue os modelos clássicos de Virgílio e Homero...',
    },
    {
        'title': 'O Principezinho',
        'author': 'Antoine de Saint-Exupéry',
        'aspects': ['summary', 'themes', 'quotes', 'similar'],
        'preview_summary': 'Um aviador perdido no deserto do Sahara encontra um pequeno príncipe vindo de um asteroide distante. Através das suas conversas, descobrimos a história das viagens do principezinho...',
        'preview_quotes': '"O essencial é invisível aos olhos", "Tu tornas-te eternamente responsável por aquilo que cativaste", "Foi o tempo que perdeste com a tua rosa que a tornou tão importante"...',
    },
    {
        'title': 'Dom Quixote',
        'author': 'Miguel de Cervantes',
        'aspects': ['summary', 'characters', 'themes', 'adaptation'],
        'preview_summary': 'Alonso Quixano, um fidalgo espanhol, enlouquece de tanto ler romances de cavalaria e decide tornar-se cavaleiro andante sob o nome de Dom Quixote de la Mancha...',
        'preview_characters': 'Dom Quixote é o idealista sonhador que vê o mundo através do prisma da cavalaria. Sancho Pança, seu fiel escudeiro, representa o pragmatismo e o senso comum...',
    },
]

# Livros favoritos do utilizador
DEMO_FAVORITES = [
    {'title': '1984', 'author': 'George Orwell', 'type': 'book'},
    {'title': 'O Senhor dos Anéis: A Irmandade do Anel', 'author': 'J.R.R. Tolkien', 'type': 'book'},
    {'title': 'O Principezinho', 'author': 'Antoine de Saint-Exupéry', 'type': 'book'},
    {'title': 'Harry Potter e a Pedra Filosofal', 'author': 'J.K. Rowling', 'type': 'analysis', 'aspect': 'characters'},
]


def create_demo_user():
    """Cria ou atualiza o utilizador demo"""
    user = User.query.filter_by(email=DEMO_USER['email']).first()
    
    if user:
        print(f"✓ Utilizador demo já existe: {user.email}")
        # Atualizar para Pro e corrigir password
        user.plan = DEMO_USER['plan']
        user.usage_count = DEMO_USER['usage_count']
        user.name = DEMO_USER['name']
        user.password_hash = bcrypt.generate_password_hash(DEMO_USER['password']).decode('utf-8')
    else:
        hashed_password = bcrypt.generate_password_hash(DEMO_USER['password']).decode('utf-8')
        user = User(
            email=DEMO_USER['email'],
            password_hash=hashed_password,
            name=DEMO_USER['name'],
            plan=DEMO_USER['plan'],
            usage_count=DEMO_USER['usage_count'],
            is_verified=True,
            is_active=True,
            created_at=datetime.utcnow() - timedelta(days=45)  # Membro há 45 dias
        )
        db.session.add(user)
        print(f"✓ Utilizador demo criado: {user.email}")
    
    db.session.commit()
    return user


def create_analysis_history(user):
    """Cria histórico de análises variado"""
    # Limpar histórico existente do utilizador demo
    AnalysisHistory.query.filter_by(user_id=user.id).delete()
    
    count = 0
    base_date = datetime.utcnow()
    
    for i, book in enumerate(DEMO_BOOKS):
        for j, aspect in enumerate(book['aspects']):
            # Variar as datas para parecer uso natural
            days_ago = (len(DEMO_BOOKS) - i) * 3 + j
            hours_ago = (j * 4) % 24
            
            created_at = base_date - timedelta(days=days_ago, hours=hours_ago)
            
            # Escolher preview baseado no aspeto
            preview = book.get(f'preview_{aspect}', book.get('preview_summary', 'Análise detalhada do livro...'))
            
            analysis = AnalysisHistory(
                user_id=user.id,
                book_title=book['title'],
                book_author=book['author'],
                aspect=aspect,
                language='pt-pt',
                response_preview=preview,
                created_at=created_at
            )
            db.session.add(analysis)
            count += 1
    
    db.session.commit()
    print(f"✓ Criadas {count} análises no histórico")
    return count


def create_favorites(user):
    """Cria favoritos do utilizador"""
    # Limpar favoritos existentes do utilizador demo
    Favorite.query.filter_by(user_id=user.id).delete()
    
    count = 0
    for fav in DEMO_FAVORITES:
        favorite = Favorite(
            user_id=user.id,
            favorite_type=fav['type'],
            book_title=fav['title'],
            book_author=fav.get('author'),
            aspect=fav.get('aspect'),
            created_at=datetime.utcnow() - timedelta(days=count * 5)
        )
        db.session.add(favorite)
        count += 1
    
    db.session.commit()
    print(f"✓ Criados {count} favoritos")
    return count


def print_login_info():
    """Imprime informações de login para a gravação"""
    print("\n" + "="*50)
    print("🎬 DADOS PARA GRAVAÇÃO DO VÍDEO")
    print("="*50)
    print(f"\n📧 Email: {DEMO_USER['email']}")
    print(f"🔑 Password: {DEMO_USER['password']}")
    print(f"👤 Nome: {DEMO_USER['name']}")
    print(f"⭐ Plano: {DEMO_USER['plan'].upper()}")
    print(f"📊 Uso: {DEMO_USER['usage_count']}/100 análises")
    print("\n" + "="*50)
    print("📚 LIVROS PARA DEMONSTRAR:")
    print("="*50)
    for book in DEMO_BOOKS[:5]:
        print(f"  • {book['title']} - {book['author']}")
    print("\n💡 Dica: Use '1984' de George Orwell para a demo principal!")
    print("="*50 + "\n")


def main():
    """Função principal"""
    print("\n🚀 Iniciando seed de dados demo...\n")
    
    with app.app_context():
        # Criar utilizador
        user = create_demo_user()
        
        # Criar histórico
        create_analysis_history(user)
        
        # Criar favoritos
        create_favorites(user)
        
        # Mostrar informações
        print_login_info()
        
        print("✅ Seed concluído com sucesso!\n")


if __name__ == '__main__':
    main()
