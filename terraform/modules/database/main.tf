resource "google_sql_database_instance" "instance" {
  name             = "${var.project_id}-postgres"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier = var.instance_tier

    ip_configuration {
      ipv4_enabled    = false
      private_network = var.vpc_id
      ssl_mode        = "ENCRYPTED_ONLY"
    }

    backup_configuration {
      enabled    = true
      start_time = "02:00"
    }
    
    # CMEK integration
    # Note: Service Account for Cloud SQL needs permissions on the key first.
    # disk_encryption_configuration {
    #   kms_key_name = var.kms_key_name
    # }
  }

  encryption_key_name = var.kms_key_name

  deletion_protection = true # Recommended for production
}

resource "google_sql_database" "database" {
  name     = var.db_name
  instance = google_sql_database_instance.instance.name
  # deletion_policy = "ABANDON" # Optional if needed
}



resource "google_sql_user" "user" {
  name     = var.db_user
  instance = google_sql_database_instance.instance.name
  password = var.db_password # In production, pull this from Secret Manager
}
