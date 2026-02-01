# AWP Sovereign Infrastructure: Zero-Trust Enclave

This Terraform configuration provisions the **Physical Architecture** for the Agentic Workflow Platform (AWP), implementing a **Zero-Trust Serverless Enclave** on Google Cloud Platform (GCP).

## Architecture Overview

The core compute engine is **Confidential GKE Autopilot** running in `europe-west9` (Sovereign Region). The architecture is designed to strictly control ingress, egress, and data residency.

### Key Components

| Component | Module | Description |
|-----------|--------|-------------|
| **Compute** | `gke_autopilot` | GKE Autopilot Cluster with **Confidential Nodes** (AMD SEV-SNP) enabled for hardware-level encryption of data-in-use. |
| **Perimeter** | `vpc_service_controls` | Defines the Service Perimeter, restricting data movement for sensitive APIs (BigQuery, Vertex AI, Storage) to within the project. |
| **Egress** | `cloud_nat` | strictly controlled egress via a static IP (whitelisted on external SaaS) for private GKE nodes. |
| **Ingress** | `load_balancer` | Provisions specific **Static IPs** and **Managed SSL Certificates** consumed by the GKE Ingress Controller. |
| **Security** | `cloud_armor` | Edge security policy (WAF) applied to the Ingress to filter traffic before it hits the cluster. |
| **Identity** | `iap` | **Identity-Aware Proxy** configuration (OAuth Brand/Client) for precise user authentication and identity propagation. |
| **IAM** | `iam` | **Workload Identity** bindings, allowing Kubernetes Service Accounts to impersonate Google Service Accounts (removing the need for key files). |

## Module Graph

```mermaid
graph TD
    User((User)) -->|HTTPS| GLB[Global Load Balancer]
    GLB -->|Check| CA[Cloud Armor (WAF)]
    GLB -->|Auth| IAP[Identity-Aware Proxy]
    GLB -->|Routing| GKE[Confidential GKE Autopilot]
    
    subgraph "VPC Service Control Perimeter"
        GKE -->|Workload Identity| Vertex[Vertex AI]
        GKE -->|Private IP| SQL[Cloud SQL]
        GKE -->|Private IP| BQ[BigQuery]
    end
    
    GKE -->|Egress| NAT[Cloud NAT]
    NAT -->|Static IP| Ext[External SaaS]
```

## Prerequisites

1.  **GCP Project**: A correctly configured project with billing enabled.
2.  **Terraform**: v1.5+.
3.  **GAuth**: Authenticated via `gcloud auth application-default login`.

## Usage

1.  **Initialize**:
    ```bash
    terraform init
    ```

2.  **Plan**:
    ```bash
    terraform plan -var="project_id=your-project-id"
    ```

3.  **Apply**:
    ```bash
    terraform apply -var="project_id=your-project-id"
    ```

## Manual Configuration Required (IAP)

Due to the deprecation of IAP Terraform resources, you must configure Identity-Aware Proxy manually:

1.  **Create OAuth Client**:
    *   Go to **GCP Console > APIs & Services > Credentials**.
    *   Create Credentials > OAuth Client ID > Web Application.
    *   Name it "IAP Client".
    *   Copy the `Client ID` and `Client Secret`.

2.  **Create Kubernetes Secret**:
    ```bash
    kubectl create secret generic iap-secret \
      --from-literal=client_id=YOUR_CLIENT_ID \
      --from-literal=client_secret=YOUR_CLIENT_SECRET
    ```

3.  **Backend Configuration**:
    *   Ensure your `BackendConfig` references this secret.
    *   Backend Verification: The backend service validates the `x-goog-iap-jwt-assertion` header. Ensure the `IAP_AUDIENCE` (Client ID) is provided to the backend via environment variable if strict validation is enabled.

## Post-Provisioning (Kubernetes)

After Terraform application, you must configure your Kubernetes manifests to reference the created resources:

*   **Ingress**: Annotation `kubernetes.io/ingress.global-static-ip-name` -> Output `ingress_static_ip_name`.
*   **SSL**: Annotation `networking.gke.io/managed-certificates` -> Output `ingress_managed_cert_name`.
*   **WAF**: `BackendConfig` reference -> Output `security_policy_name`.
*   **Workload Identity**: ServiceAccount annotation `iam.gke.io/gcp-service-account` -> Output `workload_identity_sa`.
