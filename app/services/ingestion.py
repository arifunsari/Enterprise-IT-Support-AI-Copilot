from pathlib import Path
from typing import Iterable
import zipfile
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from docx import Document as DocxDocument


SUPPORTED = {".pdf", ".txt", ".md", ".docx"}


def validate_file_content(path: Path) -> None:
    """Reject files whose bytes do not match their supported document format."""
    suffix = path.suffix.lower()
    if path.stat().st_size == 0:
        raise ValueError("The uploaded file is empty")
    with path.open("rb") as stream:
        header = stream.read(8)
    if suffix == ".pdf":
        if not header.startswith(b"%PDF-"):
            raise ValueError("The uploaded file is not a valid PDF")
    elif suffix == ".docx":
        if not zipfile.is_zipfile(path):
            raise ValueError("The uploaded file is not a valid DOCX document")
        with zipfile.ZipFile(path) as archive:
            if "word/document.xml" not in archive.namelist():
                raise ValueError("The uploaded file is not a valid DOCX document")
    elif suffix in {".txt", ".md"}:
        try:
            path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("Text documents must be UTF-8 encoded") from exc



def load_file(path: Path) -> list[Document]:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED:
        raise ValueError(f"Unsupported file type: {suffix}")
    validate_file_content(path)
    if suffix == ".pdf":
        return PyPDFLoader(str(path)).load()
    if suffix in {".txt", ".md"}:
        return TextLoader(str(path), encoding="utf-8").load()
    if suffix == ".docx":
        doc = DocxDocument(str(path))
        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        return [Document(page_content=text, metadata={"source": str(path)})]
    raise ValueError(f"Unsupported file type: {suffix}")



def chunk_documents(docs: Iterable[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=120, add_start_index=True)
    return splitter.split_documents(list(docs))
