#!/bin/bash

# F1 Prediction Analytics Infrastructure Deployment Script
# This script handles the deployment of the Terraform infrastructure

set -e

# Default values
ENVIRONMENT="dev"
AWS_REGION="us-west-2"
ACTION="plan"
AUTO_APPROVE=false
DESTROY=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to print usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -e, --environment ENVIRONMENT    Environment (dev, staging, prod) [default: dev]"
    echo "  -r, --region REGION             AWS region [default: us-west-2]"
    echo "  -a, --action ACTION             Action (plan, apply, destroy) [default: plan]"
    echo "  --auto-approve                  Auto approve Terraform apply"
    echo "  --destroy                       Destroy infrastructure"
    echo "  -h, --help                      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -e dev -a plan                    # Plan dev environment"
    echo "  $0 -e prod -a apply                  # Apply prod environment"
    echo "  $0 -e dev --destroy --auto-approve   # Destroy dev environment"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -r|--region)
            AWS_REGION="$2"
            shift 2
            ;;
        -a|--action)
            ACTION="$2"
            shift 2
            ;;
        --auto-approve)
            AUTO_APPROVE=true
            shift
            ;;
        --destroy)
            DESTROY=true
            ACTION="destroy"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            print_message $RED "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
    print_message $RED "Invalid environment. Must be one of: dev, staging, prod"
    exit 1
fi

# Validate action
if [[ ! "$ACTION" =~ ^(plan|apply|destroy)$ ]]; then
    print_message $RED "Invalid action. Must be one of: plan, apply, destroy"
    exit 1
fi

# Check prerequisites
check_prerequisites() {
    print_message $BLUE "Checking prerequisites..."

    # Check if Terraform is installed
    if ! command -v terraform &> /dev/null; then
        print_message $RED "Terraform is not installed. Please install Terraform 1.0 or later."
        exit 1
    fi

    # Check Terraform version
    terraform_version=$(terraform version -json | jq -r '.terraform_version')
    print_message $GREEN "Terraform version: $terraform_version"

    # Check if AWS CLI is installed and configured
    if ! command -v aws &> /dev/null; then
        print_message $RED "AWS CLI is not installed. Please install and configure AWS CLI."
        exit 1
    fi

    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_message $RED "AWS credentials not configured. Please run 'aws configure'."
        exit 1
    fi

    aws_account=$(aws sts get-caller-identity --query Account --output text)
    aws_user=$(aws sts get-caller-identity --query Arn --output text)
    print_message $GREEN "AWS Account: $aws_account"
    print_message $GREEN "AWS User: $aws_user"

    # Check if jq is installed (for JSON parsing)
    if ! command -v jq &> /dev/null; then
        print_message $YELLOW "jq is not installed. Some features may not work correctly."
    fi
}

# Initialize Terraform
initialize_terraform() {
    print_message $BLUE "Initializing Terraform..."

    # Create backend configuration for remote state (if using S3 backend)
    if [[ -f "backend-${ENVIRONMENT}.hcl" ]]; then
        terraform init -backend-config="backend-${ENVIRONMENT}.hcl"
    else
        terraform init
    fi
}

# Validate Terraform configuration
validate_terraform() {
    print_message $BLUE "Validating Terraform configuration..."
    terraform validate

    # Check formatting
    if ! terraform fmt -check=true -recursive .; then
        print_message $YELLOW "Terraform files are not properly formatted. Running 'terraform fmt'..."
        terraform fmt -recursive .
    fi
}

# Create workspace if needed
create_workspace() {
    if terraform workspace list | grep -q "$ENVIRONMENT"; then
        print_message $BLUE "Switching to $ENVIRONMENT workspace..."
        terraform workspace select "$ENVIRONMENT"
    else
        print_message $BLUE "Creating $ENVIRONMENT workspace..."
        terraform workspace new "$ENVIRONMENT"
    fi
}

# Plan infrastructure
plan_infrastructure() {
    print_message $BLUE "Planning infrastructure for $ENVIRONMENT environment..."

    # Set variables file based on environment
    local var_file="terraform.tfvars"
    if [[ -f "terraform-${ENVIRONMENT}.tfvars" ]]; then
        var_file="terraform-${ENVIRONMENT}.tfvars"
    fi

    local plan_file="terraform-${ENVIRONMENT}.tfplan"

    terraform plan \
        -var="environment=$ENVIRONMENT" \
        -var="aws_region=$AWS_REGION" \
        -var-file="$var_file" \
        -out="$plan_file"

    print_message $GREEN "Plan saved to $plan_file"
}

