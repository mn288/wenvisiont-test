# Infrastructure & Security Plan - CAC40 Compliance

## Overview

Deployment must be **Zero Trust**, **Auditable**, and **Private**.

## 1. Architecture (GCP)

### Compute

- **Cloud Run**:
  - Service: `agent-engine`.
  - Ingress: `Internal + Cloud Load Balancing` (or API Gateway).
  - Auth: `IAM` (Service-to-Service) + `API Keys` (External).
  - Scaling: Min: 0, Max: 100 (Auto-scaling).

### Storage

- **Cloud SQL (PostgreSQL)**:
  - Network: **Private IP Only** (VPC Peering).
  - Encryption: CMEK (Customer Managed Encryption Keys).
  - HA: Regional capability (High Availability).

### Network

- **VPC Connector**: Serverless Application Access to Private SQL.
- **Cloud Armor (WAF)**: Protect against DDoS/Bot attacks on the Exposure Gateway.

### API Gateway (The Front Door)

- **Product**: Google API Gateway or Apigee (if budget allows). We assume API Gateway for MVP.
- **Config**: `openapi.yaml`.
- **Security**: Validates API Key header `X-API-Key`.
- **Routing**: `/v1/invoke/{id}` -> Cloud Run.

## 2. Terraform Modules (`terraform/`)

### `modules/gateway/`

- Resources: `google_api_gateway_api`, `google_api_gateway_gateway`, `google_api_gateway_api_config`.

### `modules/database/`

- Update: Enable `private_network`. Remove Public IP.

### `modules/iam/`

- Define strict Service Accounts.
- `agent-engine-sa`: Can connect to SQL, Can log to Cloud Logging.
- `gateway-sa`: Can invoke Cloud Run.

## 3. CI/CD & Compliance

- **Pipeline**: GitHub Actions -> Artifact Registry -> Cloud Run.
- **Scanning**: Container Security Scanning (Trivy) before deploy.
- **Audit Logs**: Enable Data Access Logs for Cloud SQL and Cloud Run.

## Measurable Deliverables

- [ ] **Terraform Apply**: Successful creation of Private SQL and API Gateway.
- [ ] **Security Audit**: Verify `curl` to Cloud Run URL fails (403). Verify `curl` to Gateway with Key succeeds (200).
- [ ] **Compliance Report**: Document encryption and network isolation strategy.
