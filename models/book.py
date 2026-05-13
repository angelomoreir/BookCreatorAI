from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import json
import secrets
import re

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    
    # Subscription/Plan fields
    plan = db.Column(db.String(20), default='free')  # free, pro, premium
    usage_count = db.Column(db.Integer, default=0)  # Monthly usage counter
    usage_reset_date = db.Column(db.DateTime, nullable=True)
    
    # Stripe fields
    stripe_customer_id = db.Column(db.String(100), nullable=True)
    stripe_subscription_id = db.Column(db.String(100), nullable=True)
    subscription_status = db.Column(db.String(20), default='none')  # none, active, canceled, past_due
    subscription_end_date = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    books = db.relationship('Book', backref='owner', lazy='dynamic')
    subscription_history = db.relationship('SubscriptionHistory', backref='user', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.email}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'plan': self.plan,
            'usage_count': self.usage_count,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'is_verified': self.is_verified,
            'subscription_status': self.subscription_status
        }
    
    def get_plan_config(self):
        """Get full plan configuration"""
        return PLAN_CONFIG.get(self.plan, PLAN_CONFIG['free'])
    
    def get_usage_limit(self):
        """Get monthly usage limit based on plan"""
        return self.get_plan_config()['limits']['analyses_per_month']
    
    def can_use_feature(self, feature=None):
        """Check if user can use a specific feature"""
        config = self.get_plan_config()
        
        # Check usage limit
        if self.usage_count >= config['limits']['analyses_per_month']:
            return False
        
        # Check specific feature access
        if feature and feature in config['features']:
            return config['features'][feature]
        
        return True
    
    def get_available_features(self):
        """Get list of available features for user's plan"""
        return self.get_plan_config()['features']
    
    def increment_usage(self):
        """Increment usage counter"""
        self.usage_count += 1
    
    def reset_monthly_usage(self):
        """Reset monthly usage counter"""
        self.usage_count = 0
        self.usage_reset_date = datetime.utcnow()
    
    def has_active_subscription(self):
        """Check if user has an active paid subscription"""
        return self.subscription_status == 'active' and self.plan in ['pro', 'premium']


# Plan configuration - centralized definition
PLAN_CONFIG = {
    'free': {
        'name': 'Gratuito',
        'price_monthly': 0,
        'price_yearly': 0,
        'stripe_price_monthly': None,
        'stripe_price_yearly': None,
        'limits': {
            'analyses_per_month': 10,
            'saved_analyses': 5,
            'chat_messages_per_book': 10
        },
        'features': {
            'basic_analysis': True,
            'summary': True,
            'characters': True,
            'themes': True,
            'quiz': False,
            'interview': False,
            'continue_story': False,
            'alternate_ending': False,
            'export_pdf': False,
            'history': False,
            'priority_support': False
        }
    },
    'pro': {
        'name': 'Pro',
        'price_monthly': 9.99,
        'price_yearly': 99.99,
        'stripe_price_monthly': 'price_pro_monthly',  # Replace with actual Stripe price ID
        'stripe_price_yearly': 'price_pro_yearly',
        'limits': {
            'analyses_per_month': 100,
            'saved_analyses': 50,
            'chat_messages_per_book': 50
        },
        'features': {
            'basic_analysis': True,
            'summary': True,
            'characters': True,
            'themes': True,
            'quiz': True,
            'interview': True,
            'continue_story': True,
            'alternate_ending': True,
            'export_pdf': True,
            'history': True,
            'priority_support': False
        }
    },
    'premium': {
        'name': 'Premium',
        'price_monthly': 19.99,
        'price_yearly': 199.99,
        'stripe_price_monthly': 'price_premium_monthly',  # Replace with actual Stripe price ID
        'stripe_price_yearly': 'price_premium_yearly',
        'limits': {
            'analyses_per_month': 1000,
            'saved_analyses': -1,  # Unlimited
            'chat_messages_per_book': -1  # Unlimited
        },
        'features': {
            'basic_analysis': True,
            'summary': True,
            'characters': True,
            'themes': True,
            'quiz': True,
            'interview': True,
            'continue_story': True,
            'alternate_ending': True,
            'export_pdf': True,
            'history': True,
            'priority_support': True
        }
    }
}


