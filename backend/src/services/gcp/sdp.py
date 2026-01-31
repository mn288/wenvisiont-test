"""
GCP Sensitive Data Protection (Cloud DLP) Integration.
Provides PII redaction at ingress using GCP managed service.

This module wraps Google Cloud DLP to provide:
- Automatic PII detection using pre-configured templates
- De-identification using masking or replacement
- Fallback to local PIIMasker when GCP is not configured
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_dlp_client = None


def _get_settings():
    """Lazy import of settings to avoid circular imports."""
    from core.config import settings

    return settings


def get_dlp_client():
    """
    Lazy initialization of DLP client.
    Returns None if SDP is not enabled or GCP is not configured.
    """
    global _dlp_client
    settings = _get_settings()

    if _dlp_client is None and settings.SDP_ENABLED:
        try:
            from google.cloud import dlp_v2

            _dlp_client = dlp_v2.DlpServiceClient()
            logger.info("GCP DLP client initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize GCP DLP client: {e}")
            _dlp_client = None

    return _dlp_client


async def mask_pii_gcp(text: str, inspect_template: Optional[str] = None) -> str:
    """
    Use Google Cloud DLP to redact PII from text.
    Falls back to local PIIMasker if GCP is not configured.

    Args:
        text: Input text to mask
        inspect_template: Optional custom inspect template name

    Returns:
        Text with PII redacted
    """
    if not text:
        return text

    settings = _get_settings()

    # Fallback to local implementation if GCP not configured
    if not settings.SDP_ENABLED or not settings.GCP_PROJECT_ID:
        from utils.pii import masker

        return masker.mask(text)

    client = get_dlp_client()
    if not client:
        from utils.pii import masker

        return masker.mask(text)

    parent = f"projects/{settings.GCP_PROJECT_ID}/locations/{settings.GCP_REGION}"

    # Use custom or default inspect template
    template_name = inspect_template or settings.SDP_INSPECT_TEMPLATE

    # De-identification configuration
    deidentify_config = {
        "info_type_transformations": {
            "transformations": [
                {
                    "info_types": [
                        {"name": "EMAIL_ADDRESS"},
                        {"name": "PHONE_NUMBER"},
                        {"name": "CREDIT_CARD_NUMBER"},
                    ],
                    "primitive_transformation": {
                        "character_mask_config": {
                            "masking_character": "*",
                            "number_to_mask": 0,  # Mask all characters
                        }
                    },
                },
                {
                    "info_types": [
                        {"name": "PERSON_NAME"},
                    ],
                    "primitive_transformation": {"replace_config": {"new_value": {"string_value": "[PERSON_NAME]"}}},
                },
                {
                    "info_types": [
                        {"name": "LOCATION"},
                        {"name": "STREET_ADDRESS"},
                    ],
                    "primitive_transformation": {"replace_config": {"new_value": {"string_value": "[LOCATION]"}}},
                },
            ]
        }
    }

    # Inspect configuration (used if no template provided)
    inspect_config = None
    if not template_name:
        inspect_config = {
            "info_types": [
                {"name": "EMAIL_ADDRESS"},
                {"name": "PHONE_NUMBER"},
                {"name": "CREDIT_CARD_NUMBER"},
                {"name": "IBAN_CODE"},
                {"name": "PERSON_NAME"},
                {"name": "LOCATION"},
                {"name": "STREET_ADDRESS"},
            ],
            "min_likelihood": "POSSIBLE",
            "include_quote": False,
        }

    item = {"value": text}

    try:
        request = {
            "parent": parent,
            "deidentify_config": deidentify_config,
            "item": item,
        }

        if template_name:
            request["inspect_template_name"] = template_name
        else:
            request["inspect_config"] = inspect_config

        response = client.deidentify_content(request=request)

        logger.debug(f"DLP masked {len(response.overview.transformation_summaries)} items")
        return response.item.value

    except Exception as e:
        logger.warning(f"GCP DLP failed, falling back to local: {e}")
        from utils.pii import masker

        return masker.mask(text)


async def inspect_pii(text: str) -> list:
    """
    Inspect text for PII without redaction.
    Returns list of findings with info types and likelihood.

    Args:
        text: Input text to inspect

    Returns:
        List of PII findings
    """
    settings = _get_settings()

    if not settings.SDP_ENABLED or not settings.GCP_PROJECT_ID:
        logger.debug("SDP not enabled, skipping inspection")
        return []

    client = get_dlp_client()
    if not client:
        return []

    parent = f"projects/{settings.GCP_PROJECT_ID}/locations/{settings.GCP_REGION}"

    inspect_config = {
        "info_types": [
            {"name": "EMAIL_ADDRESS"},
            {"name": "PHONE_NUMBER"},
            {"name": "CREDIT_CARD_NUMBER"},
            {"name": "IBAN_CODE"},
            {"name": "PERSON_NAME"},
            {"name": "LOCATION"},
        ],
        "min_likelihood": "POSSIBLE",
        "include_quote": True,
    }

    item = {"value": text}

    try:
        response = client.inspect_content(
            request={
                "parent": parent,
                "inspect_config": inspect_config,
                "item": item,
            }
        )

        findings = []
        for finding in response.result.findings:
            findings.append(
                {
                    "info_type": finding.info_type.name,
                    "likelihood": finding.likelihood.name,
                    "quote": finding.quote if finding.quote else None,
                }
            )

        return findings

    except Exception as e:
        logger.error(f"GCP DLP inspection failed: {e}")
        return []
