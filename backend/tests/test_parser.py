from __future__ import annotations

import pytest
from app.schemas.errors import ErrorCode
from app.services.parser import ParserError, extract_text


def test_extract_text_rejects_image_files():
    with pytest.raises(ParserError) as exc_info:
        extract_text("sample.png", b"fake-image", "png")

    assert exc_info.value.code == ErrorCode.UNSUPPORTED_FILE_TYPE
    assert "暂不支持真实解析" in exc_info.value.message


def test_extract_text_rejects_empty_docx():
    with pytest.raises(ParserError) as exc_info:
        extract_text("empty.docx", b"not-a-real-docx", "docx")

    assert exc_info.value.code == ErrorCode.INTERNAL_ERROR
    assert "Word 解析失败" in exc_info.value.message


def test_extract_text_rejects_scanned_like_pdf():
    with pytest.raises(ParserError) as exc_info:
        extract_text("scan.pdf", b"not-a-real-pdf", "pdf")

    assert exc_info.value.code == ErrorCode.INTERNAL_ERROR
    assert "PDF 解析失败" in exc_info.value.message
