import sys
import os

sys.path.append(os.getcwd())

print("1. Importing fastapi...")
try:
    from fastapi import APIRouter, Depends, HTTPException, Body
    print("   OK")
except ImportError as e:
    print(f"   FAIL: {e}")

print("2. Importing langchain_text_splitters...")
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    print("   OK")
except ImportError as e:
    print(f"   FAIL: {e}")

print("3. Importing langchain_openai...")
try:
    from langchain_openai import OpenAIEmbeddings
    print("   OK")
except ImportError as e:
    print(f"   FAIL: {e}")

print("4. Importing langchain_community.vectorstores...")
try:
    from langchain_community.vectorstores import FAISS
    print("   OK")
except ImportError as e:
    print(f"   FAIL: {e}")

print("5. Importing langchain.schema...")
try:
    from langchain.schema import Document
    print("   OK")
except ImportError as e:
    print(f"   FAIL: {e}")

print("6. Importing app.services.pr_chat...")
try:
    from app.services.pr_chat import fetch_pr_documents
    print("   OK")
except ImportError as e:
    print(f"   FAIL: {e}")
