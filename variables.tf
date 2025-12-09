########################
# Provider / region
########################

variable "aws_region" {
  description = "AWS region to deploy resources in"
  type        = string
}

########################
# Google Custom Search
########################

variable "google_api_key" {
  description = "Google Programmable Search API key"
  type        = string
}

variable "google_cx" {
  description = "Google Programmable Search CX identifier"
  type        = string
}

########################
# Email reporting
########################

variable "report_email" {
  description = "Email address to send travel agent summary reports to"
  type        = string
}

########################
# CloudWatch schedules
########################

variable "schedule_expression_morning" {
  description = "CloudWatch schedule expression for the morning travel-agent run"
  type        = string
}

variable "schedule_expression_evening" {
  description = "CloudWatch schedule expression for the evening travel-agent run"
  type        = string
}

########################
# Headless scraping API (NEW)
########################

variable "headless_api_url" {
  description = "Base URL for headless scraping provider (e.g. https://api.scraperapi.com)"
  type        = string
}

variable "headless_api_key" {
  description = "API key for headless scraping provider"
  type        = string
}

variable "headless_render" {
  description = "Whether the headless API should render JavaScript (true/false)"
  type        = string
  default     = "true"
}

variable "headless_timeout" {
  description = "Timeout (seconds) for headless API requests"
  type        = number
  default     = 60
}
