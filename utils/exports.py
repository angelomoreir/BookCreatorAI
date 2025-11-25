"""
BookCreatorAI - Export Utilities
PDF and EPUB generation
"""

import io
import re
from datetime import datetime

# PDF Generation
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# EPUB Generation
from ebooklib import epub


def generate_pdf(book):
    """
    Generate a PDF file from a book object.
    Returns bytes of the PDF file.
    """
    buffer = io.BytesIO()
    
    # Create PDF document
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
        'BookTitle',
        parent=styles['Heading1'],
        fontSize=28,
        alignment=TA_CENTER,
        spaceAfter=30,
        textColor=HexColor('#4B0082')
    )
    
    subtitle_style = ParagraphStyle(
        'BookSubtitle',
        parent=styles['Normal'],
        fontSize=14,
        alignment=TA_CENTER,
        spaceAfter=10,
        textColor=HexColor('#666666')
    )
    
    chapter_style = ParagraphStyle(
        'ChapterTitle',
        parent=styles['Heading2'],
        fontSize=18,
        spaceBefore=30,
        spaceAfter=20,
        textColor=HexColor('#4B0082')
    )
    
    body_style = ParagraphStyle(
        'BookBody',
        parent=styles['Normal'],
        fontSize=11,
        alignment=TA_JUSTIFY,
        spaceAfter=12,
        leading=16
    )
    
    toc_style = ParagraphStyle(
        'TOC',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=8,
        leftIndent=20
    )
    
    # Build document content
    story = []
    
    # === COVER PAGE ===
    story.append(Spacer(1, 5*cm))
    story.append(Paragraph(book.title, title_style))
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph(f"Tema: {book.theme}", subtitle_style))
    story.append(Paragraph(f"Estilo: {book.style}", subtitle_style))
    story.append(Spacer(1, 2*cm))
    
    # Book stats
    stats = book.get_stats()
    stats_text = f"""
    <para align="center">
    {stats['word_count']:,} palavras | {stats['page_count']} páginas | {stats['chapter_count']} capítulos<br/>
    Tempo de leitura: ~{stats['reading_time']} minutos
    </para>
    """
    story.append(Paragraph(stats_text, subtitle_style))
    
    story.append(Spacer(1, 3*cm))
    story.append(Paragraph(f"Gerado em: {book.created_at.strftime('%d/%m/%Y')}", subtitle_style))
    story.append(Paragraph("Criado com BookCreatorAI", subtitle_style))
    story.append(PageBreak())
    
    # === TABLE OF CONTENTS ===
    story.append(Paragraph("Índice", title_style))
    story.append(Spacer(1, 1*cm))
    
    for i, chapter in enumerate(book.get_chapters(), 1):
        story.append(Paragraph(f"{chapter}", toc_style))
    
    story.append(PageBreak())
    
    # === BOOK CONTENT ===
    # Split text by chapters
    full_text = book.full_text
    
    # Try to split by chapter markers
    chapter_patterns = [
        r'(Capítulo\s+\d+[:\.\s])',
        r'(Chapter\s+\d+[:\.\s])',
        r'(Chapitre\s+\d+[:\.\s])',
        r'(Kapitel\s+\d+[:\.\s])',
        r'(Capitolo\s+\d+[:\.\s])'
    ]
    
    # Process text - split into paragraphs
    paragraphs = full_text.split('\n\n')
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        # Check if it's a chapter title
        is_chapter = False
        for pattern in chapter_patterns:
            if re.match(pattern, para, re.IGNORECASE):
                is_chapter = True
                break
        
        if is_chapter or para.startswith('Capítulo') or para.startswith('Chapter'):
            story.append(Paragraph(para, chapter_style))
        else:
            # Clean and add paragraph
            para = para.replace('\n', ' ')
            # Escape special characters for ReportLab
            para = para.replace('&', '&amp;')
            para = para.replace('<', '&lt;')
            para = para.replace('>', '&gt;')
            try:
                story.append(Paragraph(para, body_style))
            except:
                # If paragraph fails, add as plain text
                story.append(Paragraph(para[:500] + "...", body_style))
    
    # === FINAL PAGE ===
    story.append(PageBreak())
    story.append(Spacer(1, 5*cm))
    story.append(Paragraph("FIM", title_style))
    story.append(Spacer(1, 2*cm))
    story.append(Paragraph("Este livro foi gerado por BookCreatorAI", subtitle_style))
    story.append(Paragraph("Powered by Google Gemini AI", subtitle_style))
    
    # Build PDF
    doc.build(story)
    
    buffer.seek(0)
    return buffer.getvalue()


