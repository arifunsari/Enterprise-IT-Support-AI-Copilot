import tempfile
import unittest
import zipfile
from pathlib import Path

from docx import Document as DocxDocument
from pypdf import PdfWriter

from app.services.ingestion import SUPPORTED, chunk_documents, load_file, validate_file_content


class IngestionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_supported_formats_load_and_chunk(self):
        txt = self.root / "notes.txt"
        txt.write_text("VPN setup instructions for employees.", encoding="utf-8")
        md = self.root / "notes.md"
        md.write_text("# Help\nRestart the managed device.", encoding="utf-8")
        docx_path = self.root / "notes.docx"
        doc = DocxDocument()
        doc.add_paragraph("Contact the help desk for account support.")
        doc.save(docx_path)
        pdf_path = self.root / "notes.pdf"
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        with pdf_path.open("wb") as stream:
            writer.write(stream)

        for path in (txt, md, docx_path, pdf_path):
            with self.subTest(extension=path.suffix):
                docs = load_file(path)
                self.assertIsInstance(docs, list)
                self.assertTrue(all(hasattr(item, "page_content") for item in docs))
                self.assertIsInstance(chunk_documents(docs), list)
        self.assertEqual(SUPPORTED, {".pdf", ".txt", ".md", ".docx"})

    def test_rejects_unsupported_empty_and_invalid_content(self):
        unsupported = self.root / "notes.exe"
        unsupported.write_bytes(b"no")
        empty = self.root / "empty.txt"
        empty.write_bytes(b"")
        invalid_pdf = self.root / "broken.pdf"
        invalid_pdf.write_text("not a PDF", encoding="utf-8")
        invalid_docx = self.root / "broken.docx"
        invalid_docx.write_bytes(b"not a zip archive")

        for path in (unsupported, empty, invalid_pdf, invalid_docx):
            with self.subTest(path=path.name), self.assertRaises(ValueError):
                load_file(path)

    def test_rejects_docx_zip_without_document_xml(self):
        path = self.root / "missing-document.docx"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("other.xml", "<root />")
        with self.assertRaisesRegex(ValueError, "valid DOCX"):
            validate_file_content(path)


if __name__ == "__main__":
    unittest.main()
