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

module "iam" {
  source                 = "./modules/iam"
  project_id             = var.project_id
  github_service_account = module.github_oidc.service_account_email
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
  length           = 16
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

module "security" {
  source      = "./modules/security"
  project_id  = var.project_id
  db_password = random_password.db_password.result
}

module "database" {
  source       = "./modules/database"
  project_id   = var.project_id
  region       = var.region
  vpc_id       = module.networking.vpc_id
  db_password  = random_password.db_password.result
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
  source              = "./modules/vertex_ai"
  project_id          = var.project_id
  region              = var.region
  vpc_id              = module.networking.vpc_id
  encryption_key_name = module.kms.vertex_key_id

  depends_on = [module.networking, module.kms]
}

module "gke_autopilot" {
  source      = "./modules/gke_autopilot"
  project_id  = var.project_id
  region      = var.region
  vpc_name    = module.networking.vpc_name
  subnet_name = module.networking.subnet_name

  depends_on = [module.networking]
}

# -------------------------------------------------------------------------
# Phase 3 Hardening: Security & Ingress Support
# -------------------------------------------------------------------------
module "cloud_armor" {
  source     = "./modules/cloud_armor"
  project_id = var.project_id
}

module "load_balancer" {
  source      = "./modules/load_balancer"
  project_id  = var.project_id
  domain_name = var.domain_name
}

# -------------------------------------------------------------------------
# Phase 3 Hardening: Least-Privilege IAM Bindings
# -------------------------------------------------------------------------


# -------------------------------------------------------------------------
# CI/CD: Workload Identity Federation
# -------------------------------------------------------------------------
module "github_oidc" {
  source      = "./modules/github_oidc"
  project_id  = var.project_id
  github_repo = var.github_repo
}

# =========================================================================
# AWP AGENTIC WORKFLOW PLATFORM - PHASE 4 GCP SOVEREIGN INFRASTRUCTURE
# =========================================================================

# -------------------------------------------------------------------------
# Cloud NAT: Controlled Egress with Static IP
# -------------------------------------------------------------------------
module "cloud_nat" {
  source     = "./modules/cloud_nat"
  project_id = var.project_id
  region     = var.region
  vpc_id     = module.networking.vpc_id
  vpc_name   = module.networking.vpc_name

  # Optional: Enable secondary NAT IP for high throughput
  enable_secondary_nat_ip = var.enable_high_throughput_nat
  nat_log_filter          = var.nat_log_filter

  depends_on = [module.networking]
}

# -------------------------------------------------------------------------
# Cloud Tasks: Async Resilience for Long-Running Actions
# -------------------------------------------------------------------------
module "cloud_tasks" {
  source     = "./modules/cloud_tasks"
  project_id = var.project_id
  region     = var.region

  depends_on = [module.apis]
}



# -------------------------------------------------------------------------
# VPC Service Controls: Zero-Trust Perimeter (Optional)
# -------------------------------------------------------------------------
module "vpc_service_controls" {
  count = var.enable_vpc_service_controls ? 1 : 0

  source            = "./modules/vpc_service_controls"
  project_id        = var.project_id
  project_number    = var.project_number
  access_policy_id  = var.access_policy_id
  org_id            = var.org_id
  allowed_ip_ranges = var.vpc_sc_allowed_ip_ranges
  dry_run_mode      = var.vpc_sc_dry_run_mode

  depends_on = [module.apis]
}

# -------------------------------------------------------------------------
# Vertex AI RAG Engine: Corporate Knowledge Retrieval
# -------------------------------------------------------------------------
module "vertex_rag_engine" {
  source     = "./modules/vertex_rag_engine"
  project_id = var.project_id
  region     = var.region
  vpc_id     = module.networking.vpc_id

  depends_on = [module.networking, module.apis]
}

# =========================================================================
# OUTPUTS
# =========================================================================

output "cluster_endpoint" {
  value = module.gke_autopilot.cluster_endpoint
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

# --- AWP GCP Outputs ---

output "nat_ip_address" {
  description = "Cloud NAT static IP address for whitelisting on external services"
  value       = module.cloud_nat.nat_ip_address
}

output "cloud_tasks_queues" {
  description = "Cloud Tasks queue names for agent execution"
  value       = module.cloud_tasks.all_queue_names
}

output "vertex_rag_vector_index" {
  description = "Vertex AI RAG Vector Index ID"
  value       = module.vertex_rag_engine.vector_index_id
}

output "vertex_search_engine" {
  description = "Vertex AI Search Engine ID"
  value       = module.vertex_rag_engine.search_engine_id
}

output "dlp_inspect_template" {
  description = "DLP Inspect Template name for PII detection"
  value       = module.dlp.inspect_template_name
}

output "dlp_deidentify_template" {
  description = "DLP De-identify Template name for PII masking"
  value       = module.dlp.deidentify_template_name
}

# --- Ingress Resources ---

output "ingress_static_ip_name" {
  description = "Static IP Name for K8s Ingress annotation"
  value       = module.load_balancer.ip_name
}

output "ingress_managed_cert_name" {
  description = "Managed Cert Name for K8s Ingress annotation"
  value       = module.load_balancer.certificate_name
}

output "security_policy_name" {
  description = "Cloud Armor Policy Name for BackendConfig"
  value       = module.cloud_armor.policy_name
}

output "workload_identity_sa" {
  description = "GKE Workload Identity Service Account"
  value       = module.iam.backend_sa_email
}
