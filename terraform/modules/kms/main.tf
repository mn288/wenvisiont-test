variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
}

resource "google_kms_key_ring" "key_ring" {
  name     = "${var.project_id}-keyring"
  location = var.region
}

resource "google_kms_crypto_key" "database_key" {
  name            = "database-key"
  key_ring        = google_kms_key_ring.key_ring.id
  rotation_period = "7776000s" # 90 days

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_kms_crypto_key" "storage_key" {
  name            = "storage-key"
  key_ring        = google_kms_key_ring.key_ring.id
  rotation_period = "7776000s" # 90 days

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_kms_crypto_key" "vertex_key" {
  name            = "vertex-key"
  key_ring        = google_kms_key_ring.key_ring.id
  rotation_period = "7776000s" # 90 days

  lifecycle {
    prevent_destroy = true
  }
}

output "key_ring_name" {
  value = google_kms_key_ring.key_ring.name
}

output "database_key_id" {
  value = google_kms_crypto_key.database_key.id
}

output "storage_key_id" {
  value = google_kms_crypto_key.storage_key.id
}

output "vertex_key_id" {
  value = google_kms_crypto_key.vertex_key.id
}
