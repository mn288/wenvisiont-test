from utils.pii import PIIMasker, masker


def test_mask_pii_email():
    text = "Contact me at john.doe@example.com for more info."
    masked = masker.mask(text)
    assert "[EMAIL_REDACTED]" in masked
    assert "john.doe@example.com" not in masked


def test_mask_pii_no_pii():
    text = "Hello world, this is safe."
    masked = masker.mask(text)
    assert masked == text


def test_mask_pii_credit_card():
    # Valid Luhn CC (Test Visa: 4539 1488 0343 6467)
    text = "My card is 4539-1488-0343-6467 do not share."
    masked = masker.mask(text)
    assert "[CREDIT_CARD_REDACTED]" in masked
    assert "4539-1488-0343-6467" not in masked

    # Raw digits (Valid Luhn)
    text2 = "Card: 4539148803436467"
    masked2 = masker.mask(text2)
    assert "[CREDIT_CARD_REDACTED]" in masked2

    # Invalid CC (Fails Luhn) - Should NOT be redacted
    text3 = "Invalid Card: 1234-5678-9012-3456"
    masked3 = masker.mask(text3)
    assert "[CREDIT_CARD_REDACTED]" not in masked3
    assert "1234-5678-9012-3456" in masked3


def test_mask_pii_ssn():
    text = "SSN is 123-45-6789."
    masked = masker.mask(text)
    assert "[SSN_US_REDACTED]" in masked
    assert "123-45-6789" not in masked


def test_mask_pii_false_positives():
    # Large numbers / Math
    cases = [
        "The value of pi is 3.141592653589793238",
        "Large number: 1000000000000",
        "Equation: 123456789012345 / 3",
        "Fraction: 123456789012345/100",
    ]
    for case in cases:
        assert masker.mask(case) == case


def test_mask_pii_ssn_french():
    # Valid French SSN (NIR): 13 digits + 2-digit key
    # Format: S YY MM DD CCC NNN KK where:
    # S=sex(1/2), YY=year, MM=month(01-12), DD=dept, CCC=commune, NNN=serial, KK=key(97-number%97)
    # For 1850575101234: key = 97 - (1850575101234 % 97) = 82
    valid_ssn = "1 85 05 75 101 234 82"
    assert "[SSN_FR_REDACTED]" in masker.mask(valid_ssn)

    # Invalid Month (13) - Should NOT be redacted (fails regex)
    invalid_ssn = "1 80 13 75 000 000 12"
    assert "[SSN_FR_REDACTED]" not in masker.mask(invalid_ssn)


def test_custom_filters():
    # Check flexibility: Only email, ignore phone
    custom_masker = PIIMasker(filters=["email"])

    text = "Email: test@example.com, Phone: 06 12 34 56 78"
    masked = custom_masker.mask(text)

    assert "[EMAIL_REDACTED]" in masked
    # Phone should NOT be masked
    assert "06 12 34 56 78" in masked
    assert "[PHONE_REDACTED]" not in masked
