"""
Script para criar o utilizador supervisor (admin)
Executar uma vez: python create_supervisor.py
"""
from app import app, db, bcrypt
from models.book import User

def create_supervisor():
    with app.app_context():
        # Verificar se já existe
        existing = User.query.filter_by(email='supervisor').first()
        if existing:
            print("Utilizador 'supervisor' já existe. A atualizar para admin...")
            existing.is_admin = True
            db.session.commit()
            print("Utilizador atualizado com sucesso!")
            return
        
        # Criar novo utilizador supervisor
        hashed_password = bcrypt.generate_password_hash('Tgnwlp4s1americo').decode('utf-8')
        supervisor = User(
            name='Supervisor',
            email='supervisor',
            password_hash=hashed_password,
            is_admin=True,
            is_verified=True,
            plan='premium'
        )
        
        db.session.add(supervisor)
        db.session.commit()
        
        print("=" * 50)
        print("Utilizador supervisor criado com sucesso!")
        print("=" * 50)
        print(f"Email/Username: supervisor")
        print(f"Password: Tgnwlp4s1americo")
        print(f"Admin: Sim")
        print(f"Plano: Premium")
        print("=" * 50)
        print("Aceda ao dashboard em: /admin/dashboard")
        print("=" * 50)

if __name__ == '__main__':
    create_supervisor()
