# Application Load Balancer, ACM certificate, and Route53 DNS for api.getnotary.ai

# ACM certificates for ALB must be in us-east-1.
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"

  default_tags {
    tags = {
      awsApplication = var.aws_application_arn
      Project        = local.project_name
      Environment    = local.environment
      ManagedBy      = "terraform"
    }
  }
}

# Public Route53 hosted zone for the domain.
resource "aws_route53_zone" "main" {
  count = var.api_dns != "" ? 1 : 0
  name  = var.api_dns

  tags = {
    Name = "${local.name_prefix}-zone"
  }
}

# Wildcard ACM certificate for the domain and api subdomain.
resource "aws_acm_certificate" "main" {
  provider          = aws.us_east_1
  count             = var.api_dns != "" ? 1 : 0
  domain_name       = "api.${var.api_dns}"
  validation_method = "DNS"
  subject_alternative_names = [
    var.api_dns,
    "*.${var.api_dns}"
  ]

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name = "${local.name_prefix}-cert"
  }
}

# DNS validation records for the ACM certificate.
# Deduplicate by validation CNAME because SANs may share the same record.
locals {
  cert_validation_records = var.api_dns != "" ? {
    for dvo in aws_acm_certificate.main[0].domain_validation_options : dvo.resource_record_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }...
  } : {}
}

resource "aws_route53_record" "cert_validation" {
  for_each = local.cert_validation_records

  zone_id = aws_route53_zone.main[0].zone_id
  name    = each.value[0].name
  type    = each.value[0].type
  records = [each.value[0].record]
  ttl     = 60
}

resource "aws_acm_certificate_validation" "main" {
  provider                = aws.us_east_1
  count                   = var.api_dns != "" ? 1 : 0
  certificate_arn         = aws_acm_certificate.main[0].arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]

  timeouts {
    create = "10m"
  }
}

# Application Load Balancer in the public subnets.
resource "aws_lb" "main" {
  count              = var.api_dns != "" ? 1 : 0
  name               = "${local.name_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb[0].id]
  subnets            = aws_subnet.public[*].id

  enable_deletion_protection = false

  tags = {
    Name = "${local.name_prefix}-alb"
  }
}

# Security group for the ALB (ingress 80/443 from anywhere).
resource "aws_security_group" "alb" {
  count       = var.api_dns != "" ? 1 : 0
  name        = "${local.name_prefix}-alb-sg"
  description = "Allow inbound HTTP/HTTPS traffic"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTP redirect"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name_prefix}-alb-sg"
  }
}

# ALB target group for the API on port 8000.
resource "aws_lb_target_group" "api" {
  count       = var.api_dns != "" ? 1 : 0
  name        = "${local.name_prefix}-api-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 3
  }

  tags = {
    Name = "${local.name_prefix}-api-tg"
  }
}

# HTTPS listener.
resource "aws_lb_listener" "https" {
  count             = var.api_dns != "" ? 1 : 0
  load_balancer_arn = aws_lb.main[0].arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate_validation.main[0].certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api[0].arn
  }
}

# HTTP listener redirects to HTTPS.
resource "aws_lb_listener" "http" {
  count             = var.api_dns != "" ? 1 : 0
  load_balancer_arn = aws_lb.main[0].arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

# Route53 A record for api.getnotary.ai pointing to the ALB.
resource "aws_route53_record" "api" {
  count   = var.api_dns != "" ? 1 : 0
  zone_id = aws_route53_zone.main[0].zone_id
  name    = "api.${var.api_dns}"
  type    = "A"

  alias {
    name                   = aws_lb.main[0].dns_name
    zone_id                = aws_lb.main[0].zone_id
    evaluate_target_health = true
  }
}
