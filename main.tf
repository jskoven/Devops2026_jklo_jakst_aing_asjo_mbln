# boilerplate telling terraform to download the digitalocean provider plugin
terraform {
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
  }
}

# this variable gets auto-filled by TF_VAR bash in the secrets file.
variable "do_token" {}
provider "digitalocean" { token = var.do_token }

# uploading our generated ssh key to digitalocean
resource "digitalocean_ssh_key" "minitwit_key" {
  name       = "minitwit-terraform-key"
  public_key = file("./ssh_key/terraform.pub")
}

# Database Droplet
resource "digitalocean_droplet" "db" {
  image    = "ubuntu-22-04-x64"
  name     = "minitwit-postgres"
  region   = "fra1"
  size     = "s-1vcpu-1gb" # small boy because it only runs postgres
  ssh_keys = [digitalocean_ssh_key.minitwit_key.id]

  provisioner "remote-exec" {
    inline = [
      "export DEBIAN_FRONTEND=noninteractive",
      "sleep 5",
      # loop forever until ubuntu stops doing background updates and releases the lock
      "until sudo apt-get update -y; do echo 'Waiting for apt lock...'; sleep 5; done",
      "until sudo apt-get install -y docker.io; do echo 'Waiting for apt lock...'; sleep 5; done",
      # spin up the actual database container
      "sudo docker run -d --name postgres -e POSTGRES_USER=minitwit_admin -e POSTGRES_PASSWORD=12345 -e POSTGRES_DB=minitwit -p 5432:5432 --restart always postgres:15"
    ]

    connection {
      type        = "ssh"
      user        = "root"
      private_key = file("./ssh_key/terraform")
      host        = self.ipv4_address
    }
  }
}

# Manager Droplet
resource "digitalocean_droplet" "manager" {
  image    = "ubuntu-22-04-x64"
  name     = "minitwit-manager"
  region   = "fra1"
  size     = "s-2vcpu-4gb"
  ssh_keys = [digitalocean_ssh_key.minitwit_key.id]

  provisioner "remote-exec" {
    inline = [
      "export DEBIAN_FRONTEND=noninteractive",
      "sleep 5",
      "until sudo apt-get update -y; do echo 'Waiting for apt lock...'; sleep 5; done",
      "until sudo apt-get install -y docker.io; do echo 'Waiting for apt lock...'; sleep 5; done",
      # initialize the swarm cluster but force it to advertise on the private network ip interface
      "sudo docker swarm init --advertise-addr ${self.ipv4_address_private}"
    ]

    connection {
      type        = "ssh"
      user        = "root"
      private_key = file("./ssh_key/terraform")
      host        = self.ipv4_address
    }
  }
}

# Worker Droplet
resource "digitalocean_droplet" "worker" {
  image    = "ubuntu-22-04-x64"
  name     = "minitwit-worker"
  region   = "fra1"
  size     = "s-1vcpu-2gb" # medium boy
  ssh_keys = [digitalocean_ssh_key.minitwit_key.id]

  provisioner "remote-exec" {
    inline = [
      "export DEBIAN_FRONTEND=noninteractive",
      "sleep 5",
      "until sudo apt-get update -y; do echo 'Waiting for apt lock...'; sleep 5; done",
      "until sudo apt-get install -y docker.io; do echo 'Waiting for apt lock...'; sleep 5; done"
      # we dont join the swarm here anymore, the bash script does it, couldnt make it work via terraform
    ]

    connection {
      type        = "ssh"
      user        = "root"
      private_key = file("./ssh_key/terraform")
      host        = self.ipv4_address
    }
  }
}

# Firewall config
resource "digitalocean_firewall" "minitwit_firewall" {
  name        = "minitwit-cluster-firewall"
  droplet_ids = [digitalocean_droplet.manager.id, digitalocean_droplet.worker.id, digitalocean_droplet.db.id]

  # allow literally any TCP traffic to hit any port from anywhere. yolo
  inbound_rule {
    protocol         = "tcp"
    port_range       = "1-65535"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # allow all inbound UDP traffic for overlay networks
  inbound_rule {
    protocol         = "udp"
    port_range       = "1-65535"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # allow all outbound TCP traffic so the nodes can actually talk back to us and pull dockerhub images
  outbound_rule {
    protocol              = "tcp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  # allow all outbound UDP
  outbound_rule {
    protocol              = "udp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}

# output the IPs into the local terminal so our deploy bash script can read them
output "manager_ip"         { value = digitalocean_droplet.manager.ipv4_address }
output "manager_private_ip" { value = digitalocean_droplet.manager.ipv4_address_private }
output "worker_ip"          { value = digitalocean_droplet.worker.ipv4_address }
output "db_private_ip"      { value = digitalocean_droplet.db.ipv4_address_private }