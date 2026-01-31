variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
}

variable "frontend_neg" {
  description = "Network Endpoint Group for Frontend"
  type        = string
}

variable "backend_neg" {
  description = "Network Endpoint Group for Backend"
  type        = string
}

variable "security_policy_id" {
  description = "Cloud Armor Security Policy ID"
  type        = string
}

variable "domain_name" {
  description = "Domain name for the Load Balancer"
  type        = string
  default     = ""
}

variable "ssl_certificate_id" {
  description = "SSL Certificate ID"
  type        = string
  default     = ""
}

# Backend Service for Frontend
resource "google_compute_backend_service" "frontend_backend" {
  name        = "${var.project_id}-frontend-backend"
  protocol    = "HTTP"
  port_name   = "http"
  timeout_sec = 30

  security_policy = var.security_policy_id

  backend {
    group = var.frontend_neg
  }

  log_config {
    enable      = true
    sample_rate = 1.0
  }
}

# Backend Service for Backend API
resource "google_compute_backend_service" "api_backend" {
  name        = "${var.project_id}-api-backend"
  protocol    = "HTTP"
  port_name   = "http"
  timeout_sec = 30

  security_policy = var.security_policy_id

  backend {
    group = var.backend_neg
  }

  log_config {
    enable      = true
    sample_rate = 1.0
  }
}

# URL Map
resource "google_compute_url_map" "default" {
  name            = "${var.project_id}-url-map"
  default_service = google_compute_backend_service.frontend_backend.id

  host_rule {
    hosts        = ["*"]
    path_matcher = "allpaths"
  }

  path_matcher {
    name            = "allpaths"
    default_service = google_compute_backend_service.frontend_backend.id

    path_rule {
      paths   = ["/api/*"]
      service = google_compute_backend_service.api_backend.id
    }
  }
}

# Target HTTP Proxy (For testing, ideally HTTPS)
resource "google_compute_target_http_proxy" "default" {
  name    = "${var.project_id}-http-proxy"
  url_map = google_compute_url_map.default.id
}

# Global Forwarding Rule
resource "google_compute_global_forwarding_rule" "default" {
  name       = "${var.project_id}-lb-forwarding-rule"
  target     = google_compute_target_http_proxy.default.id
  port_range = "80"
}

# Optional HTTPS Proxy (requires cert)
# resource "google_compute_target_https_proxy" "https" {
#   count   = var.ssl_certificate_id != "" ? 1 : 0
#   name    = "${var.project_id}-https-proxy"
#   url_map = google_compute_url_map.default.id
#   ssl_certificates = [var.ssl_certificate_id]
# }

output "load_balancer_ip" {
  value = google_compute_global_forwarding_rule.default.ip_address
}

output "backend_service_id" {
  description = "Backend service ID for IAP binding"
  value       = google_compute_backend_service.api_backend.id
}

output "backend_service_name" {
  description = "Backend service name for IAP binding"
  value       = google_compute_backend_service.api_backend.name
}

output "frontend_backend_service_id" {
  description = "Frontend backend service ID"
  value       = google_compute_backend_service.frontend_backend.id
}
