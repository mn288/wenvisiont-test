resource "google_compute_network" "vpc" {
  name                    = "${var.project_id}-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "subnet" {
  name          = "${var.project_id}-subnet"
  ip_cidr_range = var.subnet_cidr
  region        = var.region
  network       = google_compute_network.vpc.id

  # Enable Private Google Access for Cloud Run to reach GCP APIs privately
  private_ip_google_access = true
}

# Private Service Access for Cloud SQL
resource "google_compute_global_address" "private_ip_address" {
  name          = "${var.project_id}-private-ip-address"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]
}

# Serverless VPC Access Connector (Optional if using Direct VPC Egress, but kept for compatibility/options)
# We will primarily use Direct VPC Egress in Cloud Run, so this might not be strictly needed,
# but often useful for other services.

# ============================================================================
# Private Service Connect (PSC) for Google APIs
# Provides secure private access to Google APIs without public internet exposure
# ============================================================================

# Reserved internal IP for PSC endpoint
resource "google_compute_global_address" "psc_address" {
  name         = "${var.project_id}-psc-endpoint-ip"
  purpose      = "PRIVATE_SERVICE_CONNECT"
  address_type = "INTERNAL"
  network      = google_compute_network.vpc.id
}

# PSC endpoint for googleapis.com
resource "google_compute_global_forwarding_rule" "psc_google_apis" {
  name                  = "${var.project_id}-psc-google-apis"
  target                = "all-apis"
  network               = google_compute_network.vpc.id
  ip_address            = google_compute_global_address.psc_address.id
  load_balancing_scheme = ""
}

# DNS zone for private access to googleapis.com
resource "google_dns_managed_zone" "psc_googleapis" {
  name        = "${var.project_id}-psc-googleapis"
  dns_name    = "googleapis.com."
  description = "Private DNS zone for PSC access to Google APIs"
  visibility  = "private"

  private_visibility_config {
    networks {
      network_url = google_compute_network.vpc.id
    }
  }
}

# A record pointing googleapis.com to PSC endpoint
resource "google_dns_record_set" "psc_googleapis_a" {
  name         = "*.googleapis.com."
  type         = "A"
  ttl          = 300
  managed_zone = google_dns_managed_zone.psc_googleapis.name
  rrdatas      = [google_compute_global_address.psc_address.address]
}

# CNAME for restricted.googleapis.com
resource "google_dns_record_set" "psc_restricted_googleapis" {
  name         = "restricted.googleapis.com."
  type         = "A"
  ttl          = 300
  managed_zone = google_dns_managed_zone.psc_googleapis.name
  rrdatas      = [google_compute_global_address.psc_address.address]
}

# ============================================================================
# Private Service Connect for Vertex AI (aiplatform.googleapis.com)
# ============================================================================

resource "google_dns_managed_zone" "psc_vertexai" {
  name        = "${var.project_id}-psc-vertexai"
  dns_name    = "aiplatform.googleapis.com."
  description = "Private DNS zone for PSC access to Vertex AI"
  visibility  = "private"

  private_visibility_config {
    networks {
      network_url = google_compute_network.vpc.id
    }
  }
}

resource "google_dns_record_set" "psc_vertexai_a" {
  name         = "${var.region}-aiplatform.googleapis.com."
  type         = "A"
  ttl          = 300
  managed_zone = google_dns_managed_zone.psc_vertexai.name
  rrdatas      = [google_compute_global_address.psc_address.address]
}