class AnalysisHistory(db.Model):
    """Track book analysis history for users"""
    __tablename__ = 'analysis_history'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Book details
    book_title = db.Column(db.String(500), nullable=False)
    book_author = db.Column(db.String(300), nullable=True)
    
    # Analysis details
    aspect = db.Column(db.String(50), nullable=False)  # info, summary, characters, quiz, etc.
    language = db.Column(db.String(10), default='pt-pt')
    
    # Response data (optional - can store for history viewing)
    response_preview = db.Column(db.Text, nullable=True)  # First 500 chars of response
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('analyses', lazy='dynamic'))
    
    def to_dict(self):
        aspect_labels = {
            'info': 'Informação',
            'summary': 'Resumo',
            'characters': 'Personagens',
            'themes': 'Temas',
            'world': 'Mundo',
            'style': 'Estilo',
            'quotes': 'Citações',
            'discussion': 'Discussão',
            'similar': 'Similares',
            'trivia': 'Curiosidades',
            'timeline': 'Cronologia',
            'symbolism': 'Simbolismo',
            'adaptation': 'Adaptações',
            'playlist': 'Playlist',
            'trailer': 'Trailer',
            'cover': 'Capa',
            'casting': 'Casting',
            'chat': 'Chat',
            'quiz': 'Quiz',
            'interview': 'Entrevista',
            'continue': 'Continuação',
            'alternate': 'Final Alternativo'
        }
        return {
            'id': self.id,
            'book_title': self.book_title,
            'book_author': self.book_author,
            'aspect': self.aspect,
            'aspect_label': aspect_labels.get(self.aspect, self.aspect),
            'language': self.language,
            'response_preview': self.response_preview[:200] + '...' if self.response_preview and len(self.response_preview) > 200 else self.response_preview,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'created_at_formatted': self.created_at.strftime('%d/%m/%Y às %H:%M')
        }


class Favorite(db.Model):
    """User favorites - books and analyses"""
    __tablename__ = 'favorites'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Favorite type: 'book' or 'analysis'
    favorite_type = db.Column(db.String(20), nullable=False, default='book')
    
    # Book info
    book_title = db.Column(db.String(500), nullable=False)
    book_author = db.Column(db.String(200), nullable=True)
    
    # For analysis favorites
    analysis_id = db.Column(db.Integer, db.ForeignKey('analysis_history.id'), nullable=True)
    aspect = db.Column(db.String(50), nullable=True)
    content_preview = db.Column(db.Text, nullable=True)
    
    # Metadata
    notes = db.Column(db.Text, nullable=True)  # User notes about the favorite
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('favorites', lazy='dynamic'))
    analysis = db.relationship('AnalysisHistory', backref=db.backref('favorited_by', lazy='dynamic'))
    
    # Unique constraint to prevent duplicates
    __table_args__ = (
        db.UniqueConstraint('user_id', 'book_title', 'book_author', 'favorite_type', 'aspect', name='unique_favorite'),
    )
    
    def to_dict(self):
        aspect_labels = {
            'info': 'Informação', 'summary': 'Resumo', 'characters': 'Personagens',
            'themes': 'Temas', 'world': 'Mundo', 'style': 'Estilo', 'quotes': 'Citações',
            'discussion': 'Discussão', 'similar': 'Similares', 'trivia': 'Curiosidades',
            'timeline': 'Cronologia', 'symbolism': 'Simbolismo', 'adaptation': 'Adaptações',
            'playlist': 'Playlist', 'trailer': 'Trailer', 'cover': 'Capa', 'casting': 'Casting',
            'chat': 'Chat', 'quiz': 'Quiz', 'interview': 'Entrevista',
            'continue': 'Continuação', 'alternate': 'Final Alternativo'
        }
        return {
            'id': self.id,
            'favorite_type': self.favorite_type,
            'book_title': self.book_title,
            'book_author': self.book_author,
            'aspect': self.aspect,
            'aspect_label': aspect_labels.get(self.aspect, self.aspect) if self.aspect else None,
            'content_preview': self.content_preview[:200] + '...' if self.content_preview and len(self.content_preview) > 200 else self.content_preview,
            'notes': self.notes,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'created_at_formatted': self.created_at.strftime('%d/%m/%Y às %H:%M')
        }