# Apply infrastructure
apply_infrastructure() {
    print_message $BLUE "Applying infrastructure for $ENVIRONMENT environment..."

    local plan_file="terraform-${ENVIRONMENT}.tfplan"

    if [[ ! -f "$plan_file" ]]; then
        print_message $YELLOW "Plan file not found. Running plan first..."
        plan_infrastructure
    fi

    local apply_args=()
    if [[ "$AUTO_APPROVE" == true ]]; then
        apply_args+=("-auto-approve")
    fi

    terraform apply "${apply_args[@]}" "$plan_file"

    # Clean up plan file
    rm -f "$plan_file"

    print_message $GREEN "Infrastructure applied successfully!"

    # Display important outputs
    display_outputs
}

# Destroy infrastructure
destroy_infrastructure() {
    print_message $YELLOW "WARNING: This will destroy all infrastructure in the $ENVIRONMENT environment!"

    if [[ "$AUTO_APPROVE" != true ]]; then
        read -p "Are you sure you want to continue? (yes/no): " confirm
        if [[ "$confirm" != "yes" ]]; then
            print_message $BLUE "Destroy cancelled."
            exit 0
        fi
    fi

    print_message $RED "Destroying infrastructure..."

    # Set variables file based on environment
    local var_file="terraform.tfvars"
    if [[ -f "terraform-${ENVIRONMENT}.tfvars" ]]; then
        var_file="terraform-${ENVIRONMENT}.tfvars"
    fi

    local destroy_args=(
        -var="environment=$ENVIRONMENT"
        -var="aws_region=$AWS_REGION"
        -var-file="$var_file"
    )

    if [[ "$AUTO_APPROVE" == true ]]; then
        destroy_args+=("-auto-approve")
    fi

    terraform destroy "${destroy_args[@]}"

    print_message $GREEN "Infrastructure destroyed successfully!"
}

# Display important outputs
display_outputs() {
    print_message $BLUE "Important outputs:"

    # EKS cluster configuration
    if terraform output -raw eks_cluster_endpoint &> /dev/null; then
        local cluster_name=$(terraform output -raw eks_cluster_id)
        print_message $GREEN "EKS Cluster: $cluster_name"
        print_message $BLUE "Configure kubectl: aws eks update-kubeconfig --region $AWS_REGION --name $cluster_name"
    fi

    # Application URLs
    if terraform output -raw application_load_balancer_dns_name &> /dev/null; then
        local alb_dns=$(terraform output -raw application_load_balancer_dns_name)
        print_message $GREEN "Application URL: http://$alb_dns"
    fi

    # Database connection
    if terraform output -raw database_connection_string &> /dev/null; then
        print_message $GREEN "Database connection string available in Terraform outputs"
        print_message $YELLOW "Use 'terraform output database_connection_string' to view"
    fi

    # S3 buckets
    if terraform output -json s3_model_storage_bucket_name &> /dev/null; then
        local model_bucket=$(terraform output -raw s3_model_storage_bucket_name)
        print_message $GREEN "Model storage bucket: s3://$model_bucket"
    fi
}

# Main execution
main() {
    print_message $BLUE "F1 Prediction Analytics Infrastructure Deployment"
    print_message $BLUE "Environment: $ENVIRONMENT"
    print_message $BLUE "Region: $AWS_REGION"
    print_message $BLUE "Action: $ACTION"
    print_message $BLUE ""

    # Check prerequisites
    check_prerequisites

    # Initialize Terraform
    initialize_terraform

    # Validate configuration
    validate_terraform

    # Create or select workspace
    create_workspace

    # Execute the requested action
    case $ACTION in
        plan)
            plan_infrastructure
            ;;
        apply)
            apply_infrastructure
            ;;
        destroy)
            destroy_infrastructure
            ;;
    esac

    print_message $GREEN "Deployment script completed successfully!"
}

# Execute main function
main "$@"