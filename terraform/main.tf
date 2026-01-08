module "networking" {
  source      = "./modules/networking"
  project_id  = var.project_id
  region      = var.region
  subnet_cidr = "10.0.0.0/24"
}

module "security" {
  source      = "./modules/security"
  project_id  = var.project_id
  db_password = var.db_password
}

module "database" {
  source      = "./modules/database"
  project_id  = var.project_id
  region      = var.region
  vpc_id      = module.networking.vpc_id
  db_password = var.db_password
  
  depends_on = [module.networking]
}

module "compute" {
  source         = "./modules/compute"
  project_id     = var.project_id
  region         = var.region
  vpc_name       = module.networking.vpc_name
  subnet_name    = module.networking.subnet_name
  backend_image  = var.backend_image
  frontend_image = var.frontend_image
  
  # Construct Database URL from module outputs
  # postgresql+asyncpg://user:password@ip:5432/dbname
  database_url   = "postgresql+asyncpg://${module.database.db_user}:${var.db_password}@${module.database.instance_ip_address}:5432/${module.database.db_name}"
  
  depends_on = [module.database]
}

# -------------------------------------------------------------------------
# Phase 3 Hardening: Cloud Armor WAF
# -------------------------------------------------------------------------
module "cloud_armor" {
  source     = "./modules/cloud_armor"
  project_id = var.project_id
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
  enable_authenticated_invoker = false  # Set to true for production
  
  depends_on = [module.compute]
}

