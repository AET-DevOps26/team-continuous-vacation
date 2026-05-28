# Infrastructure

Terraform provisions an Azure VM. Ansible deploys the app via Docker Compose.

## Prerequisites

- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.0
- [Ansible](https://docs.ansible.com/ansible/latest/installation_guide/) >= 2.12
- Azure CLI (`az login` done)
- SSH key pair (e.g. `~/.ssh/id_ed25519`)

## 1. Provision VM with Terraform

```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:
- `subscription_id` — your Azure subscription ID (`az account show --query id -o tsv`)
- `ssh_public_key_path` — path to your public key

Use the same Terraform state storage account described in the GitHub Actions section below:

```bash
terraform init
terraform apply
```

Note the `vm_public_ip` from the output.

## GitHub Actions Azure Deployment

The workflow `.github/workflows/azure-vm-deploy.yaml` provisions the VM with the Terraform configuration in `infrastructure/terraform`, then deploys the app with the existing Ansible playbook in `infrastructure/ansible`.

On pushes to `main`, it runs `terraform apply` and then `ansible-playbook`. It can also be started manually from the GitHub Actions tab. Manual runs can choose `apply`, `destroy`, and whether to skip the Ansible deployment after apply.

### Azure setup

Create a Microsoft Entra app registration and service principal for GitHub Actions. Use OpenID Connect instead of a client secret.

```bash
az login
az account set --subscription "<subscription-id>"

APP_ID=$(az ad app create --display-name "triptailor-github-actions" --query appId -o tsv)
az ad sp create --id "$APP_ID"

SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)

az role assignment create \
  --assignee "$APP_ID" \
  --role Contributor \
  --scope "/subscriptions/$SUBSCRIPTION_ID"
```

Add a federated credential for your repository. Replace `OWNER` and `REPO` with the GitHub organization/user and repository name.

```bash
az ad app federated-credential create \
  --id "$APP_ID" \
  --parameters '{
    "name": "github-main",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:AET-DevOps26/team-continuous-vacation:ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

Create a storage account and blob container for Terraform remote state. The storage account name must be globally unique and contain only lowercase letters and numbers.

```bash
az group create --name triptailor-tfstate-rg --location westeurope

az storage account create \
  --name "continousvacationstorage" \
  --resource-group triptailor-tfstate-rg \
  --location westeurope \
  --sku Standard_LRS \
  --kind StorageV2 \
  --allow-blob-public-access false

az storage container create \
  --name tfstate \
  --account-name "continousvacationstorage" \
  --auth-mode login
```

Give your local Azure CLI user access to the Terraform state container. This is required for local commands such as `terraform init`, because the backend uses Azure AD authentication and needs blob data-plane permissions.

```bash
STORAGE_SCOPE=$(az storage account show \
  --name "continousvacationstorage" \
  --resource-group triptailor-tfstate-rg \
  --query id -o tsv)

SIGNED_IN_USER_OBJECT_ID=$(az ad signed-in-user show --query id -o tsv)

az role assignment create \
  --assignee-object-id "$SIGNED_IN_USER_OBJECT_ID" \
  --assignee-principal-type User \
  --role "Storage Blob Data Contributor" \
  --scope "$STORAGE_SCOPE"
```

Give the GitHub Actions service principal the same access to the Terraform state container. This is required for the workflow to run `terraform init`, `plan`, and `apply`.

```bash
STORAGE_SCOPE=$(az storage account show \
  --name "continousvacationstorage" \
  --resource-group triptailor-tfstate-rg \
  --query id -o tsv)

az role assignment create \
  --assignee "$APP_ID" \
  --role "Storage Blob Data Contributor" \
  --scope "$STORAGE_SCOPE"
```

Create an SSH key pair for the VM deployment. The public key is passed to Terraform when the VM is created; the private key is used by Ansible to connect to the VM.

```bash
ssh-keygen -t ed25519 -C "triptailor-azure-vm" -f ./triptailor_azure_vm
```

### GitHub repository settings

Create a GitHub environment named `azure`. If you want deployment approval, add required reviewers to that environment.

Add these repository secrets:

| Secret | Value |
| --- | --- |
| `AZURE_CLIENT_ID` | App/client ID from `APP_ID` |
| `AZURE_TENANT_ID` | Azure tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID |
| `AZURE_VM_SSH_PUBLIC_KEY` | Contents of `triptailor_azure_vm.pub` |
| `AZURE_VM_SSH_PRIVATE_KEY` | Contents of `triptailor_azure_vm` |
| `AZURE_LLM_API_KEY` | Azure OpenAI API key for `genai-service` |

Add these optional repository secrets:

| Secret | Default |
| --- | --- |
| `POSTGRES_PASSWORD` | `trippassword` |
| `JWT_SECRET` | `dev-only-change-this-secret-to-at-least-32-bytes` |

Add these optional repository variables if you want values different from the Terraform defaults:

| Variable | Default |
| --- | --- |
| `AZURE_RESOURCE_GROUP` | `triptailor-rg` |
| `AZURE_LOCATION` | `polandcentral` |
| `AZURE_VM_SIZE` | `Standard_B2s_v2` |
| `AZURE_VM_ADMIN_USERNAME` | `tripadmin` |
| `AZURE_LLM_BASE_URL` | Azure OpenAI endpoint URL |

The default `Standard_B2s_v2` in `polandcentral` is chosen because Azure reported `Standard_B1s` and `Standard_B1ms` as unavailable for this student subscription in the checked EU regions, while `Standard_B2s_v2` was available in `polandcentral`. If this SKU becomes unavailable, check available burstable sizes with `az vm list-skus --location polandcentral --size Standard_B --all --output table` and set `location`/`vm_size` in `terraform.tfvars` or the `AZURE_LOCATION`/`AZURE_VM_SIZE` GitHub repository variables to the cheapest available option.

### Run the deployment

Push to `main`, or open GitHub Actions, choose `Deploy to Azure VM`, and run it manually with `terraform_action=apply`.

After it completes, the app is available at:

| Service | URL |
| --- | --- |
| Frontend | `http://<VM_IP>:3000` |
| Backend | `http://<VM_IP>:8080` |
| Persistence | `http://<VM_IP>:8081` |

Use the manual workflow option `terraform_action=destroy` to remove the Azure VM and related resources created by Terraform. The Terraform state storage account is intentionally not destroyed by this repo because it is the backend that stores state.

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
