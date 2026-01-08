from utils.pii import mask_pii


def test_mask_pii_email():
    text = "Contact me at john.doe@example.com for more info."
    masked = mask_pii(text)
    assert "[EMAIL_REDACTED]" in masked
    assert "john.doe@example.com" not in masked


def test_mask_pii_no_pii():
    text = "Hello world, this is safe."
    masked = mask_pii(text)
    assert masked == text


def test_mask_pii_credit_card():
    # Simple 16 digit
    text = "My card is 1234-5678-9012-3456 do not share."
    masked = mask_pii(text)
    assert "[CREDIT_CARD_REDACTED]" in masked
    assert "1234-5678-9012-3456" not in masked

    # Raw digits
    text2 = "Card: 4444444444444444"
    masked2 = mask_pii(text2)
    assert "[CREDIT_CARD_REDACTED]" in masked2


def test_mask_pii_ssn():
    text = "SSN is 123-45-6789."
    masked = mask_pii(text)
    assert "[SSN_REDACTED]" in masked
    assert "123-45-6789" not in masked
