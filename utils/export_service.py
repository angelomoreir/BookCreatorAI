"""
Export Service - PDF and EPUB generation for book analyses
"""
import io
import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

try:
    from ebooklib import epub
    EPUB_AVAILABLE = True
except ImportError:
    EPUB_AVAILABLE = False


def generate_pdf(book_title, book_author, analyses, user_name=None):
    """
    Generate a PDF document with book analyses.
    
    Args:
        book_title: Title of the book
        book_author: Author of the book
        analyses: List of analysis dicts with 'aspect', 'aspect_label', 'content', 'created_at'
        user_name: Optional user name for personalization
    
    Returns:
        BytesIO buffer containing the PDF
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#7c3aed')
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=20,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#6b7280')
    )
    
    section_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=16,
        spaceBefore=20,
        spaceAfter=10,
        textColor=colors.HexColor('#8b5cf6')
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=11,
        leading=16,
        alignment=TA_JUSTIFY,
        spaceAfter=12
    )
    
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#9ca3af')
    )
    
    # Helper function to escape HTML
    def escape_html(text):
        if not text:
            return text
        text = str(text)
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        return text
    
    # Build document content
    story = []
    
    # Escape title and author
    safe_title = escape_html(book_title)
    safe_author = escape_html(book_author)
    
    # Title page
    story.append(Spacer(1, 3*cm))
    story.append(Paragraph("📚 Análise Literária", title_style))
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph(f"<b>{safe_title}</b>", title_style))
    if book_author:
        story.append(Paragraph(f"por {safe_author}", subtitle_style))
    story.append(Spacer(1, 2*cm))
    
    # Metadata
    meta_data = [
        ['Gerado em:', datetime.now().strftime('%d/%m/%Y às %H:%M')],
        ['Plataforma:', 'Alma do Livro'],
    ]
    if user_name:
        meta_data.insert(0, ['Utilizador:', user_name])
    
    meta_table = Table(meta_data, colWidths=[4*cm, 8*cm])
    meta_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#6b7280')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(meta_table)
    
    story.append(PageBreak())
    
    # Table of contents
    story.append(Paragraph("📑 Índice", section_style))
    story.append(Spacer(1, 0.5*cm))
    
    for i, analysis in enumerate(analyses, 1):
        aspect_label = analysis.get('aspect_label', analysis.get('aspect', 'Análise'))
        story.append(Paragraph(f"{i}. {aspect_label}", body_style))
    
    story.append(PageBreak())
    
    # Analyses content
    for analysis in analyses:
        aspect_label = analysis.get('aspect_label', analysis.get('aspect', 'Análise'))
        content = analysis.get('content', '')
        
        # Section header
        story.append(Paragraph(aspect_label, section_style))
        
        # Content - split into paragraphs
        paragraphs = content.split('\n\n')
        for para in paragraphs:
            if para.strip():
                # Escape HTML special characters first
                para = escape_html(para)
                para = para.strip()
                if para:
                    try:
                        story.append(Paragraph(para, body_style))
                    except Exception:
                        # If paragraph fails, add as plain text without any tags
                        clean_para = para.replace('&lt;', '').replace('&gt;', '').replace('&amp;', '&')
                        story.append(Paragraph(clean_para, body_style))
        
        story.append(Spacer(1, 1*cm))
    
    # Footer
    story.append(Spacer(1, 2*cm))
    story.append(Paragraph("─" * 50, footer_style))
    story.append(Paragraph("Gerado por Alma do Livro - almadelivro.pt", footer_style))
    story.append(Paragraph("A essência de qualquer livro, revelada pela IA", footer_style))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer


def generate_epub(book_title, book_author, analyses, user_name=None):
    """
    Generate an EPUB document with book analyses.
    
    Args:
        book_title: Title of the book
        book_author: Author of the book
        analyses: List of analysis dicts with 'aspect', 'aspect_label', 'content', 'created_at'
        user_name: Optional user name for personalization
    
    Returns:
        BytesIO buffer containing the EPUB
    """
    if not EPUB_AVAILABLE:
        raise ImportError("ebooklib is not installed")
    
    book = epub.EpubBook()
    
    # Metadata
    book.set_identifier(f'almadelivro-{book_title.lower().replace(" ", "-")}-{datetime.now().timestamp()}')
    book.set_title(f'Análise: {book_title}')
    book.set_language('pt')
    book.add_author('Alma do Livro')
    if book_author:
        book.add_metadata('DC', 'description', f'Análise literária de "{book_title}" por {book_author}')
    
    # CSS Style
    style = '''
    @namespace epub "http://www.idpf.org/2007/ops";
    body {
        font-family: Georgia, serif;
        line-height: 1.6;
        color: #1a1a1a;
    }
    h1 {
        color: #7c3aed;
        text-align: center;
        margin-bottom: 1em;
    }
    h2 {
        color: #8b5cf6;
        border-bottom: 2px solid #e5e7eb;
        padding-bottom: 0.5em;
        margin-top: 2em;
    }
    p {
        text-align: justify;
        margin-bottom: 1em;
    }
    .meta {
        color: #6b7280;
        font-size: 0.9em;
        text-align: center;
        margin-bottom: 2em;
    }
    .footer {
        color: #9ca3af;
        font-size: 0.8em;
        text-align: center;
        margin-top: 3em;
        border-top: 1px solid #e5e7eb;
        padding-top: 1em;
    }
    '''
    
    nav_css = epub.EpubItem(
        uid="style_nav",
        file_name="style/nav.css",
        media_type="text/css",
        content=style
    )
    book.add_item(nav_css)
    
    chapters = []
    
    # Title page
    title_content = f'''
    <html>
    <head><link rel="stylesheet" href="style/nav.css" /></head>
    <body>
        <h1>📚 Análise Literária</h1>
        <h1>{book_title}</h1>
        <p class="meta">{f'por {book_author}' if book_author else ''}</p>
        <p class="meta">Gerado em {datetime.now().strftime('%d/%m/%Y')}</p>
        <p class="meta">Plataforma: Alma do Livro</p>
        {f'<p class="meta">Utilizador: {user_name}</p>' if user_name else ''}
    </body>
    </html>
    '''
    
    title_chapter = epub.EpubHtml(title='Capa', file_name='title.xhtml', lang='pt')
    title_chapter.content = title_content
    title_chapter.add_item(nav_css)
    book.add_item(title_chapter)
    chapters.append(title_chapter)
    
    # Analysis chapters
    for i, analysis in enumerate(analyses, 1):
        aspect_label = analysis.get('aspect_label', analysis.get('aspect', 'Análise'))
        content = analysis.get('content', '')
        
        # Convert content to HTML paragraphs
        paragraphs = content.split('\n\n')
        html_content = ''
        for para in paragraphs:
            if para.strip():
                # Handle markdown-like formatting
                para = para.replace('**', '<strong>').replace('**', '</strong>')
                para = para.replace('*', '<em>').replace('*', '</em>')
                html_content += f'<p>{para.strip()}</p>\n'
        
        chapter_content = f'''
        <html>
        <head><link rel="stylesheet" href="style/nav.css" /></head>
        <body>
            <h2>{aspect_label}</h2>
            {html_content}
        </body>
        </html>
        '''
        
        chapter = epub.EpubHtml(
            title=aspect_label,
            file_name=f'chapter_{i}.xhtml',
            lang='pt'
        )
        chapter.content = chapter_content
        chapter.add_item(nav_css)
        book.add_item(chapter)
        chapters.append(chapter)
    
    # Footer chapter
    footer_content = '''
    <html>
    <head><link rel="stylesheet" href="style/nav.css" /></head>
    <body>
        <div class="footer">
            <p>Gerado por Alma do Livro</p>
            <p>almadelivro.pt</p>
            <p>A essência de qualquer livro, revelada pela IA</p>
        </div>
    </body>
    </html>
    '''
    
    footer_chapter = epub.EpubHtml(title='Sobre', file_name='footer.xhtml', lang='pt')
    footer_chapter.content = footer_content
    footer_chapter.add_item(nav_css)
    book.add_item(footer_chapter)
    chapters.append(footer_chapter)
    
    # Navigation
    book.toc = tuple(chapters)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    
    # Spine
    book.spine = ['nav'] + chapters
    
    # Write to buffer
    buffer = io.BytesIO()
    epub.write_epub(buffer, book)
    buffer.seek(0)
    return buffer


def get_aspect_label(aspect):
    """Get human-readable label for aspect"""
    labels = {
        'summary': '📝 Resumo Completo',
        'characters': '👥 Personagens',
        'themes': '💡 Temas & Mensagens',
        'world': '🌍 Mundo & Cenário',
        'style': '✍️ Estilo Literário',
        'quotes': '💬 Citações Famosas',
        'discussion': '🎓 Questões de Discussão',
        'similar': '📚 Livros Similares',
        'trivia': '🎯 Curiosidades',
        'timeline': '📅 Cronologia',
        'symbolism': '🔮 Simbolismo',
        'adaptation': '🎬 Adaptações',
        'playlist': '🎵 Playlist Sugerida',
        'trailer': '🎬 Trailer Cinematográfico',
        'cover': '🎨 Prompt para Capa',
        'casting': '🎭 Casting do Filme',
        'quiz': '🎲 Quiz',
        'interview': '🎭 Entrevista',
        'chat': '💬 Conversa',
        'info': '📖 Informação',
        'recommendations': '🎯 Recomendações',
        'comparison': '⚖️ Comparação'
    }
    return labels.get(aspect, aspect.title())
