# =============================================================================
# VPC Service Controls Module
# =============================================================================
# Creates a Zero-Trust perimeter in europe-west-9 to prevent data exfiltration
# Ensures all sensitive GCP services are contained within the perimeter
# =============================================================================

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "project_number" {
  description = "GCP Project Number (numeric)"
  type        = string
}

variable "access_policy_id" {
  description = "Access Context Manager Policy ID. If empty, a new policy will be created."
  type        = string
  default     = ""
}

variable "org_id" {
  description = "Organization ID for Access Context Manager policy creation"
  type        = string
  default     = ""
}

# -----------------------------------------------------------------------------
# Access Context Manager Policy (Created if not provided)
# -----------------------------------------------------------------------------

resource "google_access_context_manager_access_policy" "awp_policy" {
  count  = var.access_policy_id == "" ? 1 : 0
  parent = "organizations/${var.org_id}"
  title  = "AWP Sovereign Access Policy"
}

locals {
  policy_id = var.access_policy_id != "" ? var.access_policy_id : google_access_context_manager_access_policy.awp_policy[0].name
}

# -----------------------------------------------------------------------------
# Access Level (Defines conditions for access)
# -----------------------------------------------------------------------------

resource "google_access_context_manager_access_level" "trusted_access" {
  parent = "accessPolicies/${local.policy_id}"
  name   = "accessPolicies/${local.policy_id}/accessLevels/awp_trusted_access"
  title  = "AWP Trusted Access"

  basic {
    conditions {
      # Require corporate IP ranges (to be configured)
      ip_subnetworks = var.allowed_ip_ranges

      # Require specific regions
      regions = ["FR", "EU"]
    }
  }
}

variable "allowed_ip_ranges" {
  description = "List of allowed IP CIDR ranges for access"
  type        = list(string)
  default     = []
}

# -----------------------------------------------------------------------------
# VPC Service Controls Perimeter
# -----------------------------------------------------------------------------

resource "google_access_context_manager_service_perimeter" "awp_perimeter" {
  parent = "accessPolicies/${local.policy_id}"
  name   = "accessPolicies/${local.policy_id}/servicePerimeters/awp_sovereign_perimeter"
  title  = "AWP Sovereign Perimeter"

  status {
    # Projects inside the perimeter
    resources = [
      "projects/${var.project_number}"
    ]

    # Services to restrict (cannot be accessed from outside perimeter)
    restricted_services = [
      "storage.googleapis.com",
      "bigquery.googleapis.com",
      "aiplatform.googleapis.com",
      "secretmanager.googleapis.com",
      "sqladmin.googleapis.com",
      "run.googleapis.com",
      "cloudfunctions.googleapis.com",
      "dlp.googleapis.com",
      "cloudkms.googleapis.com"
    ]

    # VPC Accessible Services configuration
    vpc_accessible_services {
      enable_restriction = true
      allowed_services   = ["RESTRICTED-SERVICES"]
    }

    # Access levels that can cross the perimeter
    access_levels = [
      google_access_context_manager_access_level.trusted_access.name
    ]
  }

  # Use dry-run mode initially to test without blocking
  use_explicit_dry_run_spec = var.dry_run_mode

  dynamic "spec" {
    for_each = var.dry_run_mode ? [1] : []
    content {
      resources = [
        "projects/${var.project_number}"
      ]
      restricted_services = [
        "storage.googleapis.com",
        "bigquery.googleapis.com",
        "aiplatform.googleapis.com",
        "secretmanager.googleapis.com",
        "sqladmin.googleapis.com"
      ]
    }
  }
}

variable "dry_run_mode" {
  description = "Enable dry-run mode for testing perimeter without blocking"
  type        = bool
  default     = true
}

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

output "perimeter_name" {
  description = "Name of the VPC Service Controls perimeter"
  value       = google_access_context_manager_service_perimeter.awp_perimeter.name
}

output "access_policy_id" {
  description = "Access Policy ID"
  value       = local.policy_id
}

output "access_level_name" {
  description = "Access Level name for trusted access"
  value       = google_access_context_manager_access_level.trusted_access.name
}
