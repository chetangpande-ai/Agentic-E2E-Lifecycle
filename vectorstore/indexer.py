"""
Code indexer for ingesting repository code into ChromaDB.
Intelligently chunks code by function/class boundaries.
"""

from typing import Dict, List
from pathlib import Path
from langchain_core.documents import Document
from vectorstore.store import add_documents
from utils.logger import logger


class CodeIndexer:
    """Indexes code files from repositories into the vector store for RAG."""

    def index_repository(self, code_files: Dict[str, str]) -> int:
        """
        Index all code files from a repository into ChromaDB.
        
        Args:
            code_files: Dict mapping file paths to file contents.
            
        Returns:
            Number of documents indexed.
        """
        if not code_files:
            logger.warning("No code files to index")
            return 0

        logger.info(f"Indexing {len(code_files)} code files into vector store...")
        documents = []

        for file_path, content in code_files.items():
            chunks = self._chunk_code(file_path, content)
            documents.extend(chunks)

        if documents:
            add_documents(documents, collection_name="code_patterns")
            logger.info(f"Indexed {len(documents)} code chunks")

        return len(documents)

    def index_test_templates(self, templates: Dict[str, str]) -> int:
        """Index test template patterns for reuse."""
        documents = []
        for name, content in templates.items():
            doc = Document(
                page_content=content,
                metadata={
                    "source": name,
                    "type": "template",
                },
            )
            documents.append(doc)

        if documents:
            add_documents(documents, collection_name="test_templates")

        return len(documents)

    def _chunk_code(self, file_path: str, content: str) -> List[Document]:
        """
        Split code into meaningful chunks (by function/class or fixed size).
        """
        ext = Path(file_path).suffix.lower()
        chunks = []

        # For feature files, keep whole file as one chunk
        if ext == '.feature':
            chunks.append(
                Document(
                    page_content=content,
                    metadata={
                        "file_path": file_path,
                        "file_type": "feature",
                        "language": "gherkin",
                    },
                )
            )
            return chunks

        # For code files, split by logical blocks
        lines = content.split('\n')
        current_chunk = []
        chunk_start = 0

        for i, line in enumerate(lines):
            current_chunk.append(line)

            # Split at function/class boundaries or every 50 lines
            is_boundary = (
                line.strip().startswith('export ') or
                line.strip().startswith('class ') or
                line.strip().startswith('function ') or
                line.strip().startswith('def ') or
                line.strip().startswith('async ') or
                (len(current_chunk) >= 50 and line.strip() == '')
            )

            if is_boundary and len(current_chunk) > 5:
                chunk_content = '\n'.join(current_chunk)
                chunks.append(
                    Document(
                        page_content=chunk_content,
                        metadata={
                            "file_path": file_path,
                            "file_type": ext.lstrip('.'),
                            "language": self._get_language(ext),
                            "start_line": chunk_start,
                            "end_line": i,
                        },
                    )
                )
                current_chunk = []
                chunk_start = i + 1

        # Add remaining lines
        if current_chunk:
            chunk_content = '\n'.join(current_chunk)
            if chunk_content.strip():
                chunks.append(
                    Document(
                        page_content=chunk_content,
                        metadata={
                            "file_path": file_path,
                            "file_type": ext.lstrip('.'),
                            "language": self._get_language(ext),
                            "start_line": chunk_start,
                            "end_line": len(lines),
                        },
                    )
                )

        return chunks

    def _get_language(self, ext: str) -> str:
        """Map file extension to language name."""
        mapping = {
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.py': 'python',
            '.java': 'java',
            '.json': 'json',
            '.feature': 'gherkin',
        }
        return mapping.get(ext, 'unknown')
