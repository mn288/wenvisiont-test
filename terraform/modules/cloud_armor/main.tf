

resource "google_compute_security_policy" "policy" {
  name = "${var.project_id}-security-policy"
  description = "Cloud Armor security policy with OWASP rules"

  # Default Rule: Deny All (Best practice, allowlist approach) or Allow All depending on risk profile.
  # For now, we allow all but filter attacks.
  rule {
    action   = "allow"
    priority = "2147483647"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    description = "Default rule, allow everything."
  }

  # OWASP Top 10 - SQL Injection
  rule {
    action   = "deny(403)"
    priority = "1000"
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('sqli-v33-stable')"
      }
    }
    description = "SQL Injection Protection"
  }

  # OWASP Top 10 - XSS
  rule {
    action   = "deny(403)"
    priority = "1001"
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('xss-v33-stable')"
      }
    }
    description = "XSS Protection"
  }
  
  # LFI/RFI
  rule {
    action   = "deny(403)"
    priority = "1002"
    match {
      expr {
       expression = "evaluatePreconfiguredExpr('lfi-v33-stable') || evaluatePreconfiguredExpr('rfi-v33-stable')"
      }
    }
    description = "LFI/RFI Protection"
  }
}

output "policy_id" {
  value = google_compute_security_policy.policy.id
}
