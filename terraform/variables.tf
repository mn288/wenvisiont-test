variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "project_number" {
  description = "GCP Project Number (numeric ID)"
  type        = string
  default     = ""
}

variable "region" {
  description = "GCP Region (e.g., europe-west9 for EU sovereignty)"
  type        = string
  default     = "europe-west9"
}

variable "zone" {
  description = "GCP Zone (e.g., europe-west9-a)"
  type        = string
  default     = "europe-west9-a"
}

# =============================================================================
# Load Balancer & SSL
# =============================================================================

variable "domain_name" {
  description = "Domain name for the load balancer (optional)"
  type        = string
  default     = ""
}

variable "ssl_certificate_id" {
  description = "Existing SSL Certificate ID (optional)"
  type        = string
  default     = ""
}

# =============================================================================
# CI/CD
# =============================================================================

variable "github_repo" {
  description = "GitHub Repository for CI/CD (owner/repo)"
  type        = string
  default     = ""
}

# =============================================================================
# AWP GCP Sovereign Infrastructure
# =============================================================================

# --- Organization & Access Policy ---

variable "org_id" {
  description = "GCP Organization ID (for VPC Service Controls)"
  type        = string
  default     = ""
}

variable "access_policy_id" {
  description = "Existing Access Context Manager policy ID (leave empty to create new)"
  type        = string
  default     = ""
}

# --- Identity-Aware Proxy (IAP) ---

variable "enable_iap" {
  description = "Enable Identity-Aware Proxy for authentication"
  type        = bool
  default     = false
}

variable "iap_support_email" {
  description = "[DEPRECATED] Support email (unused: manual OAuth configuration required)"
  type        = string
  default     = ""
}

variable "iap_allowed_members" {
  description = "List of members allowed IAP access (e.g., user:email@example.com, domain:example.com)"
  type        = list(string)
  default     = []
}

# --- VPC Service Controls ---

variable "enable_vpc_service_controls" {
  description = "Enable VPC Service Controls for Zero-Trust perimeter"
  type        = bool
  default     = false
}

variable "vpc_sc_allowed_ip_ranges" {
  description = "List of IP CIDR ranges allowed through VPC Service Controls"
  type        = list(string)
  default     = []
}

variable "vpc_sc_dry_run_mode" {
  description = "Enable dry-run mode for VPC Service Controls (testing without blocking)"
  type        = bool
  default     = true
}

# --- Cloud NAT ---

variable "enable_high_throughput_nat" {
  description = "Enable secondary NAT IP for high throughput scenarios"
  type        = bool
  default     = false
}

variable "nat_log_filter" {
  description = "Cloud NAT logging filter: ERRORS_ONLY, TRANSLATIONS_ONLY, or ALL"
  type        = string
  default     = "ERRORS_ONLY"
}
