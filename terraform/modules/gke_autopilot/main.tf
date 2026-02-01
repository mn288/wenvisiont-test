resource "google_container_cluster" "primary" {
  name     = "antigravity-cluster"
  location = var.region
  project  = var.project_id

  # GKE Autopilot Mode
  enable_autopilot = true

  network    = var.vpc_name
  subnetwork = var.subnet_name

  # Confidential Computing (SEV-SNP)
  confidential_nodes {
    enabled = true
  }

  # Private Cluster Config (Zero-Trust)
  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false # Access via IAP/Bastion recommended in strict mode, but public endpoint with CIDR whitelist often practical
    master_ipv4_cidr_block  = "172.16.0.0/28"
  }

  # Maintenance Policy
  maintenance_policy {
    recurring_window {
      start_time = "2024-01-01T00:00:00Z"
      end_time   = "2024-01-01T04:00:00Z"
      recurrence = "FREQ=WEEKLY;BYDAY=SA,SU"
    }
  }

  # Workload Identity
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  ip_allocation_policy {
    # Auto-allocation
    cluster_ipv4_cidr_block  = "/14"
    services_ipv4_cidr_block = "/20"
  }

  deletion_protection = false # For dev/demo ease
}

# Output required for providers
output "cluster_endpoint" {
  value = google_container_cluster.primary.endpoint
}

output "cluster_ca_certificate" {
  value = google_container_cluster.primary.master_auth[0].cluster_ca_certificate
}

output "cluster_name" {
  value = google_container_cluster.primary.name
}

output "cluster_id" {
  value = google_container_cluster.primary.id
}
