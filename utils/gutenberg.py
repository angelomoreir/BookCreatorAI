"""
Project Gutenberg integration for public domain books.
Provides search and text retrieval for books in the public domain.
"""
import requests
import re
import json
import logging
from datetime import datetime
from functools import lru_cache

logger = logging.getLogger(__name__)

# Gutenberg API endpoints
GUTENBERG_API = "https://gutendex.com/books"
GUTENBERG_MIRROR = "https://www.gutenberg.org"

# Authors known to be in public domain (died before 1954 = 70+ years)
# This is a sample list - the actual check uses death year
PUBLIC_DOMAIN_AUTHORS = {
    # Portuguese
    'luís de camões': 1580,
    'fernando pessoa': 1935,
    'eça de queirós': 1900,
    'eça de queiroz': 1900,
    'jose maria eca de queiroz': 1900,
    'almeida garrett': 1854,
    'camilo castelo branco': 1890,
    'júlio dinis': 1871,
    'alexandre herculano': 1877,
    'machado de assis': 1908,
    'josé de alencar': 1877,
    
    # English
    'william shakespeare': 1616,
    'jane austen': 1817,
    'charles dickens': 1870,
    'mark twain': 1910,
    'oscar wilde': 1900,
    'arthur conan doyle': 1930,
    'h.g. wells': 1946,
    'edgar allan poe': 1849,
    'herman melville': 1891,
    'bram stoker': 1912,
    'mary shelley': 1851,
    'lewis carroll': 1898,
    'robert louis stevenson': 1894,
    'h.p. lovecraft': 1937,
    'f. scott fitzgerald': 1940,
    
    # French
    'victor hugo': 1885,
    'alexandre dumas': 1870,
    'jules verne': 1905,
    'gustave flaubert': 1880,
    'honoré de balzac': 1850,
    'émile zola': 1902,
    
    # Russian
    'fiódor dostoiévski': 1881,
    'fyodor dostoevsky': 1881,
    'leo tolstoy': 1910,
    'lev tolstói': 1910,
    'anton chekhov': 1904,
    
    # Spanish
    'miguel de cervantes': 1616,
    
    # German
    'franz kafka': 1924,
    'johann wolfgang von goethe': 1832,
    
    # Italian
    'dante alighieri': 1321,
    
    # Greek
    'homer': -800,
    'homero': -800,
}

# Books known to be in public domain with their Gutenberg IDs
KNOWN_BOOKS = {
    'os lusíadas': {'id': 3333, 'author': 'Luís de Camões'},
    'the lusiads': {'id': 3333, 'author': 'Luís de Camões'},
    'dom quixote': {'id': 996, 'author': 'Miguel de Cervantes'},
    'don quixote': {'id': 996, 'author': 'Miguel de Cervantes'},
    'pride and prejudice': {'id': 1342, 'author': 'Jane Austen'},
    'orgulho e preconceito': {'id': 1342, 'author': 'Jane Austen'},
    'crime and punishment': {'id': 2554, 'author': 'Fyodor Dostoevsky'},
    'crime e castigo': {'id': 2554, 'author': 'Fyodor Dostoevsky'},
    'moby dick': {'id': 2701, 'author': 'Herman Melville'},
    'dracula': {'id': 345, 'author': 'Bram Stoker'},
    'drácula': {'id': 345, 'author': 'Bram Stoker'},
    'frankenstein': {'id': 84, 'author': 'Mary Shelley'},
    'the adventures of sherlock holmes': {'id': 1661, 'author': 'Arthur Conan Doyle'},
    'sherlock holmes': {'id': 1661, 'author': 'Arthur Conan Doyle'},
    'a tale of two cities': {'id': 98, 'author': 'Charles Dickens'},
    'alice in wonderland': {'id': 11, 'author': 'Lewis Carroll'},
    'alice no país das maravilhas': {'id': 11, 'author': 'Lewis Carroll'},
    'the picture of dorian gray': {'id': 174, 'author': 'Oscar Wilde'},
    'o retrato de dorian gray': {'id': 174, 'author': 'Oscar Wilde'},
    'war and peace': {'id': 2600, 'author': 'Leo Tolstoy'},
    'guerra e paz': {'id': 2600, 'author': 'Leo Tolstoy'},
    'the great gatsby': {'id': 64317, 'author': 'F. Scott Fitzgerald'},
    'o grande gatsby': {'id': 64317, 'author': 'F. Scott Fitzgerald'},
    'les misérables': {'id': 135, 'author': 'Victor Hugo'},
    'os miseráveis': {'id': 135, 'author': 'Victor Hugo'},
    'the count of monte cristo': {'id': 1184, 'author': 'Alexandre Dumas'},
    'o conde de monte cristo': {'id': 1184, 'author': 'Alexandre Dumas'},
    'twenty thousand leagues under the sea': {'id': 164, 'author': 'Jules Verne'},
    'vinte mil léguas submarinas': {'id': 164, 'author': 'Jules Verne'},
    'the metamorphosis': {'id': 5200, 'author': 'Franz Kafka'},
    'a metamorfose': {'id': 5200, 'author': 'Franz Kafka'},
    'the divine comedy': {'id': 8800, 'author': 'Dante Alighieri'},
    'a divina comédia': {'id': 8800, 'author': 'Dante Alighieri'},
    'the odyssey': {'id': 1727, 'author': 'Homer'},
    'odisseia': {'id': 1727, 'author': 'Homer'},
    'the iliad': {'id': 6130, 'author': 'Homer'},
    'ilíada': {'id': 6130, 'author': 'Homer'},
    'hamlet': {'id': 1524, 'author': 'William Shakespeare'},
    'romeo and juliet': {'id': 1112, 'author': 'William Shakespeare'},
    'romeu e julieta': {'id': 1112, 'author': 'William Shakespeare'},
    'macbeth': {'id': 1533, 'author': 'William Shakespeare'},
    'a christmas carol': {'id': 46, 'author': 'Charles Dickens'},
    'um conto de natal': {'id': 46, 'author': 'Charles Dickens'},
    'treasure island': {'id': 120, 'author': 'Robert Louis Stevenson'},
    'a ilha do tesouro': {'id': 120, 'author': 'Robert Louis Stevenson'},
    'the strange case of dr jekyll and mr hyde': {'id': 43, 'author': 'Robert Louis Stevenson'},
    'dr jekyll e mr hyde': {'id': 43, 'author': 'Robert Louis Stevenson'},
    'the call of the wild': {'id': 215, 'author': 'Jack London'},
    'wuthering heights': {'id': 768, 'author': 'Emily Brontë'},
    'o morro dos ventos uivantes': {'id': 768, 'author': 'Emily Brontë'},
    'jane eyre': {'id': 1260, 'author': 'Charlotte Brontë'},
    'the scarlet letter': {'id': 25344, 'author': 'Nathaniel Hawthorne'},
    'a letra escarlate': {'id': 25344, 'author': 'Nathaniel Hawthorne'},
}


