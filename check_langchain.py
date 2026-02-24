try:
    from langchain_core.documents import Document
    print("SUCCESS: Imported Document from langchain_core.documents")
except ImportError as e:
    print(f"FAIL: {e}")

try:
    from langchain.docstore.document import Document
    print("SUCCESS: Imported Document from langchain.docstore.document")
except ImportError as e:
    print(f"FAIL: {e}")
