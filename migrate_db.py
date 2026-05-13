"""
Database migration script for BookCreatorAI
Run this script to add new tables and columns
"""
import sqlite3
import os

def migrate():
    db_path = os.path.join(os.path.dirname(__file__), 'database', 'books.db')
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check and add columns to users table
    cursor.execute("PRAGMA table_info(users)")
    existing_columns = [col[1] for col in cursor.fetchall()]
    
    user_columns = [
        ("plan", "VARCHAR(20) DEFAULT 'free'"),
        ("usage_count", "INTEGER DEFAULT 0"),
        ("usage_reset_date", "DATETIME"),
        ("stripe_customer_id", "VARCHAR(100)"),
        ("stripe_subscription_id", "VARCHAR(100)"),
        ("subscription_status", "VARCHAR(20) DEFAULT 'none'"),
        ("subscription_end_date", "DATETIME"),
    ]
    
    for col_name, col_type in user_columns:
        if col_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
                print(f"Added column: {col_name}")
            except sqlite3.OperationalError as e:
                print(f"Column {col_name} might already exist: {e}")
    
    # Create subscription_history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscription_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan VARCHAR(20) NOT NULL,
            action VARCHAR(20) NOT NULL,
            stripe_subscription_id VARCHAR(100),
            stripe_invoice_id VARCHAR(100),
            amount FLOAT DEFAULT 0,
            currency VARCHAR(3) DEFAULT 'EUR',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            period_start DATETIME,
            period_end DATETIME,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    print("Created/verified subscription_history table")
    
    # Create analysis_history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            book_title VARCHAR(500) NOT NULL,
            book_author VARCHAR(300),
            aspect VARCHAR(50) NOT NULL,
            language VARCHAR(10) DEFAULT 'pt-pt',
            response_preview TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    print("Created/verified analysis_history table")
    
    # Create index for faster queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_analysis_user_id ON analysis_history(user_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_analysis_created_at ON analysis_history(created_at)
    """)
    print("Created indexes for analysis_history")
    
    # Create favorites table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            favorite_type VARCHAR(20) NOT NULL DEFAULT 'book',
            book_title VARCHAR(500) NOT NULL,
            book_author VARCHAR(200),
            analysis_id INTEGER,
            aspect VARCHAR(50),
            content_preview TEXT,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (analysis_id) REFERENCES analysis_history(id),
            UNIQUE(user_id, book_title, book_author, favorite_type, aspect)
        )
    """)
    print("Created/verified favorites table")
    
    # Create indexes for favorites
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_favorites_user_id ON favorites(user_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_favorites_book_title ON favorites(book_title)
    """)
    print("Created indexes for favorites")
    
    # Create referrals table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER NOT NULL,
            referral_code VARCHAR(20) UNIQUE NOT NULL,
            clicks INTEGER DEFAULT 0,
            signups INTEGER DEFAULT 0,
            conversions INTEGER DEFAULT 0,
            total_earnings FLOAT DEFAULT 0,
            pending_earnings FLOAT DEFAULT 0,
            paid_earnings FLOAT DEFAULT 0,
            commission_rate FLOAT DEFAULT 0.20,
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_referral_at DATETIME,
            FOREIGN KEY (referrer_id) REFERENCES users(id)
        )
    """)
    print("Created/verified referrals table")
    
    # Create referral_signups table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS referral_signups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referral_id INTEGER NOT NULL,
            referred_user_id INTEGER,
            status VARCHAR(20) DEFAULT 'pending',
            referrer_reward_given BOOLEAN DEFAULT 0,
            referred_reward_given BOOLEAN DEFAULT 0,
            commission_amount FLOAT DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            converted_at DATETIME,
            FOREIGN KEY (referral_id) REFERENCES referrals(id),
            FOREIGN KEY (referred_user_id) REFERENCES users(id)
        )
    """)
    print("Created/verified referral_signups table")
    
    # Create indexes for referrals
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_referrals_referrer_id ON referrals(referrer_id)
    """)
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_referrals_code ON referrals(referral_code)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_referral_signups_referral_id ON referral_signups(referral_id)
    """)
    print("Created indexes for referrals")
    
    # Create prompt_templates table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prompt_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            creator_id INTEGER NOT NULL,
            title VARCHAR(200) NOT NULL,
            description TEXT,
            category VARCHAR(50) NOT NULL,
            prompt_template TEXT NOT NULL,
            example_output TEXT,
            price FLOAT DEFAULT 0,
            currency VARCHAR(3) DEFAULT 'EUR',
            downloads INTEGER DEFAULT 0,
            rating FLOAT DEFAULT 0,
            rating_count INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            is_featured BOOLEAN DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (creator_id) REFERENCES users(id)
        )
    """)
    print("Created/verified prompt_templates table")
    
    # Create prompt_purchases table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prompt_purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            template_id INTEGER NOT NULL,
            amount_paid FLOAT DEFAULT 0,
            currency VARCHAR(3) DEFAULT 'EUR',
            purchased_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (template_id) REFERENCES prompt_templates(id),
            UNIQUE(user_id, template_id)
        )
    """)
    print("Created/verified prompt_purchases table")
    
    # Create indexes for marketplace
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_prompt_templates_creator ON prompt_templates(creator_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_prompt_templates_category ON prompt_templates(category)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_prompt_purchases_user ON prompt_purchases(user_id)
    """)
    print("Created indexes for marketplace")
    
    conn.commit()
    conn.close()
    print("\nMigration completed successfully!")

if __name__ == '__main__':
    migrate()
