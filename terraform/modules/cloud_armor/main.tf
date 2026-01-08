# Cloud Armor Security Policy - WAF for Cloud Run

# External IP for Load Balancer (required for Cloud Armor)
resource "google_compute_global_address" "default" {
  name = "global-static-ip"
}

# Cloud Armor Security Policy
resource "google_compute_security_policy" "waf_policy" {
  name        = "agentic-platform-waf"
  description = "Cloud Armor WAF policy for CAC40 financial platform"

  # --- Default Rule: Allow ---
  rule {
    action   = "allow"
    priority = 2147483647 # Lowest priority (default rule)
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    description = "Default allow rule"
  }

  # --- OWASP Core Rule Set: SQL Injection ---
  rule {
    action   = "deny(403)"
    priority = 1000
    match {
      expr {
        expression = "evaluatePreconfiguredWaf('sqli-v33-stable', {'sensitivity': 1})"
      }
    }
    description = "Block SQL Injection attacks (OWASP CRS)"
  }

  # --- OWASP Core Rule Set: XSS ---
  rule {
    action   = "deny(403)"
    priority = 1001
    match {
      expr {
        expression = "evaluatePreconfiguredWaf('xss-v33-stable', {'sensitivity': 1})"
      }
    }
    description = "Block XSS attacks (OWASP CRS)"
  }

  # --- OWASP Core Rule Set: LFI ---
  rule {
    action   = "deny(403)"
    priority = 1002
    match {
      expr {
        expression = "evaluatePreconfiguredWaf('lfi-v33-stable', {'sensitivity': 1})"
      }
    }
    description = "Block Local File Inclusion attacks"
  }

  # --- OWASP Core Rule Set: RCE ---
  rule {
    action   = "deny(403)"
    priority = 1003
    match {
      expr {
        expression = "evaluatePreconfiguredWaf('rce-v33-stable', {'sensitivity': 1})"
      }
    }
    description = "Block Remote Code Execution attacks"
  }

  # --- Rate Limiting (Throttle) ---
  rule {
    action   = "throttle"
    priority = 2000
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    rate_limit_options {
      conform_action   = "allow"
      exceed_action    = "deny(429)"
      rate_limit_threshold {
        count = 100
        interval_sec = 60
      }
    }
    description = "Rate limit: 100 requests per minute per IP"
  }

  # --- Geo Blocking (Optional - Example: Block specific regions) ---
  # Uncomment and configure as needed for compliance
  # rule {
  #   action   = "deny(403)"
  #   priority = 500
  #   match {
  #     expr {
  #       expression = "origin.region_code == 'RU' || origin.region_code == 'CN'"
  #     }
  #   }
  #   description = "Block traffic from specific geo regions"
  # }
}

output "waf_policy_id" {
  value       = google_compute_security_policy.waf_policy.id
  description = "Cloud Armor WAF Policy ID"
}

output "global_static_ip" {
  value       = google_compute_global_address.default.address
  description = "Global Static IP for Load Balancer"
}
