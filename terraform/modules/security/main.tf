resource "google_secret_manager_secret" "db_password" {
  secret_id = "db-password"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "db_password_val" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = var.db_password
}

# Add other secrets here (OpenAI API Key, etc.)
resource "google_secret_manager_secret" "openai_api_key" {
  secret_id = "openai-api-key"
  replication {
    auto {}
  }
}

# Note: We are not populating openai_api_key value here to avoid state leakage, 
# usually manual or via a separate secure process.
