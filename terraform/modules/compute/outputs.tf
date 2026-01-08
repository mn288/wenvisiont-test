# Outputs for Compute Module

output "backend_sa_email" {
  value       = google_service_account.backend_sa.email
  description = "Email of the backend Cloud Run service account"
}

output "frontend_sa_email" {
  value       = google_service_account.frontend_sa.email
  description = "Email of the frontend Cloud Run service account"
}

output "backend_url" {
  value       = google_cloud_run_v2_service.backend.uri
  description = "URL of the backend Cloud Run service"
}

output "frontend_url" {
  value       = google_cloud_run_v2_service.frontend.uri
  description = "URL of the frontend Cloud Run service"
}
