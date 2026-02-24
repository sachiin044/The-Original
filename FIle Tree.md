# File Tree: Supabase changes error

**Generated:** 2/22/2026, 10:39:05 AM
**Root Path:** `c:\Projects\Supabase changes error`

```
└── explaingithub-api-access # Root directory for project source
    ├── .devcontainer # Environment configuration for development containers
    │   └── devcontainer.json # Configuration for Visual Studio Code containers
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
    │   │   ├── api_keys.py # Endpoints for managing project keys
    │   │   ├── chat.py # Endpoints for AI chat interaction
    │   │   ├── credentials.py # Endpoints for managing user credentials
    │   │   ├── health.py # Simple API availability check endpoint
    │   │   └── repos.py # Endpoints for repository metadata management
    │   ├── schemas # Data validation and response models
    │   │   ├── __init__.py # Module initialization for schemas package
    │   │   └── models.py # Pydantic models for API data
    │   ├── services # Business logic and external integrations
    │   │   ├── __init__.py # Module initialization for services package
    │   │   ├── chat_store.py # Persistence logic for chat history
    │   │   ├── embed.py # Text to vector embedding conversion
    │   │   ├── followups.py # Generation of related followup questions
    │   │   ├── ingest.py # Data loading into vector database
    │   │   ├── issues_chat.py # Logic for chatting about issues
    │   │   ├── memory.py # Conversation state and history management
    │   │   ├── pr_chat.py # Logic for chatting about PRs
    │   │   ├── question_router.py # Intelligence to route user queries
    │   │   ├── rag.py # Retrieval augmented generation pipeline logic
    │   │   ├── repo_index.py # Indexing service for repository files
    │   │   └── supabase_vectorstore.py # Integration with Supabase vector storage
    │   ├── utils # General helpers and utility functions
    │   │   ├── __init__.py # Module initialization for utils package
    │   │   ├── crypto.py # Encryption and hash utility functions
    │   │   ├── github.py # Client for GitHub API interactions
    │   │   └── repo_id.py # Logic for parsing repository identifiers
    │   ├── __init__.py # Main application module initialization
    │   └── main.py # FastAPI application entry point file
    ├── tests # Automated test suites for project
    │   ├── __init__.py # Module initialization for tests package
    │   ├── test.py # General unit tests for application
    │   ├── test_supabase.py # Integration tests for Supabase operations
    │   └── verify_repo_chat.py # Script to verify chat functionality
    ├── .dockerignore # Files excluded from Docker image
    ├── .gitignore # Files ignored by Git versioning
    ├── Dockerfile # Instructions for building Docker image
    ├── FIle Tree.md # Current file structure and descriptions
    ├── Features.txt # Text file listing project features
    ├── check_langchain.py # Utility to verify LangChain installation
    ├── debug_imports.py # Script to troubleshoot import errors
    ├── generate_key.py # Script for creating new keys
    ├── integration_test.py # Full system end-to-end tests
    ├── reproduce_issue.py # Script to replicate reported bugs
    ├── requirements.txt # List of project Python dependencies
    └── streamlit_app.py # UI frontend using Streamlit framework
```