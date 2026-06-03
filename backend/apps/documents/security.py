"""PDF security validation and sanitization.

Inspects uploaded PDFs for known dangerous constructs (JavaScript, launch
actions, embedded files, auto-actions, XFA forms) before they reach the
ingestion pipeline. Returns sanitized bytes with dangerous objects stripped,
or raises PDFSecurityError if the file cannot be safely processed.
"""

import io
import logging

import pikepdf

logger = logging.getLogger(__name__)

MAX_PDF_BYTES = 50 * 1024 * 1024  # 50 MB hard cap
PDF_MAGIC = b"%PDF-"

DANGEROUS_KEYS = {
    "/JavaScript",
    "/JS",
    "/Launch",
    "/EmbeddedFile",
    "/EmbeddedFiles",
    "/RichMedia",
    "/Movie",
    "/Sound",
    "/GoToR",
    "/GoToE",
    "/SubmitForm",
    "/ImportData",
}

DANGEROUS_ACTION_TYPES = {
    "/Launch",
    "/JavaScript",
    "/GoToR",
    "/GoToE",
    "/SubmitForm",
    "/ImportData",
    "/Movie",
    "/Sound",
    "/RichMediaExecute",
}

# Map technical PDF threat identifiers to readable categories shown to users.
THREAT_LABELS = {
    "/JavaScript": "embedded scripts",
    "/JS": "embedded scripts",
    "/Launch": "auto-launch actions",
    "/EmbeddedFile": "embedded files",
    "/EmbeddedFiles": "embedded files",
    "/RichMedia": "embedded media",
    "/RichMediaExecute": "embedded media",
    "/Movie": "embedded media",
    "/Sound": "embedded media",
    "/GoToR": "external links to other files",
    "/GoToE": "external links to other files",
    "/SubmitForm": "form-submission actions",
    "/ImportData": "external data imports",
    "/XFA": "interactive forms (XFA)",
}


def _friendly_threat_message(threats: set) -> str:
    """Convert raw threat keys into a single user-facing sentence."""
    categories = sorted({THREAT_LABELS.get(t, "unsafe content") for t in threats})
    if len(categories) == 1:
        return f"This PDF contains {categories[0]} and cannot be uploaded for security reasons."
    last = categories[-1]
    head = ", ".join(categories[:-1])
    return f"This PDF contains {head}, and {last}, and cannot be uploaded for security reasons."


class PDFSecurityError(Exception):
    """Raised when a PDF fails security validation."""


def _walk_object(obj, found: set, depth: int = 0, max_depth: int = 50):
    """Recursively scan a pikepdf object graph for dangerous keys."""
    if depth > max_depth:
        return
    try:
        if isinstance(obj, pikepdf.Dictionary):
            keys = list(obj.keys())
            for key in keys:
                key_str = str(key)
                if key_str in DANGEROUS_KEYS:
                    found.add(key_str)
            if "/S" in keys:
                try:
                    action_type = str(obj["/S"])
                    if action_type in DANGEROUS_ACTION_TYPES:
                        found.add(action_type)
                except Exception:
                    pass
            for key in keys:
                try:
                    _walk_object(obj[key], found, depth + 1, max_depth)
                except Exception:
                    continue
        elif isinstance(obj, pikepdf.Array):
            for item in obj:
                _walk_object(item, found, depth + 1, max_depth)
    except Exception:
        return


def validate_and_sanitize_pdf(data: bytes) -> bytes:
    """Validate a PDF and return sanitized bytes.

    Raises PDFSecurityError if the file is malformed, oversized, or contains
    threats that cannot be safely stripped.
    """
    if not data:
        raise PDFSecurityError("This file appears to be empty. Please upload a valid PDF.")

    if len(data) > MAX_PDF_BYTES:
        raise PDFSecurityError(
            f"This file is too large. Maximum allowed size is {MAX_PDF_BYTES // (1024 * 1024)} MB."
        )

    if not data.startswith(PDF_MAGIC):
        raise PDFSecurityError(
            "This file doesn't look like a valid PDF. Please upload a real PDF document."
        )

    try:
        pdf = pikepdf.open(io.BytesIO(data))
    except pikepdf.PasswordError:
        raise PDFSecurityError("This PDF is password-protected. Please upload an unlocked copy.")
    except pikepdf.PdfError as exc:
        logger.warning("PDF parse error: %s", exc)
        raise PDFSecurityError(
            "This PDF appears to be damaged or unreadable. Please re-save it and try again."
        )

    try:
        threats: set = set()

        root = pdf.Root
        _walk_object(root, threats)

        if "/AcroForm" in root.keys():
            acroform = root["/AcroForm"]
            if isinstance(acroform, pikepdf.Dictionary) and "/XFA" in acroform.keys():
                threats.add("/XFA")

        for obj in pdf.objects:
            _walk_object(obj, threats)

        if threats:
            logger.warning("PDF rejected. Dangerous constructs: %s", sorted(threats))
            raise PDFSecurityError(_friendly_threat_message(threats))

        if "/OpenAction" in root.keys():
            del root["/OpenAction"]
        if "/AA" in root.keys():
            del root["/AA"]
        if "/Names" in root.keys():
            names = root["/Names"]
            if isinstance(names, pikepdf.Dictionary):
                for key in ("/JavaScript", "/EmbeddedFiles"):
                    if key in names.keys():
                        del names[key]

        out = io.BytesIO()
        pdf.save(out, linearize=False, fix_metadata_version=True)
        return out.getvalue()
    finally:
        pdf.close()
