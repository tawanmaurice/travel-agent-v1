##############################################
# LAMBDA FUNCTION
##############################################

resource "aws_lambda_function" "travel_agent" {
  function_name = "travel-agent-v1"
  role          = aws_iam_role.lambda_role.arn
  handler       = "lambda.lambda_handler"
  runtime       = "python3.12"

  filename         = "lambda.zip"
  source_code_hash = filebase64sha256("lambda.zip")

  # Headless scraping is slower than simple Google calls,
  # so we give it more time.
  timeout     = 120
  memory_size = 512

  #############################
  # ENVIRONMENT VARIABLES
  #############################
  environment {
    variables = {
      GOOGLE_API_KEY = var.google_api_key
      GOOGLE_CX      = var.google_cx
      TABLE_NAME     = aws_dynamodb_table.travel_agent_leads.name
      REPORT_EMAIL   = var.report_email

      # === NEW: headless scraping config ===
      HEADLESS_API_URL = var.headless_api_url   # e.g. https://api.scraperapi.com
      HEADLESS_API_KEY = var.headless_api_key
      HEADLESS_RENDER  = "true"
      HEADLESS_TIMEOUT = "60"
    }
  }
}