class SubscriptionHistory(db.Model):
    """Track subscription changes for billing history"""
    __tablename__ = 'subscription_history'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Subscription details
    plan = db.Column(db.String(20), nullable=False)
    action = db.Column(db.String(20), nullable=False)  # created, upgraded, downgraded, canceled, renewed
    
    # Stripe details
    stripe_subscription_id = db.Column(db.String(100), nullable=True)
    stripe_invoice_id = db.Column(db.String(100), nullable=True)
    
    # Amounts
    amount = db.Column(db.Float, default=0)
    currency = db.Column(db.String(3), default='EUR')
    
    # Dates
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    period_start = db.Column(db.DateTime, nullable=True)
    period_end = db.Column(db.DateTime, nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'plan': self.plan,
            'action': self.action,
            'amount': self.amount,
            'currency': self.currency,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'period_start': self.period_start.strftime('%Y-%m-%d') if self.period_start else None,
            'period_end': self.period_end.strftime('%Y-%m-%d') if self.period_end else None
        }

class Referral(db.Model):
    """Referral/Affiliate program model"""
    __tablename__ = 'referrals'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Referrer (who shares the code)
    referrer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    referral_code = db.Column(db.String(20), unique=True, nullable=False)
    
    # Stats
    clicks = db.Column(db.Integer, default=0)
    signups = db.Column(db.Integer, default=0)
    conversions = db.Column(db.Integer, default=0)  # Paid subscriptions
    
    # Earnings
    total_earnings = db.Column(db.Float, default=0)
    pending_earnings = db.Column(db.Float, default=0)
    paid_earnings = db.Column(db.Float, default=0)
    
    # Settings
    commission_rate = db.Column(db.Float, default=0.20)  # 20% commission
    is_active = db.Column(db.Boolean, default=True)
    
    # Dates
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_referral_at = db.Column(db.DateTime, nullable=True)
    
    # Relationship
    referrer = db.relationship('User', backref='referral_program', foreign_keys=[referrer_id])
    
    def to_dict(self):
        return {
            'id': self.id,
            'referral_code': self.referral_code,
            'clicks': self.clicks,
            'signups': self.signups,
            'conversions': self.conversions,
            'total_earnings': self.total_earnings,
            'pending_earnings': self.pending_earnings,
            'paid_earnings': self.paid_earnings,
            'commission_rate': self.commission_rate,
            'is_active': self.is_active,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'last_referral_at': self.last_referral_at.strftime('%Y-%m-%d %H:%M:%S') if self.last_referral_at else None
        }


class ReferralSignup(db.Model):
    """Track individual referral signups"""
    __tablename__ = 'referral_signups'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Links
    referral_id = db.Column(db.Integer, db.ForeignKey('referrals.id'), nullable=False)
    referred_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Status
    status = db.Column(db.String(20), default='pending')  # pending, signed_up, converted, expired
    
    # Reward tracking
    referrer_reward_given = db.Column(db.Boolean, default=False)
    referred_reward_given = db.Column(db.Boolean, default=False)
    
    # Commission
    commission_amount = db.Column(db.Float, default=0)
    
    # Dates
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    converted_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    referral = db.relationship('Referral', backref=db.backref('referral_signups', lazy='dynamic'))
    referred_user = db.relationship('User', backref=db.backref('was_referred_by', lazy='dynamic'), foreign_keys=[referred_user_id])
    
    def to_dict(self):
        return {
            'id': self.id,
            'status': self.status,
            'commission_amount': self.commission_amount,
            'referrer_reward_given': self.referrer_reward_given,
            'referred_reward_given': self.referred_reward_given,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'converted_at': self.converted_at.strftime('%Y-%m-%d %H:%M:%S') if self.converted_at else None
        }


class PromptTemplate(db.Model):
    """Marketplace prompt templates"""
    __tablename__ = 'prompt_templates'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Creator
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Template info
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=False)  # analysis, creative, educational, etc.
    
    # The actual prompt template
    prompt_template = db.Column(db.Text, nullable=False)
    example_output = db.Column(db.Text, nullable=True)
    
    # Pricing
    price = db.Column(db.Float, default=0)  # 0 = free
    currency = db.Column(db.String(3), default='EUR')
    
    # Stats
    downloads = db.Column(db.Integer, default=0)
    rating = db.Column(db.Float, default=0)
    rating_count = db.Column(db.Integer, default=0)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    is_featured = db.Column(db.Boolean, default=False)
    
    # Dates
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    creator = db.relationship('User', backref=db.backref('prompt_templates', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'creator_id': self.creator_id,
            'creator_name': self.creator.name if self.creator else 'Anónimo',
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'prompt_template': self.prompt_template,
            'example_output': self.example_output,
            'price': self.price,
            'currency': self.currency,
            'downloads': self.downloads,
            'rating': self.rating,
            'rating_count': self.rating_count,
            'is_featured': self.is_featured,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }


class PromptPurchase(db.Model):
    """Track prompt template purchases"""
    __tablename__ = 'prompt_purchases'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Links
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('prompt_templates.id'), nullable=False)
    
    # Transaction
    amount_paid = db.Column(db.Float, default=0)
    currency = db.Column(db.String(3), default='EUR')
    
    # Dates
    purchased_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('prompt_purchases', lazy='dynamic'))
    template = db.relationship('PromptTemplate', backref=db.backref('purchases', lazy='dynamic'))
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('user_id', 'template_id', name='unique_user_template'),)
    
    def to_dict(self):
        return {
            'id': self.id,
            'template_id': self.template_id,
            'template_title': self.template.title if self.template else None,
            'amount_paid': self.amount_paid,
            'purchased_at': self.purchased_at.strftime('%Y-%m-%d %H:%M:%S')
        }


