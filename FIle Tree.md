# File Tree

**Generated:** 2/25/2026, 1:14:25 PM
**Root Path:** `c:\Projects\explaingithub-api-access`

```
└── explaingithub-api-access # Root directory for project source
    ├── .devcontainer # Environment configuration for development containers
    │   └── devcontainer.json # Configuration for Visual Studio Code containers
    ├── adapters # External AI service adapter configurations
    │   ├── CLAUDE.md # Specific guidelines for Claude models
    │   ├── GEMINI.md # Specific guidelines for Gemini models
    │   └── GPT_OSS.md # Guidelines for GPT/Open Source models
    ├── app # Core application logic and modules
    │   ├── auth # Security and authentication related components
    │   │   ├── api_key.py # Logic for validating API keys
    │   │   ├── api_key_service.py # Database operations for managing keys
    │   │   ├── dependency.py # FastAPI dependencies for auth checks
    │   │   ├── logger.py # Logging utilities for auth events
    │   │   └── rate_limit.py # Logic to restrict request frequency
    │   ├── core # Global settings and base configuration
    │   │   ├── __init__.py # Module initialization for core package
    │   │   ├── config.py # Application settings from environment variables
    │   │   ├── db.py # Database connection and session setup
    │   │   └── exceptions.py # Custom application error and handlers
    │   ├── middleware # Request processing layers for FastAPI
    │   │   ├── __init__.py # Module initialization for middleware package
    │   │   └── request_logger.py # Middleware for logging HTTP requests
    │   ├── routers # API endpoint definitions and routing
    │   │   ├── __init__.py # Module initialization for routers package
    │   │   ├── agent.py # Endpoints for autonomous agent operations
    │   │   ├── api_keys.py # Endpoints for managing project keys
    │   │   ├── chat.py # Endpoints for AI chat interaction
    │   │   ├── credentials.py # Endpoints for managing user credentials
    │   │   ├── health.py # Simple API availability check endpoint
    │   │   ├── repos.py # Endpoints for repository metadata management
    │   │   └── workflows.py # Endpoints for workflow execution management
    │   ├── schemas # Data validation and response models
    │   │   ├── __init__.py # Module initialization for schemas package
    │   │   └── models.py # Pydantic models for API data
    │   ├── services # Business logic and external integrations
    │   │   ├── __init__.py # Module initialization for services package
    │   │   ├── agent.py # Core reasoning and orchestration for the AI agent
    │   │   ├── agent_tools # Collections of tools available to the agent
    │   │   │   ├── __init__.py # Module initialization for agent tools package
    │   │   │   ├── base.py # Base classes for custom agent tools
    │   │   │   ├── get_deployment_info_tool.py # Tool fetching deployment logic
    │   │   │   ├── get_failed_workflows_tool.py # Tool for analyzing failed workflows
    │   │   │   ├── get_issue_details_tool.py # Tool retrieving issue comments and details
    │   │   │   └── get_last_pr_tool.py # Tool pulling merged pull requests from repo
    │   │   ├── chat_store.py # Persistence logic for chat history
    │   │   ├── embed.py # Text to vector embedding conversion
    │   │   ├── followups.py # Generation of related followup questions
    │   │   ├── ingest.py # Data loading into vector database
    │   │   ├── issues_chat.py # Logic for chatting about issues
    │   │   ├── memory.py # Conversation state and history management
    │   │   ├── pinecone_client.py # Client for Pinecone vector database
    │   │   ├── pr_chat.py # Logic for chatting about PRs
    │   │   ├── question_router.py # Intelligence to route user queries
    │   │   ├── rag.py # Retrieval augmented generation pipeline logic
    │   │   ├── repo_index.py # Indexing service for repository files
    │   │   ├── supabase_vectorstore.py # Integration with Supabase vector storage
    │   │   └── workflows_chat.py # Logic for chatting about workflows
    │   ├── utils # General helpers and utility functions
    │   │   ├── __init__.py # Module initialization for utils package
    │   │   ├── crypto.py # Encryption and hash utility functions
    │   │   ├── github.py # Client for GitHub API interactions
    │   │   ├── github_actions_client.py # Client for GitHub Actions API
    │   │   └── repo_id.py # Logic for parsing repository identifiers
    │   ├── __init__.py # Main application module initialization
    │   └── main.py # FastAPI application entry point file
    ├── .dockerignore # Files excluded from Docker image
    ├── .env # Local environment variables (template)
    ├── .gitignore # Files ignored by Git versioning
    ├── Dockerfile # Instructions for building Docker image
    ├── FIle Tree.md # Current file structure and descriptions
    └── requirements.txt # List of project Python dependencies
```