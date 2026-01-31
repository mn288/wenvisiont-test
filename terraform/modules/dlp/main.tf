variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
}

resource "google_data_loss_prevention_inspect_template" "basic_pii" {
  parent       = "projects/${var.project_id}/locations/${var.region}"
  description  = "Inspect template for basic PII (Email, Phone, Credit Card)"
  display_name = "basic-pii-inspect"

  inspect_config {
    info_types {
      name = "EMAIL_ADDRESS"
    }
    info_types {
      name = "PHONE_NUMBER"
    }
    info_types {
      name = "CREDIT_CARD_NUMBER"
    }
    info_types {
      name = "IBAN_CODE"
    }
    info_types {
      name = "PERSON_NAME"
    }

    min_likelihood = "POSSIBLE"
  }
}

resource "google_data_loss_prevention_deidentify_template" "masking" {
  parent       = "projects/${var.project_id}/locations/${var.region}"
  description  = "De-identify template using character masking"
  display_name = "basic-pii-masking"

  deidentify_config {
    info_type_transformations {
      transformations {
        info_types {
          name = "EMAIL_ADDRESS"
        }
        info_types {
          name = "PHONE_NUMBER"
        }
        info_types {
          name = "CREDIT_CARD_NUMBER"
        }
        info_types {
          name = "IBAN_CODE"
        }

        primitive_transformation {
          character_mask_config {
            masking_character = "*"
            number_to_mask    = 0
            reverse_order     = false
          }
        }
      }

      transformations {
        info_types {
          name = "PERSON_NAME"
        }
        primitive_transformation {
          replace_config {
            new_value {
              string_value = "[PERSON_NAME]"
            }
          }
        }
      }
    }
  }
}

output "inspect_template_name" {
  value = google_data_loss_prevention_inspect_template.basic_pii.name
}

output "deidentify_template_name" {
  value = google_data_loss_prevention_deidentify_template.masking.name
}
