variable "subscription_id" {
  description = "Azure subscription ID"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the Azure resource group"
  type        = string
  default     = "triptailor-rg"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "polandcentral"
}

variable "vm_size" {
  description = "Azure VM size"
  type        = string
  default     = "Standard_B2ats_v2"
}

variable "admin_username" {
  description = "VM admin username"
  type        = string
  default     = "tripadmin"
}

variable "ssh_public_key_path" {
  description = "Path to SSH public key for VM access"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "monthly_budget_amount" {
  description = "Monthly Azure budget amount. Set this to current credits minus the remaining-credit buffer you want to preserve."
  type        = number
  default     = 95

  validation {
    condition     = var.monthly_budget_amount >= 0
    error_message = "monthly_budget_amount must be zero or greater."
  }
}

variable "monthly_budget_start_date" {
  description = "Budget start date in RFC3339 format. Must be the first day of the current billing month, for example 2026-07-01T00:00:00Z."
  type        = string
  default     = "2026-07-01T00:00:00Z"
}

variable "monthly_budget_end_date" {
  description = "Budget end date in RFC3339 format."
  type        = string
  default     = "2027-07-01T00:00:00Z"
}

variable "budget_alert_email_addresses" {
  description = "Comma-separated email addresses for Azure Cost Management budget alerts. Leave empty to skip creating budget alerts."
  type        = string
  default     = ""
}
