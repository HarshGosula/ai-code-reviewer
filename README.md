# 🤖 AI Code Review Bot

An intelligent GitHub App that performs automated AI-driven code reviews and repository-wide audits using multi-agent reasoning and RAG (Retrieval-Augmented Generation).

## ✨ Features

### 🔍 Automated PR Reviews
- **Triggered automatically** on PR creation or updates
- **Multi-agent analysis** covering:
  - 🔒 **Security**: SQL injection, XSS, auth issues, secrets detection
  - ⚡ **Performance**: Algorithm efficiency, N+1 queries, memory leaks
  - 🎨 **Style**: Code quality, naming, documentation, maintainability
  - 🏗️ **Architecture**: SOLID principles, design patterns, coupling
- **Contextual understanding** using RAG to learn repository patterns
- **Inline comments** on specific code lines with actionable suggestions

### 📊 Repository-Wide Audits
- **Triggered by `/audit` command** in GitHub issues
- **Complete codebase analysis** (not just diffs)
- **Knowledge base indexing** for future context
- **Comprehensive reports** with categorized findings

### 🧠 RAG-Powered Context
- **Repository-specific embeddings** stored in Pinecone
- **Learns from**:
  - Code patterns and conventions
  - Documentation (README, CONTRIBUTING, etc.)
  - Custom review rules (REVIEW_RULES.md)
- **Automatic updates** when code changes

### 🔐 Multi-Tenant & Secure
- **Per-installation isolation** using GitHub App tokens
- **Namespace separation** in vector database
- **Webhook signature verification**

## 🏗️ Architecture

```
┌─────────────────┐
│  GitHub Webhook │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   FastAPI App   │
│  (Webhook API)  │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌─────┐   ┌──────┐
│ PR  │   │Audit │
│Review   │Handler
└──┬──┘   └───┬──┘
   │          │
   └────┬─────┘
        │
        ▼
┌────────────────────┐
│  Multi-Agent       │
│  Orchestrator      │
│  (LangGraph)       │
└─────────┬──────────┘
          │
    ┌─────┴─────┬─────────┬──────────┐
    ▼           ▼         ▼          ▼
┌────────┐ ┌─────────┐ ┌──────┐ ┌──────────┐
│Security│ │Performance Style│ │Architecture
│ Agent  │ │  Agent  │ │Agent │ │  Agent   │
└────┬───┘ └────┬────┘ └───┬──┘ └────┬─────┘
     │          │           │         │
     └──────────┴───────────┴─────────┘
                │
                ▼
         ┌─────────────┐
         │   Gemini    │
         │  (LLM API)  │
         └─────────────┘
                │
                ▼
         ┌─────────────┐
         │  Pinecone   │
         │ (Vector DB) │
         └─────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- GitHub App created with:
  - Webhook URL configured
  - Private key downloaded
  - Permissions: Pull requests (read/write), Issues (read/write), Contents (read)
  - Events: Pull request, Issue comment
- Gemini API key
- Pinecone account

### Installation

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd AI-code-reviewer
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment**
```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```env
GITHUB_APP_ID=your_app_id
GITHUB_PRIVATE_KEY_PATH=private-key.pem
GITHUB_WEBHOOK_SECRET=your_webhook_secret
GEMINI_API_KEY=your_gemini_api_key
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=your_pinecone_environment
```

4. **Place your GitHub App private key**
```bash
# Save your private key as private-key.pem in the project root
```

5. **Run the application**
```bash
python -m app.main
```

Or with Docker:
```bash
docker-compose up --build
```

The app will be available at `http://localhost:8000`

### Expose Webhook (Development)

Use ngrok or similar to expose your local server:
```bash
ngrok http 8000
```

Update your GitHub App webhook URL to the ngrok URL + `/webhooks/github`

## 📖 Usage

### PR Reviews

1. Install the GitHub App on your repository
2. Create or update a pull request
3. The bot will automatically:
   - Analyze changed files
   - Post inline comments on issues
   - Provide a summary comment

### Repository Audits

1. Create an issue in your repository
2. Comment `/audit` in the issue
3. The bot will:
   - Index your entire codebase
   - Analyze all files
   - Post a comprehensive audit report

### Custom Review Rules

Create a `REVIEW_RULES.md` file in your repository root:

```markdown
# Code Review Rules

## Naming Conventions
- Use camelCase for JavaScript variables
- Use snake_case for Python variables

## Security
- Never commit API keys
- Always validate user input

## Performance
- Prefer async/await over callbacks
- Use database indexes for frequently queried fields
```

The bot will learn these rules and apply them in reviews!

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GITHUB_APP_ID` | Your GitHub App ID | Yes |
| `GITHUB_PRIVATE_KEY_PATH` | Path to private key file | Yes |
| `GITHUB_WEBHOOK_SECRET` | Webhook secret for verification | Yes |
| `GEMINI_API_KEY` | Google Gemini API key | Yes |
| `PINECONE_API_KEY` | Pinecone API key | Yes |
| `PINECONE_ENVIRONMENT` | Pinecone environment (e.g., us-east-1) | Yes |
| `PINECONE_INDEX_NAME` | Pinecone index name | No (default: github-code-review) |
| `APP_ENV` | Environment (development/production) | No (default: development) |
| `LOG_LEVEL` | Logging level | No (default: INFO) |
| `MAX_CONCURRENT_REVIEWS` | Max concurrent reviews | No (default: 5) |

## 🚢 Deployment

### Docker

```bash
docker build -t ai-code-review-bot .
docker run -p 8000:8000 --env-file .env ai-code-review-bot
```

### Railway

1. Create a new project on Railway
2. Connect your GitHub repository
3. Add environment variables
4. Deploy!

### Render

1. Create a new Web Service
2. Connect your repository
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables
6. Deploy!

## 🧪 Testing

Run tests:
```bash
pytest
```

Test webhook endpoint:
```bash
curl http://localhost:8000/webhooks/test
```

Health check:
```bash
curl http://localhost:8000/health
```

## 📊 Monitoring

The application logs all activities. In production, integrate with:
- **Sentry** for error tracking
- **DataDog** or **New Relic** for APM
- **CloudWatch** or **Stackdriver** for logs

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Powered by [Google Gemini](https://ai.google.dev/)
- Vector storage by [Pinecone](https://www.pinecone.io/)
- Multi-agent orchestration with [LangGraph](https://github.com/langchain-ai/langgraph)

## 📞 Support

For issues and questions:
- Open a GitHub issue
- Check the documentation
- Review logs for debugging

---

**Made with ❤️ for better code reviews**

