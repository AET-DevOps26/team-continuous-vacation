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

Use the same Terraform state storage account described in the GitHub Actions section below.

> **Local-only testing:** the `backend "azurerm"` block in `main.tf` points at the shared remote state (`continousvacationstorage` / `triptailor-tfstate-rg`). That storage account lives in the team subscription, so if you are logged into a different subscription (e.g. a personal *Azure for Students* one) `terraform init` fails with `403 AuthorizationPermissionMismatch` or `ResourceGroupNotFound`. To provision against your own subscription, comment out the backend block so Terraform uses local state, then `terraform init -reconfigure`:
>
> ```hcl
> terraform {
>   # comment out this block to try it locally
>   # backend "azurerm" {
>   #   resource_group_name  = "triptailor-tfstate-rg"
>   #   storage_account_name = "continousvacationstorage"
>   #   container_name       = "tfstate"
>   #   key                  = "triptailor.tfstate"
>   #   use_azuread_auth     = true
>   # }
>   ...
> }
> ```
>
> Do **not** commit this change — the backend block must stay enabled for CI and shared deployments.

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

If you are moving to a new Azure account because the old account ran out of credit, do the following in the new account before running GitHub Actions:

1. Select the new subscription with `az account set --subscription "<new-subscription-id>"`.
2. Create a new app registration/service principal with the commands above, or reuse an existing one only if it belongs to the new tenant and subscription.
3. Add the GitHub OIDC federated credential below. Keep the `subject` value aligned with the GitHub environment name `azure`.
4. Create a new Terraform state resource group, storage account, and `tfstate` container in the new subscription.
5. Update the `backend "azurerm"` block in `infrastructure/terraform/main.tf` if the new storage account or state resource group names differ from `triptailor-tfstate-rg` and `continousvacationstorage`.
6. Grant `Storage Blob Data Contributor` on the state storage account to both your local user and the GitHub Actions service principal.
7. Create or copy an SSH key pair for the VM. If the private key was exposed to the old account or old workflow runs, generate a fresh pair.
8. Create or select the Azure OpenAI/Cognitive Services resource for `genai-service`, create a model deployment, and copy its endpoint and API key.
9. In Cost Management, check the current credit balance. Set the monthly budget amount to `current balance - 5`; for example, use `95` if the new account has `100 USD` available.

Add a federated credential for your repository and the `azure` GitHub environment used by `.github/workflows/azure-vm-deploy.yaml`.

```bash
az ad app federated-credential create \
  --id "$APP_ID" \
  --parameters '{
    "name": "github-environment-azure",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:AET-DevOps26/team-continuous-vacation:environment:azure",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

If you also want to authenticate jobs that do not use a GitHub environment, add a second federated credential with the branch subject `repo:AET-DevOps26/team-continuous-vacation:ref:refs/heads/main`.

Create a storage account and blob container for Terraform remote state. The storage account name must be globally unique and contain only lowercase letters and numbers.

```bash
az group create --name triptailor-tfstate-rg --location polandcentral

az storage account create \
  --name "triptfstate354f93b6" \
  --resource-group triptailor-tfstate-rg \
  --location polandcentral \
  --sku Standard_LRS \
  --kind StorageV2 \
  --allow-blob-public-access false

az storage container create \
  --name tfstate \
  --account-name "triptfstate354f93b6" \
  --auth-mode login
```

Give your local Azure CLI user access to the Terraform state container. This is required for local commands such as `terraform init`, because the backend uses Azure AD authentication and needs blob data-plane permissions.

```bash
STORAGE_SCOPE=$(az storage account show \
  --name "triptfstate354f93b6" \
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
  --name "triptfstate354f93b6" \
  --resource-group triptailor-tfstate-rg \
  --query id -o tsv)

SP_OBJECT_ID=$(az ad sp show --id "$APP_ID" --query id -o tsv)

