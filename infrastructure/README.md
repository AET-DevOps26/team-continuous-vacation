# Infrastructure

Terraform provisions an Azure VM. Ansible deploys the app via Docker Compose.

## Prerequisites

- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.0
- [Ansible](https://docs.ansible.com/ansible/latest/installation_guide/) >= 2.12
- Azure CLI (`az login` done)
- SSH key pair (e.g. `~/.ssh/id_ed25519`)

## 1. Provision VM with Terraform

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:
- `subscription_id` — your Azure subscription ID (`az account show --query id -o tsv`)
- `ssh_public_key_path` — path to your public key

```bash
terraform init
terraform apply
```

Note the `vm_public_ip` from the output.

## 2. Deploy with Ansible

```bash
cd ../ansible
```

Edit `inventory.ini`:
- Replace `<REPLACE_WITH_VM_IP>` with the IP from step 1

Create secrets file:
```bash
cp vars.yml.example vars.yml
```

Edit `vars.yml`:
- `azure_llm_api_key` — Azure OpenAI API key
- `azure_llm_base_url` — Azure OpenAI endpoint

Deploy:
```bash
ansible-playbook -i inventory.ini playbook.yml -e @vars.yml
```

## 3. Access

| Service    | URL                  |
|------------|----------------------|
| Frontend   | `http://<VM_IP>:3000` |
| Backend    | `http://<VM_IP>:8080` |
| Persistence| `http://<VM_IP>:8081` |

## Teardown

```bash
cd ../terraform
terraform destroy
```

## Files (gitignored, never commit)

- `terraform/terraform.tfvars` — contains subscription ID
- `ansible/vars.yml` — contains API keys
- `ansible/inventory.ini` — contains VM IP
