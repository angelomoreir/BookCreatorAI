"""
Script para criar um utilizador premium rapidamente
Executar: python add_premium_user.py
"""
from app import app, db, bcrypt
from models.book import User
from datetime import datetime, timedelta
import sys

def create_premium_user(email, name, password):
    """Cria um utilizador com plano premium"""
    with app.app_context():
        # Verificar se já existe
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            print(f"⚠️  Utilizador com email '{email}' já existe!")
            print(f"   Atualizando para Premium...")
            existing_user.plan = 'premium'
            existing_user.subscription_status = 'active'
            existing_user.subscription_end_date = datetime.utcnow() + timedelta(days=365)
            existing_user.usage_count = 0
            existing_user.is_verified = True
            existing_user.is_active = True
            db.session.commit()
            print(f"✅ Utilizador '{email}' atualizado para Premium!")
            print(f"   - Plano: {existing_user.plan}")
            print(f"   - Status: {existing_user.subscription_status}")
            print(f"   - Limite mensal: 1000 análises")
            return existing_user
        
        # Criar novo utilizador premium
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        premium_user = User(
            name=name,
            email=email,
            password_hash=hashed_password,
            plan='premium',
            subscription_status='active',
            subscription_end_date=datetime.utcnow() + timedelta(days=365),
            usage_count=0,
            is_verified=True,
            is_active=True
        )
        
        db.session.add(premium_user)
        db.session.commit()
        
        print("\n✅ Utilizador Premium criado com sucesso!")
        print(f"   📧 Email: {email}")
        print(f"   👤 Nome: {name}")
        print(f"   💎 Plano: Premium")
        print(f"   📊 Limite mensal: 1000 análises")
        print(f"   ✅ Verificado: Sim")
        print(f"   📅 Válido até: {premium_user.subscription_end_date.strftime('%d/%m/%Y')}")
        print(f"\n🔑 Credenciais de acesso:")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        
        return premium_user

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 CRIAR UTILIZADOR PREMIUM - BookCreatorAI")
    print("=" * 60)
    print()
    
    # Verificar se foram passados argumentos
    if len(sys.argv) == 4:
        email = sys.argv[1].strip().lower()
        name = sys.argv[2].strip()
        password = sys.argv[3].strip()
    else:
        # Valores padrão para teste rápido
        email = "premium@bookscreator.ai"
        name = "Utilizador Premium"
        password = "Premium2026!"
        
        print(f"📝 Criando utilizador premium padrão:")
        print(f"   Email: {email}")
        print(f"   Nome: {name}")
        print(f"   Password: {password}")
        print()
        print("💡 Para criar com dados personalizados, use:")
        print("   python add_premium_user.py <email> <nome> <password>")
        print()
    
    create_premium_user(email, name, password)
