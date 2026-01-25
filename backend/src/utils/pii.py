import re
from typing import List, Optional


class PIIMasker:
    def __init__(self, filters: Optional[List[str]] = None):
        """
        Production-grade PII Masker.
        :param filters: Options: 'email', 'phone', 'cc', 'ssn_us', 'ssn_fr', 'iban', 'ip', 'date', 'api_key'
        """
        self.filters = (
            filters if filters else ["email", "phone", "cc", "ssn_us", "ssn_fr", "iban", "ip", "date", "api_key"]
        )
        self._compile_patterns()

    def _compile_patterns(self):
        self.patterns = {}

        # 1. Email (Standard RFC 5322 subset)
        if "email" in self.filters:
            self.patterns["email"] = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")

        # 2. Phone (International E.164-ish & Local)
        if "phone" in self.filters:
            self.patterns["phone"] = re.compile(r"(?:\b(?:\+|00)33|0)\s*[1-9](?:[\s.-]*\d{2}){4}\b")

        # 3. SSN US (Strict formatting)
        if "ssn_us" in self.filters:
            self.patterns["ssn_us"] = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

        # 4. SSN FR (NIR) - Matches 13 digits + 2 optional key digits, allows A/B for Corsica
        if "ssn_fr" in self.filters:
            self.patterns["ssn_fr"] = re.compile(
                r"\b[12][\s\.]?\d{2}[\s\.]?(?:0[1-9]|1[0-2]|2[0-9]|2[AB])[\s\.]?\d{2}[\s\.]?\d{3}[\s\.]?\d{3}(?:[\s\.]?\d{2})?\b"
            )

        # 5. IBAN (Generic Structure)
        if "iban" in self.filters:
            self.patterns["iban"] = re.compile(r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){2,}(?:\s?[A-Z0-9]{1,4})?\b")

        # 6. IP Address (Strict IPv4 - excludes 999.999.999.999)
        if "ip" in self.filters:
            self.patterns["ip"] = re.compile(
                r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
            )

        # 7. Date (ISO 8601 & Common formats)
        if "date" in self.filters:
            self.patterns["date"] = re.compile(r"\b(?:\d{4}[-/]\d{2}[-/]\d{2})|(?:\d{2}[-/]\d{2}[-/]\d{4})\b")

        # 8. API Keys (High entropy strings assigned to variables)
        if "api_key" in self.filters:
            self.patterns["api_key"] = re.compile(
                r"(?i)(?:api_key|access_token|secret|auth_token)(?:[\"\']?\s?[:=]\s?[\"\']?)([a-z0-9_\-]{16,})"
            )

        # 9. Credit Card (Strict Boundaries)
        if "cc" in self.filters:
            # CRITICAL: The Lookbehind (?<!\.) and Lookahead (?!\.) prevent matching the
            # integer part of a float (e.g. 1234.56).
            # Matches: 16 digits contiguous, or groups of 4.
            self.cc_pattern = re.compile(
                r"(?<![\d\.])\b(?:\d{4}[-\s]?){3}\d{4}\b(?![\d\.])|(?<![\d\.])\b\d{13,19}\b(?![\d\.])"
            )

    # --- CHECKSUM ALGORITHMS (Production Grade) ---

    def _is_luhn_valid(self, number: str) -> bool:
        """Standard Luhn Algorithm for Credit Cards."""
        digits = [int(d) for d in re.sub(r"\D", "", number)]
        checksum = 0
        reverse_digits = digits[::-1]

        for i, digit in enumerate(reverse_digits):
            if i % 2 == 1:
                doubled = digit * 2
                checksum += doubled if doubled < 10 else doubled - 9
            else:
                checksum += digit
        return checksum % 10 == 0

    def _is_iban_valid(self, iban: str) -> bool:
        """ISO 7064 Mod 97 Check for IBAN."""
        # 1. Remove spaces/dashes and upper case
        clean = re.sub(r"[^A-Z0-9]", "", iban.upper())
        if len(clean) < 15:
            return False  # Basic min length

        # 2. Move first 4 chars (Country+Check) to the end
        rearranged = clean[4:] + clean[:4]

        # 3. Convert letters to numbers (A=10, B=11...)
        numeric_str = ""
        for char in rearranged:
            if char.isdigit():
                numeric_str += char
            else:
                numeric_str += str(ord(char) - 55)

        # 4. Modulo 97
        return int(numeric_str) % 97 == 1

    def _is_nir_valid(self, ssn: str) -> bool:
        """French SSN (NIR) Key Validation (Mod 97). Handles Corsica (2A/2B)."""
        clean = re.sub(r"[^0-9AB]", "", ssn.upper())

        # Must be 15 chars (13 digit + 2 key) or 13 (we might want to mask without key too, but usually key is present)
        # For stricter masking, we assume the 15 digit format (number + key) is present in text
        if len(clean) != 15:
            return False

        number_part = clean[:13]
        key_part = int(clean[13:])

        # Handle Corsica Exceptions
        if "2A" in number_part:
            number_part = number_part.replace("2A", "19")
            # Math trick for 2A: subtract 1,000,000 from the numeric conversion if needed,
            # but string replacement usually works for the modulo check logic if consistent.
            # Standard algo: treat 2A as 19, then subtract 1,000,000 from the resulting integer
            numeric_val = int(number_part) - 1000000
        elif "2B" in number_part:
            number_part = number_part.replace("2B", "18")
            numeric_val = int(number_part) - 2000000
        else:
            numeric_val = int(number_part)

        expected_key = 97 - (numeric_val % 97)
        return expected_key == key_part

    def _is_valid_us_ssn_structure(self, ssn: str) -> bool:
        """Checks for 'Impossible' US SSN numbers."""
        clean = re.sub(r"\D", "", ssn)
        if len(clean) != 9:
            return False

        area = int(clean[:3])
        group = int(clean[3:5])
        serial = int(clean[5:])

        # 1. Area cannot be 000, 666, or 900-999
        if area == 0 or area == 666 or area >= 900:
            return False

        # 2. Group cannot be 00
        if group == 0:
            return False

        # 3. Serial cannot be 0000
        if serial == 0:
            return False

        return True

    # --- MASKING LOGIC ---

    def mask(self, text: str) -> str:
        if not text:
            return text

        # 1. Simple Regex Filters (Email, Phone, IP)
        if "email" in self.filters:
            text = self.patterns["email"].sub("[EMAIL_REDACTED]", text)
        if "phone" in self.filters:
            text = self.patterns["phone"].sub("[PHONE_REDACTED]", text)
        if "ip" in self.filters:
            text = self.patterns["ip"].sub("[IP_REDACTED]", text)

        # 2. Complex Logic Filters

        if "ssn_us" in self.filters:

            def validate_us(match):
                if self._is_valid_us_ssn_structure(match.group(0)):
                    return "[SSN_US_REDACTED]"
                return match.group(0)  # It's just a random ID, not an SSN

            text = self.patterns["ssn_us"].sub(validate_us, text)

        if "ssn_fr" in self.filters:

            def validate_fr(match):
                if self._is_nir_valid(match.group(0)):
                    return "[SSN_FR_REDACTED]"
                return match.group(0)

            text = self.patterns["ssn_fr"].sub(validate_fr, text)

        if "iban" in self.filters:

            def validate_iban_match(match):
                if self._is_iban_valid(match.group(0)):
                    return "[IBAN_REDACTED]"
                return match.group(0)

            text = self.patterns["iban"].sub(validate_iban_match, text)

        if "cc" in self.filters:

            def validate_cc(match):
                if self._is_luhn_valid(match.group(0)):
                    return "[CREDIT_CARD_REDACTED]"
                return match.group(0)  # It's a fraction or database ID

            text = self.cc_pattern.sub(validate_cc, text)

        if "date" in self.filters:

            def validate_date(match):
                # Basic logical validation (Month 1-12, Day 1-31)
                val = match.group(0).replace("/", "-")
                parts = val.split("-")
                # Detect format based on year position
                try:
                    if len(parts[0]) == 4:
                        _y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
                    else:
                        d, m, _y = int(parts[0]), int(parts[1]), int(parts[2])

                    if 1 <= m <= 12 and 1 <= d <= 31:
                        return "[DATE_REDACTED]"
                except ValueError:
                    pass
                return match.group(0)

            text = self.patterns["date"].sub(validate_date, text)

        if "api_key" in self.filters and "api_key" in self.patterns:

            def redact_key_value(match):
                full_str = match.group(0)
                sensitive_val = match.group(1)
                return full_str.replace(sensitive_val, "[API_KEY_REDACTED]")

            text = self.patterns["api_key"].sub(redact_key_value, text)

        return text


# Usage
masker = PIIMasker()
