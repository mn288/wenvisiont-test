resource "google_service_account" "backend_sa" {
  account_id   = "backend-sa"
  display_name = "Backend Cloud Run Service Account"
}

resource "google_service_account" "frontend_sa" {
  account_id   = "frontend-sa"
  display_name = "Frontend Cloud Run Service Account"
}

# Backend Service
resource "google_cloud_run_v2_service" "backend" {
  name     = "backend"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"

  template {
    service_account = google_service_account.backend_sa.email

    containers {
      image = var.backend_image

      env {
        name  = "DATABASE_URL"
        value = var.database_url
      }

      env {
        name  = "API_V1_STR"
        value = "/api/v1"
      }
    }

    vpc_access {
      network_interfaces {
        network    = var.vpc_name
        subnetwork = var.subnet_name
      }
      egress = "ALL_TRAFFIC"
    }
  }
}

resource "google_cloud_run_v2_service" "frontend" {
  name     = "frontend"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"

  template {
    service_account = google_service_account.frontend_sa.email

    containers {
      image = var.frontend_image

      env {
        name  = "NEXT_PUBLIC_API_URL"
        value = "/api" # Relative path when behind LB
      }
    }

    vpc_access {
      network_interfaces {
        network    = var.vpc_name
        subnetwork = var.subnet_name
      }
      egress = "ALL_TRAFFIC"
    }
  }
}

# Network Endpoint Groups (NEGs)

resource "google_compute_region_network_endpoint_group" "backend_neg" {
  name                  = "backend-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  cloud_run {
    service = google_cloud_run_v2_service.backend.name
  }
}

resource "google_compute_region_network_endpoint_group" "frontend_neg" {
  name                  = "frontend-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  cloud_run {
    service = google_cloud_run_v2_service.frontend.name
  }
}


