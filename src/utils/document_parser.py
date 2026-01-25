"""Document parser for various file formats."""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List
import aiofiles
from pypdf import PdfReader
from docx import Document
from PIL import Image
import io


class DocumentParser:
    """Parser for various document formats."""

    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".md", ".png", ".jpg", ".jpeg"}

    def __init__(self, upload_dir: str = "./uploads"):
        """Initialize document parser."""
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def parse(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Parse a document and extract content."""
        if not file_path.exists():
            return None

        extension = file_path.suffix.lower()

        if extension == ".pdf":
            return await self._parse_pdf(file_path)
        elif extension in {".docx", ".doc"}:
            return await self._parse_docx(file_path)
        elif extension in {".txt", ".md"}:
            return await self._parse_text(file_path)
        elif extension in {".png", ".jpg", ".jpeg"}:
            return await self._parse_image(file_path)
        else:
            return None

    async def _parse_pdf(self, file_path: Path) -> Dict[str, Any]:
        """Parse PDF document."""
        reader = PdfReader(str(file_path))

        pages = []
        full_text = []

        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            pages.append({
                "page_number": i + 1,
                "text": text,
                "char_count": len(text)
            })
            full_text.append(text)

        return {
            "type": "pdf",
            "filename": file_path.name,
            "page_count": len(reader.pages),
            "pages": pages,
            "full_text": "\n\n".join(full_text),
            "metadata": reader.metadata or {}
        }

    async def _parse_docx(self, file_path: Path) -> Dict[str, Any]:
        """Parse Word document."""
        doc = Document(str(file_path))

        paragraphs = []
        tables = []

        for para in doc.paragraphs:
            if para.text.strip():
                paragraphs.append({
                    "text": para.text,
                    "style": para.style.name if para.style else None
                })

        for table in doc.tables:
            table_data = []
            for row in table.rows:
                row_data = [cell.text for cell in row.cells]
                table_data.append(row_data)
            tables.append(table_data)

        full_text = "\n".join([p["text"] for p in paragraphs])

        return {
            "type": "docx",
            "filename": file_path.name,
            "paragraph_count": len(paragraphs),
            "paragraphs": paragraphs,
            "tables": tables,
            "full_text": full_text
        }

    async def _parse_text(self, file_path: Path) -> Dict[str, Any]:
        """Parse text file."""
        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
            content = await f.read()

        lines = content.split("\n")

        return {
            "type": "text",
            "filename": file_path.name,
            "line_count": len(lines),
            "char_count": len(content),
            "full_text": content
        }

    async def _parse_image(self, file_path: Path) -> Dict[str, Any]:
        """Parse image file (extract metadata)."""
        with Image.open(file_path) as img:
            return {
                "type": "image",
                "filename": file_path.name,
                "format": img.format,
                "size": img.size,
                "mode": img.mode,
                "file_path": str(file_path)
            }

    def get_supported_extensions(self) -> List[str]:
        """Return list of supported file extensions."""
        return list(self.SUPPORTED_EXTENSIONS)

    async def extract_text(self, file_path: Path) -> str:
        """Extract plain text from a document."""
        parsed = await self.parse(file_path)
        if parsed and "full_text" in parsed:
            return parsed["full_text"]
        return ""
