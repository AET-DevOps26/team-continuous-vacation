output "vm_public_ip" {
  description = "Public IP address of the VM"
  value       = azurerm_public_ip.main.ip_address
}

output "vm_admin_username" {
  description = "Admin username for SSH"
  value       = var.admin_username
}

output "ssh_command" {
  description = "SSH command to connect to VM"
  value       = "ssh ${var.admin_username}@${azurerm_public_ip.main.ip_address}"
}
