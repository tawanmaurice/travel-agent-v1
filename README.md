Travel Agent V1 — Google Scraper + DynamoDB + SES Email Reports

Travel Agent V1 is an automated travel lead generator built on AWS.
It searches the web for long-term rental opportunities (ideal for people moving to a new city), extracts relevant URLs, stores them in DynamoDB, and sends a summary email report using AWS SES.

This version is designed for daily, automated travel lead discovery with zero manual work.

🚀 Features

🔍 Google Programmable Search API scraping for rental listings

🏗️ Terraform deployment for Lambda, DynamoDB, IAM, and CloudWatch scheduling

💾 DynamoDB upsert (no duplicates, hash-based ID system)

✉️ AWS SES email summary reports sent after every run

⚡ Skips junk/social domains like Facebook, Reddit, Twitter, etc.

🕒 Run manually or on an automated schedule

🧱 Architecture

Services Used:

AWS Lambda (Python 3.12)

AWS DynamoDB

AWS SES

AWS IAM

AWS CloudWatch Event Rules (scheduled triggers)

Flow:

Lambda runs a set of Google Queries

For each URL found:

Clean & validate domain

Skip social/junk URLs

Hash URL → record ID

Upsert into DynamoDB

After scraping completes:

Count total saved leads

Email a report via SES

📁 File Structure
travel-agent-v1/
│
├── lambda.py              # Main scraping + SES logic
├── lambda.tf             # Lambda resource
├── dynamo.tf             # DynamoDB table
├── iamrole.tf            # IAM roles, SES + Dynamo permissions
├── cloudwatch.tf         # Scheduling
├── variables.tf          # Required variables
├── terraform.tfvars      # Your API keys + report email
├── outputs.tf
│
├── build-lambda/         # Python dependencies (created during build)
├── lambda.zip            # Deployment zip (generated locally)
│
└── README.md             # (this file)

🔑 Required Variables

Add these to terraform.tfvars:

aws_region      = "us-east-1"
google_api_key  = "YOUR_GOOGLE_API_KEY"
google_cx       = "YOUR_GOOGLE_CX"
report_email    = "tawanxxx@gmail.com"


⚠️ Do NOT commit real API keys to GitHub.

🧩 Build & Deploy
1. Create Lambda package
pip install -r requirements.txt -t build-lambda
Compress-Archive -Path .\build-lambda\* -DestinationPath .\lambda.zip -Force

2. Terraform deploy
terraform init
terraform fmt
terraform validate
terraform plan -out=tfplan
terraform apply tfplan

🧪 Test the Lambda

In AWS Console → Lambda → travel-agent-v1

Click Test

Set event name: manual-test

Run

You should see:

Travel agent completed. Saved XX records.
SES summary email sent.


And an email in your inbox with scraped leads.

📧 Email Reports

This build sends a summary email report to yourself:

Number of new URLs saved

Example top URLs

Timestamp

Email identity must be verified in SES:

tawanxxx@gmail.com


(Already done in this project)

🔒 IAM Policies (included & working)

dynamodb:PutItem

dynamodb:UpdateItem

dynamodb:DescribeTable

ses:SendEmail

ses:SendRawEmail

CloudWatch log permissions

🧠 How It Handles Duplicates

Every URL is hashed:

hashlib.sha256(url.encode()).hexdigest()


This becomes the DynamoDB partition key.

Same URL twice → ONE record (upsert)

New URL → inserted