def is_public_domain(author_name: str, publication_year: int = None) -> bool:
    """
    Check if a book is likely in the public domain.
    Rules vary by country, but generally:
    - Author died 70+ years ago (EU/US)
    - Or published before 1928 (US)
    """
    if not author_name:
        return False
    
    author_lower = author_name.lower().strip()
    
    # Check known authors
    for known_author, death_year in PUBLIC_DOMAIN_AUTHORS.items():
        if known_author in author_lower or author_lower in known_author:
            current_year = datetime.now().year
            if current_year - death_year >= 70:
                return True
    
    # Check by publication year (US rule: before 1928)
    if publication_year and publication_year < 1928:
        return True
    
    return False


def search_gutenberg(title: str, author: str = None, language: str = 'en') -> list:
    """
    Search Project Gutenberg for books.
    Returns list of matching books with metadata.
    """
    try:
        # First check known books
        title_lower = title.lower().strip()
        if title_lower in KNOWN_BOOKS:
            book_info = KNOWN_BOOKS[title_lower]
            return [{
                'id': book_info['id'],
                'title': title,
                'author': book_info['author'],
                'language': language,
                'source': 'gutenberg',
                'is_public_domain': True
            }]
        
        # Search Gutenberg API
        params = {'search': title}
        if language:
            lang_map = {'pt-pt': 'pt', 'pt-br': 'pt', 'en': 'en', 'fr': 'fr', 'de': 'de', 'es': 'es', 'it': 'it'}
            params['languages'] = lang_map.get(language, language[:2])
        
        response = requests.get(GUTENBERG_API, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for book in data.get('results', [])[:10]:
            authors = book.get('authors', [])
            author_name = authors[0].get('name', 'Unknown') if authors else 'Unknown'
            
            results.append({
                'id': book.get('id'),
                'title': book.get('title'),
                'author': author_name,
                'language': book.get('languages', ['en'])[0],
                'source': 'gutenberg',
                'is_public_domain': True,
                'download_count': book.get('download_count', 0),
                'formats': list(book.get('formats', {}).keys())
            })
        
        return results
        
    except Exception as e:
        logger.warning(f"Gutenberg search error: {e}")
        return []


def get_book_text(gutenberg_id: int) -> dict:
    """
    Get the full text of a book from Project Gutenberg.
    Returns dict with text, chapters, and metadata.
    """
    try:
        # Try different text formats
        text_urls = [
            f"{GUTENBERG_MIRROR}/cache/epub/{gutenberg_id}/pg{gutenberg_id}.txt",
            f"{GUTENBERG_MIRROR}/files/{gutenberg_id}/{gutenberg_id}-0.txt",
            f"{GUTENBERG_MIRROR}/files/{gutenberg_id}/{gutenberg_id}.txt",
        ]
        
        text = None
        for url in text_urls:
            try:
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    text = response.text
                    break
            except:
                continue
        
        if not text:
            # Try the API to get format URLs
            api_response = requests.get(f"{GUTENBERG_API}/{gutenberg_id}", timeout=10)
            if api_response.status_code == 200:
                book_data = api_response.json()
                formats = book_data.get('formats', {})
                
                # Prefer plain text
                for fmt_key in ['text/plain; charset=utf-8', 'text/plain', 'text/plain; charset=us-ascii']:
                    if fmt_key in formats:
                        text_url = formats[fmt_key]
                        response = requests.get(text_url, timeout=30)
                        if response.status_code == 200:
                            text = response.text
                            break
        
        if not text:
            return {'success': False, 'error': 'Texto não encontrado'}
        
        # Clean up the text
        text = clean_gutenberg_text(text)
        
        # Extract chapters
        chapters = extract_chapters(text)
        
        # Get metadata
        metadata = get_book_metadata(gutenberg_id)
        
        return {
            'success': True,
            'text': text,
            'chapters': chapters,
            'metadata': metadata,
            'word_count': len(text.split()),
            'source': 'Project Gutenberg'
        }
        
    except Exception as e:
        logger.warning(f"Error getting book text: {e}")
        return {'success': False, 'error': str(e)}


def clean_gutenberg_text(text: str) -> str:
    """
    Remove Gutenberg headers, footers, and clean up text.
    """
    # Remove Gutenberg header
    header_patterns = [
        r'\*\*\* START OF.*?\*\*\*',
        r'\*\*\* START OF THE PROJECT GUTENBERG.*?\*\*\*',
        r'The Project Gutenberg [Ee]Book.*?(?=\n\n)',
    ]
    
    for pattern in header_patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            text = text[match.end():]
            break
    
    # Remove Gutenberg footer
    footer_patterns = [
        r'\*\*\* END OF.*',
        r'\*\*\* END OF THE PROJECT GUTENBERG.*',
        r'End of.*Project Gutenberg.*',
    ]
    
    for pattern in footer_patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            text = text[:match.start()]
            break
    
    # Clean up extra whitespace
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    text = text.strip()
    
    return text


def extract_chapters(text: str) -> list:
    """
    Extract chapter titles and positions from text.
    """
    chapters = []
    
    # Common chapter patterns
    patterns = [
        r'^(CHAPTER|CAPÍTULO|CAPITULO|Chapter|Capítulo)\s+([IVXLCDM]+|\d+)[.\s]*(.*)$',
        r'^(PART|PARTE|Part|Parte)\s+([IVXLCDM]+|\d+)[.\s]*(.*)$',
        r'^(BOOK|LIVRO|Book|Livro)\s+([IVXLCDM]+|\d+)[.\s]*(.*)$',
        r'^([IVXLCDM]+)\.\s*(.+)$',
        r'^(\d+)\.\s*(.+)$',
    ]
    
    lines = text.split('\n')
    for i, line in enumerate(lines):
        line = line.strip()
        for pattern in patterns:
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                chapters.append({
                    'title': line,
                    'position': sum(len(l) + 1 for l in lines[:i])
                })
                break
    
    # If no chapters found, create artificial divisions
    if not chapters:
        text_length = len(text)
        num_sections = min(10, max(3, text_length // 10000))
        section_size = text_length // num_sections
        
        for i in range(num_sections):
            chapters.append({
                'title': f'Secção {i + 1}',
                'position': i * section_size
            })
    
    return chapters


@lru_cache(maxsize=100)
def get_book_metadata(gutenberg_id: int) -> dict:
    """
    Get book metadata from Gutenberg API.
    """
    try:
        response = requests.get(f"{GUTENBERG_API}/{gutenberg_id}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            authors = data.get('authors', [])
            
            return {
                'title': data.get('title'),
                'author': authors[0].get('name') if authors else 'Unknown',
                'author_birth': authors[0].get('birth_year') if authors else None,
                'author_death': authors[0].get('death_year') if authors else None,
                'languages': data.get('languages', []),
                'subjects': data.get('subjects', []),
                'bookshelves': data.get('bookshelves', []),
                'download_count': data.get('download_count', 0),
                'copyright': data.get('copyright', False),
            }
    except Exception as e:
        logger.warning(f"Error getting metadata: {e}")
    
    return {}


def check_book_availability(title: str, author: str = None) -> dict:
    """
    Check if a book is available for reading.
    Returns availability status and source.
    """
    title_lower = title.lower().strip()
    
    # Check known books first
    if title_lower in KNOWN_BOOKS:
        book_info = KNOWN_BOOKS[title_lower]
        return {
            'available': True,
            'source': 'gutenberg',
            'gutenberg_id': book_info['id'],
            'is_public_domain': True,
            'message': 'Livro disponível para leitura gratuita!'
        }
    
    # Check if author is in public domain
    if author and is_public_domain(author):
        # Search Gutenberg
        results = search_gutenberg(title, author)
        if results:
            return {
                'available': True,
                'source': 'gutenberg',
                'gutenberg_id': results[0]['id'],
                'is_public_domain': True,
                'message': 'Livro disponível para leitura gratuita!'
            }
    
    # Not available
    return {
        'available': False,
        'source': None,
        'is_public_domain': False,
        'message': 'Este livro ainda está protegido por direitos de autor.'
    }