class Series(db.Model):
    """Book series/collection model"""
    __tablename__ = 'series'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text, nullable=True)
    cover_image = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    books = db.relationship('Book', backref='series', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'cover_image': self.cover_image,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'book_count': self.books.count(),
            'books': [b.id for b in self.books]
        }

class Book(db.Model):
    __tablename__ = 'books'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(500), nullable=False)
    theme = db.Column(db.String(500), nullable=False)
    style = db.Column(db.String(100), nullable=False)
    chapters = db.Column(db.Text, nullable=False)  # JSON string
    full_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # User ownership
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # New fields
    language = db.Column(db.String(10), default='pt-pt')
    is_favorite = db.Column(db.Boolean, default=False)
    tags = db.Column(db.Text, default='[]')  # JSON array of tags
    share_token = db.Column(db.String(32), unique=True, nullable=True)
    word_count = db.Column(db.Integer, default=0)
    parent_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=True)
    
    # Cover and editing fields
    cover_image = db.Column(db.Text, nullable=True)  # Base64 or URL
    chapters_content = db.Column(db.Text, nullable=True)  # JSON with individual chapter content
    style_template = db.Column(db.String(50), default='standard')  # Template used
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Advanced AI fields
    characters = db.Column(db.Text, nullable=True)  # JSON array of character objects
    world_setting = db.Column(db.Text, nullable=True)  # JSON with worldbuilding details
    plot_outline = db.Column(db.Text, nullable=True)  # Selected plot outline
    ai_analysis = db.Column(db.Text, nullable=True)  # JSON with AI analysis results
    
    # Series/Collection
    series_id = db.Column(db.Integer, db.ForeignKey('series.id'), nullable=True)
    series_order = db.Column(db.Integer, default=0)  # Order within series
    synopsis = db.Column(db.Text, nullable=True)  # Book synopsis/summary
    
    def __repr__(self):
        return f'<Book {self.title}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'theme': self.theme,
            'style': self.style,
            'language': self.language or 'pt-pt',
            'chapters': json.loads(self.chapters) if self.chapters else [],
            'full_text': self.full_text,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
            'is_favorite': self.is_favorite or False,
            'tags': self.get_tags(),
            'share_token': self.share_token,
            'word_count': self.word_count or self.calculate_word_count(),
            'reading_time': self.get_reading_time(),
            'parent_id': self.parent_id,
            'cover_image': self.cover_image,
            'style_template': self.style_template or 'standard',
            'chapters_content': self.get_chapters_content(),
            'characters': self.get_characters(),
            'world_setting': self.get_world_setting(),
            'plot_outline': self.plot_outline,
            'ai_analysis': self.get_ai_analysis(),
            'series_id': self.series_id,
            'series_order': self.series_order or 0,
            'synopsis': self.synopsis
        }
    
    def set_chapters(self, chapters_list):
        """Set chapters from a list"""
        self.chapters = json.dumps(chapters_list, ensure_ascii=False)
    
    def get_chapters(self):
        """Get chapters as a list"""
        return json.loads(self.chapters) if self.chapters else []
    
    def set_tags(self, tags_list):
        """Set tags from a list"""
        self.tags = json.dumps(tags_list, ensure_ascii=False)
    
    def get_tags(self):
        """Get tags as a list"""
        try:
            return json.loads(self.tags) if self.tags else []
        except:
            return []
    
    def add_tag(self, tag):
        """Add a single tag"""
        tags = self.get_tags()
        if tag not in tags:
            tags.append(tag)
            self.set_tags(tags)
    
    def remove_tag(self, tag):
        """Remove a single tag"""
        tags = self.get_tags()
        if tag in tags:
            tags.remove(tag)
            self.set_tags(tags)
    
    def calculate_word_count(self):
        """Calculate word count from full text"""
        if self.full_text:
            words = len(re.findall(r'\w+', self.full_text))
            return words
        return 0
    
    def get_reading_time(self):
        """Estimate reading time in minutes (avg 200 words/min)"""
        words = self.word_count or self.calculate_word_count()
        minutes = max(1, round(words / 200))
        return minutes
    
    def get_page_count(self):
        """Estimate page count (avg 250 words/page)"""
        words = self.word_count or self.calculate_word_count()
        return max(1, round(words / 250))
    
    def generate_share_token(self):
        """Generate a unique share token"""
        self.share_token = secrets.token_urlsafe(16)
        return self.share_token
    
    def get_stats(self):
        """Get book statistics"""
        word_count = self.word_count or self.calculate_word_count()
        return {
            'word_count': word_count,
            'page_count': self.get_page_count(),
            'chapter_count': len(self.get_chapters()),
            'reading_time': self.get_reading_time(),
            'character_count': len(self.full_text) if self.full_text else 0,
            'avg_words_per_chapter': round(word_count / max(1, len(self.get_chapters())))
        }
    
    def get_chapters_content(self):
        """Get individual chapter contents as a list"""
        if self.chapters_content:
            try:
                return json.loads(self.chapters_content)
            except:
                pass
        # Parse from full_text if not stored separately
        return self.parse_chapters_from_text()
    
    def set_chapters_content(self, chapters_list):
        """Set individual chapter contents"""
        self.chapters_content = json.dumps(chapters_list, ensure_ascii=False)
    
    def parse_chapters_from_text(self):
        """Parse full_text into individual chapters"""
        if not self.full_text:
            return []
        
        chapters = []
        chapter_titles = self.get_chapters()
        
        if not chapter_titles:
            return [{'title': 'Conteúdo', 'content': self.full_text}]
        
        # Split by chapter titles
        text = self.full_text
        for i, title in enumerate(chapter_titles):
            # Find the start of this chapter
            start_idx = text.find(title)
            if start_idx == -1:
                # Try finding by chapter number
                start_idx = text.lower().find(f"capítulo {i+1}")
            
            if start_idx != -1:
                # Find the end (start of next chapter or end of text)
                end_idx = len(text)
                if i + 1 < len(chapter_titles):
                    next_start = text.find(chapter_titles[i + 1])
                    if next_start != -1:
                        end_idx = next_start
                
                content = text[start_idx:end_idx].strip()
                chapters.append({
                    'title': title,
                    'content': content
                })
        
        # If parsing failed, return the whole text
        if not chapters:
            return [{'title': chapter_titles[0] if chapter_titles else 'Conteúdo', 'content': self.full_text}]
        
        return chapters
    
    def update_chapter(self, index, new_content):
        """Update a specific chapter's content"""
        chapters = self.get_chapters_content()
        if 0 <= index < len(chapters):
            chapters[index]['content'] = new_content
            self.set_chapters_content(chapters)
            # Rebuild full_text
            self.full_text = '\n\n'.join([ch['content'] for ch in chapters])
            self.word_count = self.calculate_word_count()
            return True
        return False
    
    def update_chapter_title(self, index, new_title):
        """Update a specific chapter's title"""
        chapters = self.get_chapters_content()
        chapter_titles = self.get_chapters()
        
        if 0 <= index < len(chapters):
            old_title = chapters[index]['title']
            chapters[index]['title'] = new_title
            chapters[index]['content'] = chapters[index]['content'].replace(old_title, new_title, 1)
            self.set_chapters_content(chapters)
            
            if 0 <= index < len(chapter_titles):
                chapter_titles[index] = new_title
                self.set_chapters(chapter_titles)
            
            # Rebuild full_text
            self.full_text = '\n\n'.join([ch['content'] for ch in chapters])
            return True
        return False
    
    # ==================== ADVANCED AI METHODS ====================
    
    def get_characters(self):
        """Get characters as a list of dicts"""
        try:
            return json.loads(self.characters) if self.characters else []
        except:
            return []
    
    def set_characters(self, characters_list):
        """Set characters from a list of dicts"""
        self.characters = json.dumps(characters_list, ensure_ascii=False)
    
    def add_character(self, character):
        """Add a character dict: {name, role, description, traits, arc}"""
        characters = self.get_characters()
        characters.append(character)
        self.set_characters(characters)
    
    def get_world_setting(self):
        """Get worldbuilding as a dict"""
        try:
            return json.loads(self.world_setting) if self.world_setting else {}
        except:
            return {}
    
    def set_world_setting(self, world_dict):
        """Set worldbuilding from a dict"""
        self.world_setting = json.dumps(world_dict, ensure_ascii=False)
    
    def get_ai_analysis(self):
        """Get AI analysis results as a dict"""
        try:
            return json.loads(self.ai_analysis) if self.ai_analysis else {}
        except:
            return {}
    
    def set_ai_analysis(self, analysis_dict):
        """Set AI analysis from a dict"""
        self.ai_analysis = json.dumps(analysis_dict, ensure_ascii=False)
    
    def get_characters_prompt(self):
        """Generate prompt section for characters"""
        characters = self.get_characters()
        if not characters:
            return ""
        
        prompt = "\n\nPERSONAGENS DEFINIDOS:\n"
        for char in characters:
            prompt += f"\n- {char.get('name', 'Sem nome')} ({char.get('role', 'personagem')})"
            if char.get('description'):
                prompt += f"\n  Descrição: {char['description']}"
            if char.get('traits'):
                prompt += f"\n  Traços: {char['traits']}"
            if char.get('arc'):
                prompt += f"\n  Arco: {char['arc']}"
        
        return prompt
    
    def get_world_prompt(self):
        """Generate prompt section for worldbuilding"""
        world = self.get_world_setting()
        if not world:
            return ""
        
        prompt = "\n\nUNIVERSO/CENÁRIO:\n"
        if world.get('time_period'):
            prompt += f"- Época: {world['time_period']}\n"
        if world.get('location'):
            prompt += f"- Local: {world['location']}\n"
        if world.get('atmosphere'):
            prompt += f"- Atmosfera: {world['atmosphere']}\n"
        if world.get('rules'):
            prompt += f"- Regras do mundo: {world['rules']}\n"
        if world.get('technology'):
            prompt += f"- Tecnologia: {world['technology']}\n"
        if world.get('society'):
            prompt += f"- Sociedade: {world['society']}\n"
        if world.get('custom'):
            prompt += f"- Detalhes adicionais: {world['custom']}\n"
        
        return prompt


