# Variables for EKS Module

variable "name_prefix" {
  description = "Name prefix for resources"
  type        = string
}

variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
}

variable "cluster_version" {
  description = "Kubernetes version for the EKS cluster"
  type        = string
  default     = "1.28"

  validation {
    condition = can(regex("^1\\.(2[7-9]|[3-9][0-9])$", var.cluster_version))
    error_message = "EKS cluster version must be 1.27 or higher."
  }
}

variable "vpc_id" {
  description = "VPC ID where the cluster will be created"
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs for the EKS cluster"
  type        = list(string)

  validation {
    condition     = length(var.subnet_ids) >= 2
    error_message = "At least 2 subnet IDs must be provided for high availability."
  }
}

variable "public_subnet_ids" {
  description = "List of public subnet IDs for load balancers"
  type        = list(string)
  default     = []
}

variable "node_groups" {
  description = "EKS node group configurations"
  type = map(object({
    instance_types = list(string)
    scaling_config = object({
      desired_size = number
      max_size     = number
      min_size     = number
    })
    disk_size     = number
    capacity_type = string
  }))

  validation {
    condition = alltrue([
      for k, v in var.node_groups :
      contains(["ON_DEMAND", "SPOT"], v.capacity_type)
    ])
    error_message = "Capacity type must be either ON_DEMAND or SPOT."
  }
}

variable "public_access_cidrs" {
  description = "List of CIDR blocks for EKS public access"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "ec2_ssh_key" {
  description = "EC2 SSH key name for node group access"
  type        = string
  default     = null
}

variable "allowed_security_group_ids" {
  description = "List of security group IDs allowed to access nodes"
  type        = list(string)
  default     = []
}

variable "enable_irsa" {
  description = "Enable IAM Roles for Service Accounts"
  type        = bool
  default     = true
}

variable "cluster_endpoint_private_access" {
  description = "Enable private access to EKS cluster endpoint"
  type        = bool
  default     = true
}

variable "cluster_endpoint_public_access" {
  description = "Enable public access to EKS cluster endpoint"
  type        = bool
  default     = true
}

variable "addon_versions" {
  description = "Versions for EKS addons"
  type = object({
    vpc_cni        = optional(string, "v1.15.4-eksbuild.1")
    coredns        = optional(string, "v1.10.1-eksbuild.5")
    kube_proxy     = optional(string, "v1.28.2-eksbuild.2")
    ebs_csi_driver = optional(string, "v1.24.1-eksbuild.1")
  })
  default = {}
}

variable "enable_cluster_logging" {
  description = "Enable EKS control plane logging"
  type        = bool
  default     = true
}

variable "cluster_log_types" {
  description = "List of control plane log types to enable"
  type        = list(string)
  default     = ["api", "audit", "authenticator", "controllerManager", "scheduler"]
}

variable "cluster_log_retention_days" {
  description = "Retention period for EKS control plane logs"
  type        = number
  default     = 7

  validation {
    condition = contains([
      1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653
    ], var.cluster_log_retention_days)
    error_message = "Log retention days must be a valid CloudWatch log retention period."
  }
}

variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}

# Cluster autoscaler settings
variable "enable_cluster_autoscaler" {
  description = "Enable cluster autoscaler IAM policies"
  type        = bool
  default     = true
}

# AWS Load Balancer Controller settings
variable "enable_aws_load_balancer_controller" {
  description = "Enable AWS Load Balancer Controller IAM policies"
  type        = bool
  default     = true
}

# External DNS settings
variable "enable_external_dns" {
  description = "Enable External DNS IAM policies"
  type        = bool
  default     = false
}