output "vpc_id" {
  value = google_compute_network.vpc.id
}

output "vpc_name" {
  value = google_compute_network.vpc.name
}

output "subnet_id" {
  value = google_compute_subnetwork.subnet.id
}

output "subnet_name" {
  value = google_compute_subnetwork.subnet.name
}

output "private_vpc_connection" {
  value = google_service_networking_connection.private_vpc_connection
}

output "psc_endpoint_address" {
  description = "Private Service Connect endpoint IP address"
  value       = google_compute_global_address.psc_address.address
}

output "psc_endpoint_id" {
  description = "Private Service Connect endpoint ID"
  value       = google_compute_global_address.psc_address.id
}
