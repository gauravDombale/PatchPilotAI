from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, cast

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from pydantic import SecretStr

from resolver.config import get_settings

try:
    from langchain_community.vectorstores import Chroma as _ImportedChroma
    CHROMA_CLASS: Any | None = _ImportedChroma
except ImportError:  # pragma: no cover - exercised in slim runtime image
    CHROMA_CLASS = None

EXCLUDE_DIRS = {
    ".git",
    ".venv",
    ".work",
    ".chroma",
    ".pytest_cache",
    ".mypy_cache",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
}


class RepoIndexer:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.chunk_size = 1200
        self.chunk_overlap = 150

    def _split_text(self, text: str) -> list[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]
        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunks.append(text[start:end])
            if end >= len(text):
                break
            start = max(end - self.chunk_overlap, start + 1)
        return chunks

    def _collect_files(self, repo_dir: Path) -> list[Path]:
        files: list[Path] = []
        for p in repo_dir.rglob("*"):
            rel_parts = p.relative_to(repo_dir).parts
            if any(part in EXCLUDE_DIRS for part in rel_parts):
                continue
            if p.is_file() and p.suffix in {".py", ".md", ".ts", ".tsx", ".js", ".json", ".yml"}:
                files.append(p)
        files.sort(key=self._file_priority)
        return files

    def _file_priority(self, path: Path) -> tuple[int, str]:
        rel = str(path)
        if rel.startswith("app/") and path.suffix == ".py":
            return (0, rel)
        if rel.startswith("tests/") and path.suffix == ".py":
            return (1, rel)
        if rel == "README.md":
            return (2, rel)
        return (3, rel)

    def _collection_name(self, repo: str, sha: str) -> str:
        return hashlib.md5(f"{repo}:{sha}".encode(), usedforsecurity=False).hexdigest()

    def index_repo(self, repo: str, sha: str, repo_dir: Path) -> Any:
        if CHROMA_CLASS is None:
            raise RuntimeError("chromadb extra is not installed")
        collection_name = self._collection_name(repo, sha)
        docs: list[Document] = []
        for file in self._collect_files(repo_dir):
            text = file.read_text(encoding="utf-8", errors="ignore")
            for chunk in self._split_text(text):
                docs.append(Document(page_content=chunk, metadata={"path": str(file.relative_to(repo_dir))}))
        embedding = OpenAIEmbeddings(model=self.settings.embed_model, api_key=SecretStr(self.settings.openai_api_key.get_secret_value() if isinstance(self.settings.openai_api_key, SecretStr) else self.settings.openai_api_key))
        return CHROMA_CLASS.from_documents(
            docs,
            embedding=embedding,
            persist_directory=self.settings.chroma_dir,
            collection_name=collection_name,
        )

    def retrieve(self, repo: str, sha: str, query: str, repo_dir: Path, k: int = 8) -> list[Document]:
        if not self.settings.has_openai_key or CHROMA_CLASS is None:
            return self._retrieve_local(query=query, repo_dir=repo_dir, k=k)
        collection_name = self._collection_name(repo, sha)
        embedding = OpenAIEmbeddings(model=self.settings.embed_model, api_key=SecretStr(self.settings.openai_api_key.get_secret_value() if isinstance(self.settings.openai_api_key, SecretStr) else self.settings.openai_api_key))
        store = CHROMA_CLASS(
            collection_name=collection_name,
            persist_directory=self.settings.chroma_dir,
            embedding_function=embedding,
        )
        try:
            docs = cast(list[Document], store.similarity_search(query, k=k))
            if docs:
                return docs
            return self._retrieve_local(query=query, repo_dir=repo_dir, k=k)
        except Exception:
            store = self.index_repo(repo=repo, sha=sha, repo_dir=repo_dir)
            docs = cast(list[Document], store.similarity_search(query, k=k))
            if docs:
                return docs
            return self._retrieve_local(query=query, repo_dir=repo_dir, k=k)

    def _retrieve_local(self, query: str, repo_dir: Path, k: int) -> list[Document]:
        query_terms = {t.lower() for t in query.split() if t.strip()}
        candidates: list[tuple[int, Document]] = []
        fallback_chunks: list[Document] = []
        for file in self._collect_files(repo_dir):
            text = file.read_text(encoding="utf-8", errors="ignore")
            for chunk in self._split_text(text):
                rel = str(file.relative_to(repo_dir))
                if rel.startswith("app/") and rel.endswith(".py"):
                    fallback_chunks.append(Document(page_content=chunk, metadata={"path": rel}))
                elif rel.startswith("tests/"):
                    fallback_chunks.append(Document(page_content=chunk, metadata={"path": rel}))
                lowered = chunk.lower()
                score = sum(1 for term in query_terms if term in lowered)
                if score > 0:
                    candidates.append(
                        (
                            score,
                            Document(
                                page_content=chunk,
                                metadata={"path": rel},
                            ),
                        )
                    )
        candidates.sort(key=lambda x: x[0], reverse=True)
        if candidates:
            return [doc for _, doc in candidates[:k]]
        if fallback_chunks:
            return fallback_chunks[:k]
        return []
