"""Document text extraction service.

Supports:
- PDF: text extraction via pypdf
- DOCX: text extraction via python-docx
- Images (png/jpg/jpeg): rejected with clear error (OCR not implemented in Phase 2)
"""

from __future__ import annotations

import logging
from io import BytesIO

from app.schemas.errors import ErrorCode

logger = logging.getLogger("contractguard.parser")


class ParserError(Exception):
    """Raised when document parsing fails."""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def extract_text(filename: str, content: bytes, file_type: str) -> str:
    """Extract text from a contract file.

    Args:
        filename: Original filename (for logging).
        content: Raw file bytes.
        file_type: File extension (pdf, doc, docx, png, jpg, jpeg).

    Returns:
        Extracted text string.

    Raises:
        ParserError: If extraction fails or file type is unsupported.
    """
    file_type = file_type.lower()

    if file_type == "pdf":
        return _extract_pdf(content, filename)
    elif file_type in ("doc", "docx"):
        return _extract_docx(content, filename)
    elif file_type in ("png", "jpg", "jpeg"):
        raise ParserError(
            ErrorCode.UNSUPPORTED_FILE_TYPE,
            "图片格式暂不支持真实解析，请上传 PDF 或 Word 文件",
        )
    else:
        raise ParserError(
            ErrorCode.UNSUPPORTED_FILE_TYPE,
            f"不支持的文件格式: {file_type}",
        )


def _extract_pdf(content: bytes, filename: str) -> str:
    """Extract text from PDF using pypdf."""
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ParserError(ErrorCode.INTERNAL_ERROR, "PDF 解析库未安装")

    try:
        reader = PdfReader(BytesIO(content))
        pages_text: list[str] = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                pages_text.append(f"--- 第 {i + 1} 页 ---\n{text.strip()}")

        full_text = "\n\n".join(pages_text)
        if not full_text.strip():
            raise ParserError(
                ErrorCode.UNSUPPORTED_FILE_TYPE,
                "PDF 文件无法提取文本，可能是扫描件。请上传文字版 PDF。",
            )

        logger.info("parser.pdf", extra={
            "file_name": filename,
            "pages": len(reader.pages),
            "text_length": len(full_text),
        })
        return full_text

    except ParserError:
        raise
    except Exception as exc:
        logger.error("parser.pdf_error", extra={"file_name": filename, "error_detail": str(exc)})
        raise ParserError(ErrorCode.INTERNAL_ERROR, f"PDF 解析失败: {exc}") from exc


def _extract_docx(content: bytes, filename: str) -> str:
    """Extract text from DOCX using python-docx."""
    try:
        from docx import Document
    except ImportError:
        raise ParserError(ErrorCode.INTERNAL_ERROR, "Word 解析库未安装")

    try:
        doc = Document(BytesIO(content))
        paragraphs: list[str] = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                paragraphs.append(text)

        full_text = "\n".join(paragraphs)
        if not full_text.strip():
            raise ParserError(
                ErrorCode.UNSUPPORTED_FILE_TYPE,
                "Word 文件内容为空",
            )

        logger.info("parser.docx", extra={
            "file_name": filename,
            "paragraphs": len(paragraphs),
            "text_length": len(full_text),
        })
        return full_text

    except ParserError:
        raise
    except Exception as exc:
        logger.error("parser.docx_error", extra={"file_name": filename, "error_detail": str(exc)})
        raise ParserError(ErrorCode.INTERNAL_ERROR, f"Word 解析失败: {exc}") from exc
