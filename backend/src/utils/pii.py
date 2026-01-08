import re


def mask_pii(text: str) -> str:
    """
    Masks PII (Personally Identifiable Information) in the given text.
    Currently supports:
    - Email Addresses
    - Credit Card Numbers (Basic Luhn-like sequence check)
    - SSN (Simple pattern)
    """
    if not text:
        return text

    # 1. IBAN (International Bank Account Number)
    # Starts with 2 letters, then 2 digits, then up to 30 alphanumeric characters
    # Support spaces grouping (common 4-char groups)
    iban_pattern = r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){2,}(?:\s?[A-Z0-9]{1,4})?\b"
    text = re.sub(iban_pattern, "[IBAN_REDACTED]", text)

    # 2. French SSN (Numéro de Sécurité Sociale)
    # 13 digits, optional spaces (e.g., 1 80 01 75 000 000)
    # Broad pattern: 13-15 digits with spaces
    ssn_fr_pattern = r"\b[12]\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{3}\s?\d{3}(\s?\d{2})?\b"
    text = re.sub(ssn_fr_pattern, "[SSN_FR_REDACTED]", text)

    # 3. Phone Numbers (French)
    # 06 12 34 56 78 or +33 6 12 ...
    phone_fr_pattern = r"(?:(?:\+|00)33|0)\s*[1-9](?:[\s.-]*\d{2}){4}"
    text = re.sub(phone_fr_pattern, "[PHONE_REDACTED]", text)

    # 4. Email Masking
    # Regex for email: something@something.something
    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"
    text = re.sub(email_pattern, "[EMAIL_REDACTED]", text)

    # 5. Credit Card Masking (Simple 13-19 digits usually)
    # This is a broad matcher to catch potential card numbers.
    # We look for sequences of 13-16 digits, possibly separated by spaces or dashes.
    cc_pattern = r"\b(?:\d{4}[-\s]?){3}\d{4}\b|\b\d{13,19}\b"
    text = re.sub(cc_pattern, "[CREDIT_CARD_REDACTED]", text)

    # 6. SSN (Social Security Number) - US Format
    ssn_pattern = r"\b\d{3}-\d{2}-\d{4}\b"
    text = re.sub(ssn_pattern, "[SSN_REDACTED]", text)

    return text
