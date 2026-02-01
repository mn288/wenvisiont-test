variable "project_id" {
  type = string
}

variable "domain_name" {
  type        = string
  description = "Domain name for the managed SSL certificate"
}

resource "google_compute_global_address" "default" {
  name    = "antigravity-ip"
  project = var.project_id
}

resource "google_compute_managed_ssl_certificate" "default" {
  name    = "antigravity-cert"
  project = var.project_id

  managed {
    domains = [var.domain_name]
  }
}

output "ip_address" {
  value = google_compute_global_address.default.address
}

output "ip_name" {
  value = google_compute_global_address.default.name
}

output "certificate_name" {
  value = google_compute_managed_ssl_certificate.default.name
}
