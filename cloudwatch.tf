############################################
# CloudWatch / EventBridge schedule
############################################

# Morning run (8:00 UTC = 3:00 AM Eastern when UTC-5)
resource "aws_cloudwatch_event_rule" "travel_agent_schedule_morning" {
  name                = "travel-agent-schedule-morning"
  description         = "Run travel-agent-v1 Lambda in the morning"
  schedule_expression = "cron(0 8 * * ? *)" # every day, 08:00 UTC

  # default event bus
  event_bus_name = "default"
}

# Evening run (20:00 UTC = 3:00 PM Eastern when UTC-5)
resource "aws_cloudwatch_event_rule" "travel_agent_schedule_evening" {
  name                = "travel-agent-schedule-evening"
  description         = "Run travel-agent-v1 Lambda in the evening"
  schedule_expression = "cron(0 20 * * ? *)" # every day, 20:00 UTC

  event_bus_name = "default"
}

# Morning target wiring the rule → Lambda
resource "aws_cloudwatch_event_target" "travel_agent_target_morning" {
  rule      = aws_cloudwatch_event_rule.travel_agent_schedule_morning.name
  target_id = "travel-agent-target-morning"
  arn       = aws_lambda_function.travel_agent.arn

  # Optional: if you want to see in logs that this is the morning run
  input = jsonencode({
    run_type = "morning"
  })
}

# Evening target wiring the rule → Lambda
resource "aws_cloudwatch_event_target" "travel_agent_target_evening" {
  rule      = aws_cloudwatch_event_rule.travel_agent_schedule_evening.name
  target_id = "travel-agent-target-evening"
  arn       = aws_lambda_function.travel_agent.arn

  input = jsonencode({
    run_type = "evening"
  })
}

# Permissions so EventBridge can invoke the Lambda
resource "aws_lambda_permission" "allow_morning" {
  statement_id  = "AllowExecutionFromCloudWatchTravelMorning"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.travel_agent.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.travel_agent_schedule_morning.arn
}

resource "aws_lambda_permission" "allow_evening" {
  statement_id  = "AllowExecutionFromCloudWatchTravelEvening"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.travel_agent.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.travel_agent_schedule_evening.arn
}