class PushSubscription(db.Model):
    """Store push notification subscriptions"""
    __tablename__ = 'push_subscriptions'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Subscription data
    endpoint = db.Column(db.Text, nullable=False, unique=True)
    p256dh_key = db.Column(db.Text, nullable=False)  # Public key
    auth_key = db.Column(db.Text, nullable=False)    # Auth secret
    
    # Preferences
    notify_usage_reset = db.Column(db.Boolean, default=True)
    notify_new_features = db.Column(db.Boolean, default=True)
    notify_tips = db.Column(db.Boolean, default=False)
    notify_promotions = db.Column(db.Boolean, default=False)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('push_subscriptions', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'endpoint': self.endpoint[:50] + '...',
            'notify_usage_reset': self.notify_usage_reset,
            'notify_new_features': self.notify_new_features,
            'notify_tips': self.notify_tips,
            'notify_promotions': self.notify_promotions,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'is_active': self.is_active
        }


class Notification(db.Model):
    """Store notification history"""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Null for broadcast
    
    # Notification content
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)  # usage_reset, new_feature, tip, promo
    url = db.Column(db.String(500), nullable=True)
    
    # Status
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime, nullable=True)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('notifications', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'body': self.body,
            'type': self.notification_type,
            'url': self.url,
            'sent_at': self.sent_at.strftime('%Y-%m-%d %H:%M:%S'),
            'is_read': self.is_read
        }


