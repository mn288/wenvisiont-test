module "apis" {
  source     = "./modules/apis"
  project_id = var.project_id
}

module "networking" {
  source      = "./modules/networking"
  project_id  = var.project_id
  region      = var.region
  subnet_cidr = "10.0.0.0/24"
  
  depends_on = [module.apis]
}

module "kms" {
  source     = "./modules/kms"
  project_id = var.project_id
  region     = var.region
}

module "artifact_registry" {
  source     = "./modules/artifact_registry"
  project_id = var.project_id
  region     = var.region
}

module "dlp" {
  source     = "./modules/dlp"
  project_id = var.project_id
  region     = var.region
}

resource "random_password" "db_password" {
  length  = 16
  special = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

module "security" {
  source      = "./modules/security"
  project_id  = var.project_id
  db_password = random_password.db_password.result
}

module "database" {
  source      = "./modules/database"
  project_id  = var.project_id
  region      = var.region
  vpc_id      = module.networking.vpc_id
  db_password = random_password.db_password.result
  kms_key_name = module.kms.database_key_id
  
  depends_on = [module.networking, module.kms]
}

module "memorystore" {
  source     = "./modules/memorystore"
  project_id = var.project_id
  region     = var.region
  vpc_id     = module.networking.vpc_id
  
  depends_on = [module.networking]
}

module "vertex_ai" {
  source     = "./modules/vertex_ai"
  project_id = var.project_id
  region     = var.region
  vpc_id     = module.networking.vpc_id
  encryption_key_name = module.kms.vertex_key_id
  
  depends_on = [module.networking, module.kms]
}

module "compute" {
  source         = "./modules/compute"
  project_id     = var.project_id
  region         = var.region
  vpc_name       = module.networking.vpc_name
  subnet_name    = module.networking.subnet_name
  backend_image  = "${module.artifact_registry.repository_url}/backend:latest"
  frontend_image = "${module.artifact_registry.repository_url}/frontend:latest"
  
  # Construct Database URL with Redis and Vertex AI config if needed
  # postgresql+asyncpg://user:password@ip:5432/dbname
  database_url   = "postgresql+asyncpg://${module.database.db_user}:${random_password.db_password.result}@${module.database.instance_ip_address}:5432/${module.database.db_name}"
  
  depends_on = [module.database]
}

# -------------------------------------------------------------------------
# Phase 3 Hardening: Cloud Armor WAF & Load Balancing
# -------------------------------------------------------------------------
module "cloud_armor" {
  source     = "./modules/cloud_armor"
  project_id = var.project_id
}

module "load_balancer" {
  source             = "./modules/load_balancer"
  project_id         = var.project_id
  region             = var.region
  frontend_neg       = module.compute.frontend_neg_id
  backend_neg        = module.compute.backend_neg_id
  security_policy_id = module.cloud_armor.policy_id
  domain_name        = var.domain_name
  ssl_certificate_id = var.ssl_certificate_id
  
  depends_on = [module.compute, module.cloud_armor]
}

# -------------------------------------------------------------------------
# Phase 3 Hardening: Least-Privilege IAM Bindings
# -------------------------------------------------------------------------
module "iam" {
  source              = "./modules/iam"
  project_id          = var.project_id
  backend_sa_email    = module.compute.backend_sa_email
  frontend_sa_email   = module.compute.frontend_sa_email
  backend_location    = var.region
  backend_service_name = "backend"
  enable_authenticated_invoker = true
  github_sa_email     = module.github_oidc.service_account_email
  
  depends_on = [module.compute, module.github_oidc]
}

# -------------------------------------------------------------------------
# CI/CD: Workload Identity Federation
# -------------------------------------------------------------------------
module "github_oidc" {
  source      = "./modules/github_oidc"
  project_id  = var.project_id
  github_repo = var.github_repo
}

output "load_balancer_ip" {
  value = module.load_balancer.load_balancer_ip
}

output "redis_host" {
  value = module.memorystore.redis_host
}

output "wif_provider" {
  description = "Workload Identity Provider for GitHub Actions"
  value       = module.github_oidc.workload_identity_provider
}

output "wif_service_account" {
  description = "Service Account for GitHub Actions"
  value       = module.github_oidc.service_account_email
}
