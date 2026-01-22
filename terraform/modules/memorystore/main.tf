variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID for private access"
  type        = string
}

resource "google_redis_instance" "cache" {
  name           = "${var.project_id}-redis"
  memory_size_gb = 1
  region         = var.region
  
  # Use a tier that supports basic availability or HA depending on requirements
  tier = "BASIC" 

  authorized_network = var.vpc_id
  
  redis_version = "REDIS_6_X"
  display_name  = "Session Cache"

  connect_mode = "PRIVATE_SERVICE_ACCESS"
}

output "redis_host" {
  value = google_redis_instance.cache.host
}

output "redis_port" {
  value = google_redis_instance.cache.port
}
