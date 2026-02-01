variable "project_id" {
  type = string
}

resource "google_compute_security_policy" "policy" {
  name    = "antigravity-security-policy"
  project = var.project_id

  # Default rule: Allow all (to be hardened)
  rule {
    action   = "allow"
    priority = "2147483647"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    description = "Default rule, allow all"
  }

  # Example: Block specific IP (Placeholder)
  # rule {
  #   action   = "deny(403)"
  #   priority = "1000"
  #   match {
  #     versioned_expr = "SRC_IPS_V1"
  #     config {
  #       src_ip_ranges = ["1.2.3.4/32"]
  #     }
  #   }
  #   description = "Deny malicious IP"
  # }
}

output "policy_name" {
  value = google_compute_security_policy.policy.name
}
