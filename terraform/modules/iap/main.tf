# =============================================================================
# Identity-Aware Proxy (IAP) Module
# =============================================================================
# Configures IAP authentication for Cloud Run services
# Provides identity propagation for Human-in-the-Loop approvals
# =============================================================================

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "project_number" {
  description = "GCP Project Number"
  type        = string
}

variable "backend_service_id" {
  description = "Backend service ID for IAP binding"
  type        = string
}

variable "allowed_members" {
  description = "List of members allowed IAP access (e.g., user:email@example.com, domain:example.com)"
  type        = list(string)
  default     = []
}

# -----------------------------------------------------------------------------
# manual_step: OAuth Consent Screen & Client
# -----------------------------------------------------------------------------
# IMPORTANT: The `google_iap_brand` and `google_iap_client` resources are 
# DEPRECATED as of Jan 2025.
#
# ACTION REQUIRED: You must manually configure the OAuth Consent Screen 
# and create an OAuth Client ID in the Google Cloud Console.
# 
# 1. Go to APIs & Services > OAuth consent screen.
# 2. Configure the consent screen (Application Name: "AWP Agentic Workflow Platform").
# 3. Go to APIs & Services > Credentials.
# 4. Create an OAuth 2.0 Client ID (Application type: "Web application").
# 5. Add Authorized redirect URIs for IAP (https://iap.googleapis.com/v1/oauth/clientIds/YOUR_CLIENT_ID:handleRedirect).
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# IAP Web Backend Service IAM Binding
# -----------------------------------------------------------------------------

resource "google_iap_web_backend_service_iam_binding" "backend_binding" {
  project             = var.project_id
  web_backend_service = var.backend_service_id
  role                = "roles/iap.httpsResourceAccessor"
  members             = var.allowed_members
}

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------
# No outputs for Client ID/Secret as they are now managed manually.
