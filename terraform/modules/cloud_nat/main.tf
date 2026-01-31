# =============================================================================
# Cloud NAT Module
# =============================================================================
# Provides controlled egress for external API calls with static IP
# All outbound traffic from Cloud Run goes through this NAT
# =============================================================================

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
}

variable "vpc_id" {
  description = "VPC Network ID"
  type        = string
}

variable "vpc_name" {
  description = "VPC Network name"
  type        = string
}

# -----------------------------------------------------------------------------
# Cloud Router (Required for Cloud NAT)
# -----------------------------------------------------------------------------

resource "google_compute_router" "nat_router" {
  name    = "${var.project_id}-nat-router"
  network = var.vpc_name
  region  = var.region
  project = var.project_id

  bgp {
    asn = 64514
  }
}

# -----------------------------------------------------------------------------
# Static IP Address for NAT (Whitelisting on external services)
# -----------------------------------------------------------------------------

resource "google_compute_address" "nat_ip" {
  name         = "${var.project_id}-nat-ip"
  region       = var.region
  project      = var.project_id
  address_type = "EXTERNAL"
  network_tier = "PREMIUM"
}

# Optional: Additional NAT IPs for high-throughput scenarios
resource "google_compute_address" "nat_ip_secondary" {
  count        = var.enable_secondary_nat_ip ? 1 : 0
  name         = "${var.project_id}-nat-ip-secondary"
  region       = var.region
  project      = var.project_id
  address_type = "EXTERNAL"
  network_tier = "PREMIUM"
}

variable "enable_secondary_nat_ip" {
  description = "Enable secondary NAT IP for high throughput"
  type        = bool
  default     = false
}

# -----------------------------------------------------------------------------
# Cloud NAT Gateway
# -----------------------------------------------------------------------------

resource "google_compute_router_nat" "nat" {
  name                   = "${var.project_id}-cloud-nat"
  router                 = google_compute_router.nat_router.name
  region                 = var.region
  project                = var.project_id
  nat_ip_allocate_option = "MANUAL_ONLY"
  nat_ips = concat(
    [google_compute_address.nat_ip.self_link],
    var.enable_secondary_nat_ip ? [google_compute_address.nat_ip_secondary[0].self_link] : []
  )
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  # Minimum ports per VM for consistent external connections
  min_ports_per_vm = 1024

  # Enable endpoint-independent mapping for better compatibility
  enable_endpoint_independent_mapping = true

  # Logging configuration
  log_config {
    enable = true
    filter = var.nat_log_filter
  }

  # UDP idle timeout (default is 30s, we increase for long-polling)
  udp_idle_timeout_sec = 120

  # TCP established idle timeout
  tcp_established_idle_timeout_sec = 1200

  # TCP transitory idle timeout
  tcp_transitory_idle_timeout_sec = 30

  # ICMP idle timeout
  icmp_idle_timeout_sec = 30
}

variable "nat_log_filter" {
  description = "NAT logging filter: ERRORS_ONLY, TRANSLATIONS_ONLY, or ALL"
  type        = string
  default     = "ERRORS_ONLY"
}

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

output "nat_ip_address" {
  description = "Primary NAT IP address (for whitelisting)"
  value       = google_compute_address.nat_ip.address
}

output "nat_ip_addresses" {
  description = "All NAT IP addresses"
  value = concat(
    [google_compute_address.nat_ip.address],
    var.enable_secondary_nat_ip ? [google_compute_address.nat_ip_secondary[0].address] : []
  )
}

output "router_name" {
  description = "Cloud Router name"
  value       = google_compute_router.nat_router.name
}

output "nat_name" {
  description = "Cloud NAT name"
  value       = google_compute_router_nat.nat.name
}
