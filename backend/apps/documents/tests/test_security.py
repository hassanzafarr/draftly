"""Tests for PDF security validation in apps.documents.security."""

import io

import pikepdf
import pytest

from apps.documents.security import (
    MAX_PDF_BYTES,
    PDFSecurityError,
    validate_and_sanitize_pdf,
)


def _make_pdf(modify=None) -> bytes:
    """Build a minimal in-memory PDF, optionally mutated by `modify(pdf)`."""
    pdf = pikepdf.Pdf.new()
    pdf.add_blank_page(page_size=(612, 792))
    if modify is not None:
        modify(pdf)
    buf = io.BytesIO()
    pdf.save(buf)
    pdf.close()
    return buf.getvalue()


class TestValidPDFs:
    def test_clean_pdf_passes(self):
        data = _make_pdf()
        result = validate_and_sanitize_pdf(data)
        assert result.startswith(b"%PDF-")

    def test_sanitized_output_is_parseable(self):
        data = _make_pdf()
        result = validate_and_sanitize_pdf(data)
        pdf = pikepdf.open(io.BytesIO(result))
        assert len(pdf.pages) == 1
        pdf.close()

    def test_open_action_stripped(self):
        def add_open_action(pdf):
            pdf.Root["/OpenAction"] = pikepdf.Array([pdf.pages[0].obj, pikepdf.Name("/Fit")])

        data = _make_pdf(add_open_action)
        result = validate_and_sanitize_pdf(data)
        pdf = pikepdf.open(io.BytesIO(result))
        assert "/OpenAction" not in pdf.Root.keys()
        pdf.close()


class TestRejection:
    def test_empty_file_rejected(self):
        with pytest.raises(PDFSecurityError, match="empty"):
            validate_and_sanitize_pdf(b"")

    def test_non_pdf_rejected(self):
        with pytest.raises(PDFSecurityError, match="valid PDF"):
            validate_and_sanitize_pdf(b"not a pdf at all")

    def test_oversized_rejected(self):
        oversized = b"%PDF-" + b"\x00" * (MAX_PDF_BYTES + 1)
        with pytest.raises(PDFSecurityError, match="too large"):
            validate_and_sanitize_pdf(oversized)

    def test_corrupt_pdf_rejected(self):
        with pytest.raises(PDFSecurityError, match="damaged or unreadable"):
            validate_and_sanitize_pdf(b"%PDF-1.4\nbroken garbage")

    def test_javascript_rejected(self):
        def add_js(pdf):
            pdf.Root["/Names"] = pikepdf.Dictionary(
                {
                    "/JavaScript": pikepdf.Dictionary(
                        {
                            "/Names": pikepdf.Array(
                                [
                                    pikepdf.String("EvilScript"),
                                    pikepdf.Dictionary(
                                        {
                                            "/S": pikepdf.Name("/JavaScript"),
                                            "/JS": pikepdf.String("app.alert('pwned');"),
                                        }
                                    ),
                                ]
                            ),
                        }
                    ),
                }
            )

        data = _make_pdf(add_js)
        with pytest.raises(PDFSecurityError, match="embedded scripts"):
            validate_and_sanitize_pdf(data)

    def test_launch_action_rejected(self):
        def add_launch(pdf):
            pdf.Root["/OpenAction"] = pikepdf.Dictionary(
                {
                    "/S": pikepdf.Name("/Launch"),
                    "/F": pikepdf.String("calc.exe"),
                }
            )

        data = _make_pdf(add_launch)
        with pytest.raises(PDFSecurityError, match="auto-launch"):
            validate_and_sanitize_pdf(data)
