from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import secrets
import re

db = SQLAlchemy()

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