class UserTasteProfile(db.Model):
    """Store user's reading taste profile for AI recommendations"""
    __tablename__ = 'user_taste_profiles'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    
    # Favorite genres (JSON list with scores)
    favorite_genres = db.Column(db.Text, default='{}')  # {"fantasy": 0.8, "romance": 0.6}
    
    # Favorite themes (JSON list with scores)
    favorite_themes = db.Column(db.Text, default='{}')  # {"redemption": 0.9, "love": 0.7}
    
    # Preferred writing styles
    preferred_styles = db.Column(db.Text, default='{}')  # {"descriptive": 0.8, "fast-paced": 0.6}
    
    # Favorite authors
    favorite_authors = db.Column(db.Text, default='[]')  # ["J.K. Rowling", "Stephen King"]
    
    # Books liked (with ratings)
    liked_books = db.Column(db.Text, default='[]')  # [{"title": "...", "author": "...", "rating": 5}]
    
    # Books disliked
    disliked_books = db.Column(db.Text, default='[]')
    
    # Reading preferences
    prefers_series = db.Column(db.Boolean, default=None)  # True if prefers series over standalone
    prefers_long_books = db.Column(db.Boolean, default=None)
    prefers_complex_plots = db.Column(db.Boolean, default=None)
    
    # Mood preferences (what they read for)
    reading_moods = db.Column(db.Text, default='{}')  # {"escape": 0.8, "learn": 0.5, "emotion": 0.7}
    
    # AI-generated taste summary
    taste_summary = db.Column(db.Text, nullable=True)
    
    # Stats
    books_analyzed = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('taste_profile', uselist=False))
    
    def get_genres(self):
        import json
        try:
            return json.loads(self.favorite_genres or '{}')
        except:
            return {}
    
    def set_genres(self, genres_dict):
        import json
        self.favorite_genres = json.dumps(genres_dict)
    
    def get_themes(self):
        import json
        try:
            return json.loads(self.favorite_themes or '{}')
        except:
            return {}
    
    def set_themes(self, themes_dict):
        import json
        self.favorite_themes = json.dumps(themes_dict)
    
    def get_liked_books(self):
        import json
        try:
            return json.loads(self.liked_books or '[]')
        except:
            return []
    
    def add_liked_book(self, title, author, rating=5):
        import json
        books = self.get_liked_books()
        # Check if already exists
        for book in books:
            if book.get('title', '').lower() == title.lower():
                book['rating'] = rating
                self.liked_books = json.dumps(books)
                return
        books.append({'title': title, 'author': author, 'rating': rating})
        self.liked_books = json.dumps(books[-50:])  # Keep last 50
    
    def to_dict(self):
        return {
            'id': self.id,
            'genres': self.get_genres(),
            'themes': self.get_themes(),
            'liked_books': self.get_liked_books(),
            'books_analyzed': self.books_analyzed,
            'taste_summary': self.taste_summary,
            'last_updated': self.last_updated.strftime('%Y-%m-%d') if self.last_updated else None
        }


