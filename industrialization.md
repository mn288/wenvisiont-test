# Industrialization Plan: CAC40 Financial Agentic Platform

**Status**: ✅ **COMPLETED**
**Date**: 2026-01-08
**Target**: Production Readiness (Audit, Security, Reliability)

## Executive Summary

A comprehensive deep-dive code audit was conducted on the entire codebase (Backend, Frontend, Infrastructure). The system currently functions as a **High-Fidelity Prototype** but fails significant **Financial Compliance** and **Production Readiness** checks.

## 1. Compliance & Security (Verified Gaps)

### 1.1. Comprehensive PII Masking

- **Status**: **FAILED**.
- **Audit Findings**:
  - `mask_pii` is implemented (`src/utils/pii.py`) and used on **Input** (`nodes.py:32`).
  - **GAP**: Intermediate tool outputs and Final QA responses are **NOT masked**.
  - **Risk**: PII (Names, Phone Numbers) leak into `step_logs` database table.

### 1.2. Audit Trail & Explainability

- **Status**: **PARTIAL**.
- **Audit Findings**:
  - `step_logs` table has a `metadata_` column (Schema Correct).
  - **GAP**: The application logic (`nodes.py`) **never populates** this column with LLM metadata (Token usage, Model Name, Finish Reason).
  - **Risk**: Impossible to prove "Temperature 0" or audit costs per transaction.

### 1.3. RBAC (Access Control)

- **Status**: **FAILED**.
- **Audit Findings**:
  - Middleware correctly extracts `X-Tenant-ID` and `X-Role`.
  - **GAP**: Critical endpoints in `src/api/v1/endpoints/agents.py` (deployment, deletion) have **NO permission checks**. Any authenticated user can delete any agent.

## 2. Architecture & Persistence (Verified Gaps)

### 2.1. Agent Persistence

- **Status**: **File-System Dependent**.
- **Audit Findings**:
  - Agents are loaded/saved to YAML files (`backend/config/agents/`).
  - **GAP**: `ArchitectService` generates JSON, but there is **NO Database Table** for Agents.
  - **Impact**: Cannot manage agents dynamically in a stateless container environment (Cloud Run). Changes are lost on redeploy if not committed to Git.

### 2.2. Frontend "Smoke & Mirrors"

- **Status**: **Mock Data**.
- **Audit Findings**:
  - `StudioDashboard` (`page.tsx`) hardcodes metrics:
    - Compliance Score: `98%` (Hardcoded)
    - Total Invocations: `1.2k` (Hardcoded)
  - **GAP**: No API integration for real system stats.
  - **GAP**: No UI exists for **API Key Management** (Generate/Rotate Key).

## 3. Infrastructure (Terraform)

- **Status**: **Incomplete**.
- **Audit Findings**:
  - `modules/networking`: correctly implements Private Service Access (SQL).
  - `modules/security`: **MISSING Cloud Armor** (WAF) configuration. **MISSING IAM Bindings** for service accounts.
  - **Risk**: The platform is currently exposed without WAF protection.

## 4. MCP Integration (Verified Gaps)

### 4.1. RBAC on MCP Endpoints

- **Status**: **FAILED**.
- **Audit Findings**:
  - `/mcp/servers` POST and DELETE endpoints have **NO permission checks**.
  - **Risk**: Any authenticated user can add/delete MCP server configurations.

### 4.2. MCP Server List

- **Status**: **FAILED**.
- **Audit Findings**:
  - `/agents/mcp/servers` returns **hardcoded** `["local", "fastmcp"]`.
  - **GAP**: Does not query DB for actual available servers.

### 4.3. Per-Tenant MCP Access Control

- **Status**: **MISSING**.
- **Audit Findings**:
  - No mechanism to restrict which MCP servers a tenant/org can use.
  - **GAP**: `generate_agent()` has placeholder comment but no validation.
  - **Risk**: Tenants can access any registered MCP server regardless of permissions.

## 5. Remediation Plan

### Phase 1: immediate Fixes (Code Based)

1.  **PII Output Masking**: Apply `mask_pii` to all `log_step` calls in `nodes.py`.
2.  **Metadata Logging**: Capture and store LLM usage stats in `step_logs`.
3.  **RBAC Enforcement**: Add `depends(require_role("ADMIN"))` to sensitive endpoints.

### Phase 2: Architecture Lift (Data Layer)

1.  **Agent Database**: Create `superagents` table. Migrating YAML -> DB.
2.  **Stats API**: Implement `GET /stats` to replace frontend mocks.

### Phase 3: Infrastructure Hardening

1.  **Cloud Armor**: Add Terraform module for WAF policies.
2.  **IAM Lockdown**: Implement least-privilege service accounts.

### Phase 4: MCP Industrialization

1.  **RBAC on MCP Endpoints**: Add `Depends(require_role("ADMIN"))` to `/mcp/servers` POST/DELETE.
2.  **Fix Server List API**: Query DB in `/agents/mcp/servers` instead of hardcoded list.
3.  **Per-Tenant Access Control**: Add `allowed_mcp_servers` to tenant config, validate in agent endpoints.

## 6. Implementation Roadmap (Immediate)

We will proceed with **Phase 1 (Immediate Fixes)** as defined in `implementation_plan.md`. This addresses the most critical compliance risks (Data Leakage & Audit).