def generate_epub(book):
    """
    Generate an EPUB file from a book object.
    Returns bytes of the EPUB file.
    """
    # Create EPUB book
    epub_book = epub.EpubBook()
    
    # Set metadata
    epub_book.set_identifier(f'bookcreatorai-{book.id}')
    epub_book.set_title(book.title)
    epub_book.set_language(book.language or 'pt')
    epub_book.add_author('BookCreatorAI')
    
    # Add metadata
    epub_book.add_metadata('DC', 'description', f'Tema: {book.theme}')
    epub_book.add_metadata('DC', 'subject', book.style)
    epub_book.add_metadata('DC', 'date', book.created_at.strftime('%Y-%m-%d'))
    
    # CSS Style
    style = '''
    @namespace epub "http://www.idpf.org/2007/ops";
    body {
        font-family: Georgia, serif;
        line-height: 1.6;
        margin: 5%;
    }
    h1 {
        text-align: center;
        color: #4B0082;
        margin-bottom: 2em;
    }
    h2 {
        color: #4B0082;
        margin-top: 2em;
        margin-bottom: 1em;
    }
    p {
        text-align: justify;
        text-indent: 1.5em;
        margin: 0.5em 0;
    }
    .cover {
        text-align: center;
        padding-top: 30%;
    }
    .cover h1 {
        font-size: 2em;
        margin-bottom: 0.5em;
    }
    .cover .meta {
        color: #666;
        font-style: italic;
    }
    .stats {
        text-align: center;
        color: #888;
        font-size: 0.9em;
        margin: 2em 0;
    }
    .toc-title {
        text-align: center;
    }
    .toc-list {
        list-style: none;
        padding: 0;
    }
    .toc-list li {
        margin: 0.5em 0;
    }
    .footer {
        text-align: center;
        margin-top: 3em;
        color: #888;
        font-size: 0.9em;
    }
    '''
    
    nav_css = epub.EpubItem(
        uid="style_nav",
        file_name="style/nav.css",
        media_type="text/css",
        content=style
    )
    epub_book.add_item(nav_css)
    
    # === COVER CHAPTER ===
    stats = book.get_stats()
    cover_content = f'''
    <html>
    <head><link rel="stylesheet" type="text/css" href="style/nav.css"/></head>
    <body>
        <div class="cover">
            <h1>{book.title}</h1>
            <p class="meta">Tema: {book.theme}</p>
            <p class="meta">Estilo: {book.style}</p>
            <div class="stats">
                {stats['word_count']:,} palavras | {stats['page_count']} páginas | {stats['chapter_count']} capítulos<br/>
                Tempo de leitura: ~{stats['reading_time']} minutos
            </div>
            <p class="meta">Gerado em {book.created_at.strftime('%d/%m/%Y')}</p>
            <p class="meta">Criado com BookCreatorAI</p>
        </div>
    </body>
    </html>
    '''
    
    cover_chapter = epub.EpubHtml(title='Capa', file_name='cover.xhtml', lang=book.language or 'pt')
    cover_chapter.content = cover_content
    cover_chapter.add_item(nav_css)
    epub_book.add_item(cover_chapter)
    
    # === TABLE OF CONTENTS CHAPTER ===
    toc_items = ''.join([f'<li>{ch}</li>' for ch in book.get_chapters()])
    toc_content = f'''
    <html>
    <head><link rel="stylesheet" type="text/css" href="style/nav.css"/></head>
    <body>
        <h1 class="toc-title">Índice</h1>
        <ul class="toc-list">
            {toc_items}
        </ul>
    </body>
    </html>
    '''
    
    toc_chapter = epub.EpubHtml(title='Índice', file_name='toc.xhtml', lang=book.language or 'pt')
    toc_chapter.content = toc_content
    toc_chapter.add_item(nav_css)
    epub_book.add_item(toc_chapter)
    
    # === MAIN CONTENT ===
    # Split content by chapters
    full_text = book.full_text
    chapters_list = book.get_chapters()
    
    # Create content chapters
    content_chapters = []
    
    # Try to split by chapter markers
    chapter_pattern = r'((?:Capítulo|Chapter|Chapitre|Kapitel|Capitolo)\s+\d+[:\.\s][^\n]*)'
    parts = re.split(chapter_pattern, full_text, flags=re.IGNORECASE)
    
    if len(parts) > 1:
        # We have chapter markers
        current_title = "Introdução"
        current_content = []
        chapter_num = 0
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            if re.match(r'(?:Capítulo|Chapter|Chapitre|Kapitel|Capitolo)\s+\d+', part, re.IGNORECASE):
                # Save previous chapter
                if current_content:
                    content = '<p>' + '</p><p>'.join(current_content) + '</p>'
                    ch = epub.EpubHtml(
                        title=current_title,
                        file_name=f'chapter_{chapter_num}.xhtml',
                        lang=book.language or 'pt'
                    )
                    ch.content = f'''
                    <html>
                    <head><link rel="stylesheet" type="text/css" href="style/nav.css"/></head>
                    <body>
                        <h2>{current_title}</h2>
                        {content}
                    </body>
                    </html>
                    '''
                    ch.add_item(nav_css)
                    epub_book.add_item(ch)
                    content_chapters.append(ch)
                
                current_title = part
                current_content = []
                chapter_num += 1
            else:
                # Content paragraph
                paragraphs = part.split('\n\n')
                for p in paragraphs:
                    p = p.strip().replace('\n', ' ')
                    if p:
                        # Escape HTML
                        p = p.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        current_content.append(p)
        
        # Save last chapter
        if current_content:
            content = '<p>' + '</p><p>'.join(current_content) + '</p>'
            ch = epub.EpubHtml(
                title=current_title,
                file_name=f'chapter_{chapter_num}.xhtml',
                lang=book.language or 'pt'
            )
            ch.content = f'''
            <html>
            <head><link rel="stylesheet" type="text/css" href="style/nav.css"/></head>
            <body>
                <h2>{current_title}</h2>
                {content}
            </body>
            </html>
            '''
            ch.add_item(nav_css)
            epub_book.add_item(ch)
            content_chapters.append(ch)
    else:
        # No chapter markers, create single content chapter
        paragraphs = full_text.split('\n\n')
        content = ''
        for p in paragraphs:
            p = p.strip().replace('\n', ' ')
            if p:
                p = p.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                content += f'<p>{p}</p>'
        
        main_chapter = epub.EpubHtml(
            title='Conteúdo',
            file_name='content.xhtml',
            lang=book.language or 'pt'
        )
        main_chapter.content = f'''
        <html>
        <head><link rel="stylesheet" type="text/css" href="style/nav.css"/></head>
        <body>
            <h1>{book.title}</h1>
            {content}
        </body>
        </html>
        '''
        main_chapter.add_item(nav_css)
        epub_book.add_item(main_chapter)
        content_chapters.append(main_chapter)
    
    # === END CHAPTER ===
    end_content = '''
    <html>
    <head><link rel="stylesheet" type="text/css" href="style/nav.css"/></head>
    <body>
        <div class="cover">
            <h1>FIM</h1>
            <p class="footer">Este livro foi gerado por BookCreatorAI</p>
            <p class="footer">Powered by Google Gemini AI</p>
        </div>
    </body>
    </html>
    '''
    
    end_chapter = epub.EpubHtml(title='Fim', file_name='end.xhtml', lang=book.language or 'pt')
    end_chapter.content = end_content
    end_chapter.add_item(nav_css)
    epub_book.add_item(end_chapter)
    
    # Define Table of Contents
    epub_book.toc = [cover_chapter, toc_chapter] + content_chapters + [end_chapter]
    
    # Add navigation files
    epub_book.add_item(epub.EpubNcx())
    epub_book.add_item(epub.EpubNav())
    
    # Define spine
    epub_book.spine = ['nav', cover_chapter, toc_chapter] + content_chapters + [end_chapter]
    
    # Write to buffer
    buffer = io.BytesIO()
    epub.write_epub(buffer, epub_book)
    buffer.seek(0)
    
    return buffer.getvalue()