class BookPrediction(db.Model):
    """Store AI predictions for books user might like"""
    __tablename__ = 'book_predictions'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Book info
    book_title = db.Column(db.String(300), nullable=False)
    book_author = db.Column(db.String(200), nullable=True)
    
    # Prediction details
    match_score = db.Column(db.Float, default=0.0)  # 0-100 percentage
    reasons = db.Column(db.Text, nullable=True)  # JSON list of reasons
    
    # Status
    was_explored = db.Column(db.Boolean, default=False)
    user_feedback = db.Column(db.String(20), nullable=True)  # 'liked', 'disliked', 'neutral'
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('predictions', lazy='dynamic'))
    
    def get_reasons(self):
        import json
        try:
            return json.loads(self.reasons or '[]')
        except:
            return []
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.book_title,
            'author': self.book_author,
            'match_score': self.match_score,
            'reasons': self.get_reasons(),
            'was_explored': self.was_explored,
            'feedback': self.user_feedback,
            'created_at': self.created_at.strftime('%Y-%m-%d')
        }


class PromoCode(db.Model):
    """Promotional codes for discounts"""
    __tablename__ = 'promo_codes'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    discount_percent = db.Column(db.Integer, default=10)  # 10 = 10%
    discount_type = db.Column(db.String(20), default='percent')  # percent, fixed, trial
    valid_from = db.Column(db.DateTime, default=datetime.utcnow)
    valid_until = db.Column(db.DateTime, nullable=True)
    max_uses = db.Column(db.Integer, default=100)
    current_uses = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    applies_to = db.Column(db.String(20), default='all')  # all, pro, premium
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    def is_valid(self):
        if not self.is_active:
            return False
        if self.current_uses >= self.max_uses:
            return False
        if self.valid_until and datetime.utcnow() > self.valid_until:
            return False
        return True
    
    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'discount_percent': self.discount_percent,
            'discount_type': self.discount_type,
            'valid_until': self.valid_until.strftime('%Y-%m-%d') if self.valid_until else None,
            'max_uses': self.max_uses,
            'current_uses': self.current_uses,
            'is_active': self.is_active,
            'applies_to': self.applies_to,
            'is_valid': self.is_valid()
        }


