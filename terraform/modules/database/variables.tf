variable "project_id" { type = string }
variable "region" { type = string }
variable "vpc_id" { type = string }

variable "instance_tier" {
  type    = string
  default = "db-f1-micro" # Upgrage to db-custom-X-Y for production
}

variable "db_name" {
  type    = string
  default = "app_db"
}

variable "db_user" {
  type    = string
  default = "app_user"
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "kms_key_name" {
  description = "KMS Key Name for CMEK"
  type        = string
  default     = null
}
