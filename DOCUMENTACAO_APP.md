# 📚 BookCreatorAI - Documentação Completa

## Índice
1. [Introdução](#introdução)
2. [Tecnologias Utilizadas](#tecnologias-utilizadas)
3. [Estrutura do Projeto](#estrutura-do-projeto)
4. [Funcionalidades Principais](#funcionalidades-principais)
5. [Como Usar](#como-usar)
6. [API e Endpoints](#api-e-endpoints)
7. [Base de Dados](#base-de-dados)
8. [Deployment](#deployment)

---

## 1. Introdução

O **BookCreatorAI** é uma aplicação web inovadora que utiliza Inteligência Artificial (Google Gemini) para criar, explorar e interagir com livros. A aplicação permite aos utilizadores gerar livros completos automaticamente, explorar qualquer livro existente, e utilizar funcionalidades interativas únicas como entrevistas com personagens, quizzes, e muito mais.

### Objetivos da Aplicação:
- Criar livros originais usando IA
- Explorar e analisar livros existentes
- Proporcionar experiências interativas com o conteúdo literário
- Facilitar a aprendizagem e entretenimento através da literatura

---

## 2. Tecnologias Utilizadas

### Backend
| Tecnologia | Versão | Descrição |
|------------|--------|-----------|
| Python | 3.11 | Linguagem de programação principal |
| Flask | 3.0.0 | Framework web |
| SQLAlchemy | 3.1.1 | ORM para base de dados |
| SQLite | - | Base de dados relacional |
| Google Gemini AI | 2.0-flash | Modelo de IA para geração de texto |

### Frontend
| Tecnologia | Descrição |
|------------|-----------|
| HTML5 | Estrutura das páginas |
| Tailwind CSS | Framework de estilos |
| JavaScript (Vanilla) | Interatividade e chamadas API |

### Bibliotecas Adicionais
- **ReportLab**: Geração de ficheiros PDF
- **EbookLib**: Geração de ficheiros EPUB
- **Pillow**: Processamento de imagens
- **Gunicorn**: Servidor WSGI para produção

---

## 3. Estrutura do Projeto

```
BookCreatorAI/
├── app.py                 # Aplicação principal Flask
├── config.py              # Configurações (API keys, database)
├── requirements.txt       # Dependências Python
├── Procfile              # Comando de start para Render
├── render.yaml           # Configuração de deployment
│
├── models/
│   ├── __init__.py
│   └── book.py           # Modelos da base de dados (Book, Series)
│
├── templates/            # Templates HTML (Jinja2)
│   ├── index.html        # Página inicial
│   ├── create_book.html  # Criar novo livro
│   ├── list_books.html   # Lista de livros
│   ├── view_book.html    # Ver detalhes do livro
│   ├── read_book.html    # Ler livro
│   ├── book_explorer.html # Explorador de livros
│   ├── character_interview.html # Entrevista personagens
│   ├── book_quiz.html    # Quiz do livro
│   └── chat_book.html    # Chat sobre livro
│
├── static/
│   ├── script.js         # JavaScript principal
│   └── style.css         # Estilos adicionais
│
├── database/
│   └── books.db          # Base de dados SQLite
│
└── utils/                # Utilitários
    └── __init__.py
```

---

## 4. Funcionalidades Principais

### 4.1 📖 Criação de Livros com IA

**Descrição**: Gera livros completos automaticamente usando a API do Google Gemini.

**Como funciona**:
1. O utilizador escolhe um tema/título
2. Seleciona o estilo literário (romance, ficção científica, etc.)
3. Define o número de capítulos e páginas
4. A IA gera o livro completo com:
   - Título
   - Capítulos estruturados
   - Conteúdo narrativo
   - Capa gerada (prompt para IA de imagem)

**Localização**: `/create` ou botão "Criar Livro" na página inicial

---

### 4.2 📚 Biblioteca de Livros

**Descrição**: Gestão completa dos livros criados.

**Funcionalidades**:
- Listar todos os livros
- Ver detalhes de cada livro
- Ler livros online
- Exportar para PDF/EPUB
- Eliminar livros

**Localização**: `/books`

---

### 4.3 🔍 Explorador de Livros

**Descrição**: Analisa qualquer livro (existente na literatura) com IA.

**Aspetos Analisados**:
| Aspeto | Descrição |
|--------|-----------|
| 📝 Resumo | Sinopse completa do livro |
| 👥 Personagens | Lista e análise de personagens |
| 💡 Temas | Temas principais e mensagens |
| 🌍 Mundo | Cenário e ambientação |
| ✍️ Estilo | Análise do estilo literário |
| 💬 Citações | Citações famosas do livro |
| 🎓 Discussão | Questões para debate |
| 📚 Similares | Livros recomendados semelhantes |
| 🎯 Curiosidades | Factos interessantes |
| 📅 Cronologia | Linha temporal dos eventos |
| 🔮 Simbolismo | Símbolos e significados |
| 🎬 Adaptações | Filmes e séries baseados |

**Localização**: `/explorer`

---

### 4.4 🎮 Funcionalidades Interativas

#### 🎭 Entrevista com Personagens
**Descrição**: Chat em tempo real com qualquer personagem do livro.

**Como funciona**:
1. Selecionar um livro
2. Escolher um personagem
3. Fazer perguntas ao personagem
4. A IA responde "como se fosse" o personagem, mantendo a sua personalidade

**Localização**: Página do livro → "Entrevistar" ou Explorador → "Entrevistar"

---

#### 🎲 Quiz Interativo
**Descrição**: Quiz de 10 perguntas sobre o livro.

**Características**:
- 3 níveis de dificuldade (fácil, médio, difícil)
- Perguntas de escolha múltipla
- Explicações para cada resposta
- Pontuação final

**Localização**: Página do livro → "Quiz" ou Explorador → "Quiz"

---

#### 📖 Continuar História
**Descrição**: Gera continuações para o livro.

**Tipos de continuação**:
- **Próximo Capítulo**: Continua a história
- **Epílogo**: O que aconteceu depois
- **Sequela**: Início de um novo livro

**Localização**: Página do livro → "Continuar" ou Explorador → "Continuar"

---

#### 🔀 Final Alternativo
**Descrição**: Explora cenários "E se...?" com finais diferentes.

**Como funciona**:
1. Escrever um cenário alternativo (ex: "E se o protagonista não tivesse sobrevivido?")
2. A IA gera um final alternativo coerente com o universo do livro

**Localização**: Explorador → "Final Alternativo"

---

#### 🎵 Playlist Sugerida
**Descrição**: Gera uma lista de músicas que combinam com o livro.

**Características**:
- 12-15 músicas reais
- Explicação de porque cada música combina
- Variedade de géneros musicais
- Organizada por momentos/temas do livro

**Localização**: Explorador → "Playlist"

---

#### 🎬 Trailer Cinematográfico
**Descrição**: Gera texto para um trailer de filme baseado no livro.

**Elementos incluídos**:
- Descrições visuais cinematográficas
- Frases impactantes
- Sugestões de música
- Título e tagline

**Localização**: Explorador → "Trailer"

---

#### 🎨 Prompt para Capa
**Descrição**: Gera descrições otimizadas para criar capas com IA de imagem.

**Inclui**:
- Prompt principal (em inglês, otimizado para DALL-E/Midjourney)
- Estilo visual sugerido
- Cores dominantes
- Variações alternativas

**Localização**: Explorador → "Prompt Capa"

---

#### 🎭 Casting de Filme
**Descrição**: Sugere atores para uma adaptação cinematográfica.

**Inclui**:
- Ator principal e alternativa para cada personagem
- Justificação para cada escolha
- Sugestão de realizador
- Sugestão de compositor para banda sonora

**Localização**: Explorador → "Casting"

---

### 4.5 💬 Chat com Livros

**Descrição**: Conversa sobre qualquer aspeto do livro com a IA.

**Casos de uso**:
- Tirar dúvidas sobre a história
- Discutir interpretações
- Pedir análises específicas
- Explorar contexto histórico

**Localização**: Página do livro → "Chat" ou Explorador → secção de chat

---

## 5. Como Usar

### 5.1 Criar um Livro

1. Aceder à aplicação
2. Clicar em "Criar Livro"
3. Preencher:
   - **Tema/Título**: Sobre o que será o livro
   - **Estilo**: Género literário
   - **Capítulos**: Número de capítulos (1-20)
   - **Páginas**: Extensão aproximada
   - **Idioma**: Português ou outro
4. Clicar "Gerar Livro"
5. Aguardar a geração (pode demorar 1-3 minutos)
6. O livro aparece na biblioteca

### 5.2 Explorar um Livro Existente

1. Ir a "Explorador" no menu
2. Escrever o título do livro (ex: "1984")
3. Escrever o autor (ex: "George Orwell")
4. Clicar "Explorar Livro"
5. Escolher os aspetos a analisar
6. Usar as funcionalidades interativas

### 5.3 Exportar Livros

1. Ir à biblioteca
2. Clicar no livro desejado
3. Escolher "Exportar PDF" ou "Exportar EPUB"
4. O ficheiro é descarregado automaticamente

---

## 6. API e Endpoints

### Páginas (GET)

| Rota | Descrição |
|------|-----------|
| `/` | Página inicial |
| `/create` | Criar novo livro |
| `/books` | Lista de livros |
| `/book/<id>` | Ver livro específico |
| `/read/<id>` | Ler livro |
| `/explorer` | Explorador de livros |
| `/interview/<id>` | Entrevista com personagem |
| `/quiz/<id>` | Quiz do livro |
| `/chat/<id>` | Chat sobre livro |

### API (POST)

| Endpoint | Descrição | Parâmetros |
|----------|-----------|------------|
| `/api/generate-book` | Gerar livro | theme, style, chapters, pages, language |
| `/api/explore-book` | Explorar livro | title, author, aspect, question |
| `/api/book/<id>/chat` | Chat com livro | message, history |
| `/api/book/<id>/interview` | Entrevista personagem | character, message, history |
| `/api/book/<id>/quiz` | Gerar quiz | difficulty |
| `/api/book/<id>/continue` | Continuar história | continuation_type, direction |

### Parâmetros do Explorador (aspect)

| Valor | Funcionalidade |
|-------|----------------|
| `info` | Informações básicas |
| `summary` | Resumo completo |
| `characters` | Personagens |
| `themes` | Temas e mensagens |
| `world` | Mundo e cenário |
| `style` | Estilo literário |
| `quotes` | Citações famosas |
| `discussion` | Questões de discussão |
| `similar` | Livros similares |
| `trivia` | Curiosidades |
| `timeline` | Cronologia |
| `symbolism` | Simbolismo |
| `adaptation` | Adaptações |
| `chat` | Chat geral |
| `interview` | Entrevista personagem |
| `quiz` | Quiz |
| `continue` | Continuar história |
| `alternate` | Final alternativo |
| `playlist` | Playlist sugerida |
| `trailer` | Trailer cinematográfico |
| `cover` | Prompt para capa |
| `casting` | Casting de filme |

---

## 7. Base de Dados

### Modelo: Book

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | Integer | Identificador único (PK) |
| title | String(200) | Título do livro |
| author | String(100) | Autor (default: "IA") |
| genre | String(50) | Género literário |
| synopsis | Text | Sinopse |
| full_text | Text | Texto completo do livro |
| chapters | Text | JSON com lista de capítulos |
| created_at | DateTime | Data de criação |
| updated_at | DateTime | Data de atualização |
| cover_image | Text | URL ou base64 da capa |
| series_id | Integer | FK para série (opcional) |

### Modelo: Series

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | Integer | Identificador único (PK) |
| name | String(200) | Nome da série |
| description | Text | Descrição |
| created_at | DateTime | Data de criação |

---

## 8. Deployment

### Plataforma: Render.com

**URL da Aplicação**: `https://bookscreatorai1.onrender.com`

### Configuração

**Build Command**:
```bash
pip install --upgrade pip && pip install -r requirements.txt
```

**Start Command**:
```bash
gunicorn app:app --bind=0.0.0.0:$PORT
```

### Variáveis de Ambiente

| Variável | Descrição |
|----------|-----------|
| `GOOGLE_API_KEY` | Chave da API Google Gemini |

### Plano Gratuito - Limitações

- Instância "adormece" após 15 minutos de inatividade
- Primeira visita pode demorar 30-50 segundos
- Recursos limitados de CPU e memória

### Atualizar a Aplicação

1. Fazer alterações no código local
2. Abrir GitHub Desktop
3. Commit das alterações
4. Push para GitHub
5. Render faz deploy automático

---

## Anexo: Fluxo de Funcionamento

```
┌─────────────────────────────────────────────────────────────┐
│                        UTILIZADOR                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND (Browser)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   HTML5     │  │   CSS       │  │    JavaScript       │  │
│  │  (Jinja2)   │  │ (Tailwind)  │  │  (Fetch API calls)  │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     BACKEND (Flask)                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Routes    │  │   Models    │  │    API Endpoints    │  │
│  │  (app.py)   │  │  (SQLAlch.) │  │   (/api/...)        │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────────┐
│      SQLite Database    │     │     Google Gemini API       │
│   ┌─────────────────┐   │     │   ┌─────────────────────┐   │
│   │  books.db       │   │     │   │  gemini-2.0-flash   │   │
│   │  - Books        │   │     │   │  - Text Generation  │   │
│   │  - Series       │   │     │   │  - Analysis         │   │
│   └─────────────────┘   │     │   └─────────────────────┘   │
└─────────────────────────┘     └─────────────────────────────┘
```

---

## Créditos

- **Desenvolvido por**: [Seu Nome]
- **Data**: Novembro 2025
- **Tecnologia IA**: Google Gemini
- **Hospedagem**: Render.com

---

*Documento gerado automaticamente para o projeto BookCreatorAI*