class ErrorLog(db.Model):
    """Log of application errors"""
    __tablename__ = 'error_logs'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    error_type = db.Column(db.String(100), nullable=False)
    error_message = db.Column(db.Text, nullable=False)
    endpoint = db.Column(db.String(200), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    stack_trace = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_resolved = db.Column(db.Boolean, default=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'error_type': self.error_type,
            'error_message': self.error_message[:200] + '...' if len(self.error_message) > 200 else self.error_message,
            'endpoint': self.endpoint,
            'user_id': self.user_id,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'is_resolved': self.is_resolved
        }


class LoginLog(db.Model):
    """Track user login activity"""
    __tablename__ = 'login_logs'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    ip_address = db.Column(db.String(50), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    device_type = db.Column(db.String(50), nullable=True)  # desktop, mobile, tablet
    country = db.Column(db.String(100), nullable=True)
    success = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('login_logs', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'ip_address': self.ip_address,
            'device_type': self.device_type,
            'success': self.success,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }


class EmailTemplate(db.Model):
    """Email templates for mass communication"""
    __tablename__ = 'email_templates'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    template_type = db.Column(db.String(50), default='general')  # general, promo, newsletter
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'subject': self.subject,
            'body': self.body[:100] + '...' if len(self.body) > 100 else self.body,
            'template_type': self.template_type,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }


class ScheduledNotification(db.Model):
    """Scheduled notifications for future delivery"""
    __tablename__ = 'scheduled_notifications'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    scheduled_for = db.Column(db.DateTime, nullable=False)
    target_segment = db.Column(db.String(50), default='all')  # all, free, pro, premium
    is_sent = db.Column(db.Boolean, default=False)
    sent_at = db.Column(db.DateTime, nullable=True)
    sent_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message[:100] + '...' if len(self.message) > 100 else self.message,
            'scheduled_for': self.scheduled_for.strftime('%Y-%m-%d %H:%M'),
            'target_segment': self.target_segment,
            'is_sent': self.is_sent,
            'sent_count': self.sent_count
        }


class AdminGoal(db.Model):
    """Admin goals and targets"""
    __tablename__ = 'admin_goals'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(200), nullable=False)
    goal_type = db.Column(db.String(50), nullable=False)  # users, revenue, analyses
    target_value = db.Column(db.Integer, nullable=False)
    current_value = db.Column(db.Integer, default=0)
    deadline = db.Column(db.DateTime, nullable=True)
    is_completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        progress = (self.current_value / self.target_value * 100) if self.target_value > 0 else 0
        return {
            'id': self.id,
            'title': self.title,
            'goal_type': self.goal_type,
            'target_value': self.target_value,
            'current_value': self.current_value,
            'progress': round(min(progress, 100), 1),
            'deadline': self.deadline.strftime('%Y-%m-%d') if self.deadline else None,
            'is_completed': self.is_completed
        }


class AppSettings(db.Model):
    """Application settings and configuration"""
    __tablename__ = 'app_settings'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
    value_type = db.Column(db.String(20), default='string')  # string, int, float, bool, json
    description = db.Column(db.String(500), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @staticmethod
    def get(key, default=None):
        setting = AppSettings.query.filter_by(key=key).first()
        if not setting:
            return default
        if setting.value_type == 'int':
            return int(setting.value)
        if setting.value_type == 'float':
            return float(setting.value)
        if setting.value_type == 'bool':
            return setting.value.lower() == 'true'
        if setting.value_type == 'json':
            import json
            return json.loads(setting.value)
        return setting.value


class BlockedIP(db.Model):
    """Blocked IP addresses"""
    __tablename__ = 'blocked_ips'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ip_address = db.Column(db.String(50), unique=True, nullable=False)
    reason = db.Column(db.String(500), nullable=True)
    blocked_at = db.Column(db.DateTime, default=datetime.utcnow)
    blocked_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)  # None = permanent
    
    def is_active(self):
        if self.expires_at is None:
            return True
        return datetime.utcnow() < self.expires_at
    
    def to_dict(self):
        return {
            'id': self.id,
            'ip_address': self.ip_address,
            'reason': self.reason,
            'blocked_at': self.blocked_at.strftime('%Y-%m-%d %H:%M'),
            'expires_at': self.expires_at.strftime('%Y-%m-%d %H:%M') if self.expires_at else 'Permanente',
            'is_active': self.is_active()
        }
