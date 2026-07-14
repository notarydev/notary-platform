resource "aws_ecs_cluster" "this" {
  name = var.project_name
}

# Task definitions, services, load balancers, and autoscaling policies will be added as the runtime architecture is finalized.
