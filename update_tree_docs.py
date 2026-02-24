import os
import re

filepath = r"c:\Projects\Supabase changes error\explaingithub-api-access\FIle Tree.md"

def get_desc(name):
    name_lower = name.lower()
    
    # Specific Exact Matches
    exact_matches = {
        "main.py": "Application entry point",
        "rag.py": "RAG logic and LLM pipeline",
        "__init__.py": "Python package initialization",
        "dockerfile": "Docker image build instructions",
        "requirements.txt": "Python package dependencies",
        ".env": "Environment configuration",
        "mkdocs.env.yml": "Environment configuration",
        "mkdocs.yml": "MkDocs configuration",
        "devcontainer.json": "VS Code dev container setup",
        ".gitignore": "Git ignore rules",
        ".dockerignore": "Docker ignore rules",
        "config.py": "Application configuration",
        "db.py": "Database connection setup",
        "exceptions.py": "Custom exception classes",
        "request_logger.py": "Request logging middleware",
        "api_keys.py": "API key routing/auth",
        "api_key_service.py": "API key management",
        "models.py": "Database/Pydantic models",
        "chat_store.py": "Chat history storage",
        "embed.py": "Text embedding logic",
        "issues_chat.py": "GitHub issues chat logic",
        "pr_chat.py": "GitHub PRs chat logic",
        "repo_index.py": "Repository indexing",
        "supabase_vectorstore.py": "Supabase vector database integration",
        "crypto.py": "Cryptographic utilities",
        "github.py": "GitHub API utilities",
        "repo_id.py": "Repository ID parsing",
        "app": "Main backend application",
        "auth": "Authentication module",
        "core": "Core config and database",
        "middleware": "FastAPI middleware",
        "routers": "API endpoints",
        "schemas": "Data validation schemas",
        "services": "Business logic and AI services",
        "utils": "Helper utilities",
        "docs": "Project documentation",
        "repos": "Stored code repositories",
        "fastapi": "FastAPI source code",
        ".github": "GitHub Actions and templates",
        "tests": "Integration and unit tests",
        "scripts": "Utility scripts",
        "adapters": "LLM Model adapters",
        "explaingithub-api-access": "Root directory for the RepoLens backend"
    }

    if name_lower in exact_matches:
        return exact_matches[name_lower]
        
    if name_lower.endswith(".py"): return "Python source file"
    if name_lower.endswith(".md") or name_lower.endswith(".mdx"): return "Markdown documentation"
    if name_lower.endswith(".yml") or name_lower.endswith(".yaml"): return "YAML configuration"
    if name_lower.endswith(".json"): return "JSON data"
    if name_lower.endswith(".png") or name_lower.endswith(".jpg") or name_lower.endswith(".jpeg") or name_lower.endswith(".webp"): return "Image asset"
    if name_lower.endswith(".svg"): return "Vector graphic asset"
    if name_lower.endswith(".css"): return "Stylesheet"
    if name_lower.endswith(".js"): return "JavaScript logic"
    if name_lower.endswith(".html"): return "HTML template"
    if name_lower.endswith(".txt"): return "Text document"
    if name_lower == "license": return "License text"
    
    # Generic
    if "." not in name:
        return "Directory"
    return "File"

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()
    
out_lines = []
tree_pattern = re.compile(r'^([ \t│├└─]*)(.+)$')

in_code_block = False

for line in lines:
    stripped = line.rstrip('\n')
    
    if stripped.startswith('```'):
        in_code_block = not in_code_block
        out_lines.append(line)
        continue
        
    if in_code_block:
        match = tree_pattern.match(stripped)
        if match:
            prefix = match.group(1)
            name = match.group(2).strip()
            if name:
                if " - " not in name:
                    desc = get_desc(name)
                    out_lines.append(f"{prefix}{name} - {desc}\n")
                else:
                    out_lines.append(line)
            else:
                out_lines.append(line)
        else:
            out_lines.append(line)
    else:
        out_lines.append(line)
        
with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(out_lines)

print("File Tree.md has been successfully updated.")