az role assignment create \
  --assignee-object-id "$SP_OBJECT_ID" \
  --assignee-principal-type ServicePrincipal \
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
| `AZURE_VM_SIZE` | `Standard_B2ats_v2` |
| `AZURE_VM_ADMIN_USERNAME` | `tripadmin` |
| `AZURE_LLM_BASE_URL` | Azure OpenAI endpoint URL |
| `AZURE_MONTHLY_BUDGET_AMOUNT` | `95` |
| `AZURE_MONTHLY_BUDGET_START_DATE` | `2026-07-01T00:00:00Z` |
| `AZURE_MONTHLY_BUDGET_END_DATE` | `2027-07-01T00:00:00Z` |
| `AZURE_BUDGET_ALERT_EMAIL_ADDRESSES` | Empty, which disables budget alert creation |

The default `Standard_B2ats_v2` in `polandcentral` is chosen because Azure reported smaller burstable sizes as unavailable for this student subscription in the checked EU regions, while `Standard_B2ats_v2` was available in `polandcentral`. If this SKU becomes unavailable, check available burstable sizes with `az vm list-skus --location polandcentral --size Standard_B --all --output table` and set `location`/`vm_size` in `terraform.tfvars` or the `AZURE_LOCATION`/`AZURE_VM_SIZE` GitHub repository variables to the cheapest available option.

### Cost alert setup

Terraform creates an Azure Cost Management monthly subscription budget when `AZURE_BUDGET_ALERT_EMAIL_ADDRESSES` is non-empty. It also creates an Azure Monitor action group named `triptailor-cost-alerts`.

Azure budgets alert on cost thresholds, not on live remaining credit for every subscription type. To get an alert when roughly `5 USD` remains, set:

```text
AZURE_MONTHLY_BUDGET_AMOUNT = <current-credit-balance> - 5
AZURE_BUDGET_ALERT_EMAIL_ADDRESSES = "person1@example.com,person2@example.com"
```

The budget sends both actual-cost and forecasted-cost notifications at `100%` of that amount. Cost Management data is delayed, usually by several hours, so keep the Azure spending limit enabled for student/free-credit subscriptions when possible. Microsoft also sends automatic credit alerts for Enterprise Agreement Azure Prepayment at 90% and 100%, but those credit alerts are not available on every Azure offer type.

When the billing month changes, update `AZURE_MONTHLY_BUDGET_START_DATE` to the first day of the active billing month, for example `2026-08-01T00:00:00Z`. If the new account starts with a different credit amount, update `AZURE_MONTHLY_BUDGET_AMOUNT` before rerunning the deployment.

### GitHub migration checklist

In GitHub, update the `azure` environment or repository settings after the new Azure account is prepared:

1. Replace `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, and `AZURE_SUBSCRIPTION_ID` with values from the new account.
2. Replace `AZURE_VM_SSH_PUBLIC_KEY` and `AZURE_VM_SSH_PRIVATE_KEY` if you generated a new VM key pair.
3. Replace `AZURE_LLM_API_KEY` and `AZURE_LLM_BASE_URL` with the new Azure OpenAI resource values.
4. Set `AZURE_BUDGET_ALERT_EMAIL_ADDRESSES` to the team recipients.
5. Set `AZURE_MONTHLY_BUDGET_AMOUNT` to the new current credit balance minus `5`.
6. Set `AZURE_MONTHLY_BUDGET_START_DATE` and `AZURE_MONTHLY_BUDGET_END_DATE`.
7. Trigger `Deploy to Azure VM` manually with `terraform_action=apply`.

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
| Gateway    | `http://<VM_IP>:3000` |

The gateway is the single public entrypoint. It routes `/` to the frontend and `/api/*` to the backend. Persistence, GenAI, and Postgres are internal services.

## Teardown

```bash
cd ../terraform
terraform destroy
```

## Files (gitignored, never commit)

- `terraform/terraform.tfvars` — contains subscription ID
- `ansible/vars.yml` — contains API keys
- `ansible/inventory.ini` — contains VM IP
