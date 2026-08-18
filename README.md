# SQL Analytics Agent

SQL Analytics Agent is a natural-language analytics application that lets users ask business questions without having to write SQL manually.

A user can ask something like:

```text
What was our total revenue by region in Q1?
```

The agent identifies the relevant database schema, generates the SQL query, validates it, executes it against PostgreSQL, checks the result for anomalies, chooses a suitable visualization, and explains the result in plain English.

The project also supports investigative questions such as:

```text
Why did the South region underperform?
```

For these questions, the agent can break the problem into smaller analytical questions, run multiple queries, compare the evidence, and produce a root-cause style explanation.

---

## What the project does

The main goal of this project is to automate some of the repetitive work involved in day-to-day data analysis.

Instead of manually going through this process:

```text
Business Question
      ↓
Find the right tables
      ↓
Write SQL
      ↓
Run the query
      ↓
Fix SQL errors
      ↓
Check the result
      ↓
Build a chart
      ↓
Write a summary
```

the agent handles most of the workflow automatically.

It is mainly designed for routine and well-defined analytics requests. The system is not intended to replace the business judgement required to decide which metrics matter or why something happened outside the available data.

---

## Features

* Natural language to SQL
* Automatic schema understanding
* SQL validation before execution
* Read-only database access
* Self-healing SQL retries
* Simple and investigative question handling
* Root cause analysis
* Automatic anomaly detection
* Automatic chart selection
* Plain-English business summaries
* Follow-up question suggestions
* Conversation memory
* Downloadable reports
* Redis caching
* LangSmith tracing
* FastAPI backend
* Streamlit frontend
* PostgreSQL on AWS RDS
* Docker support
* Kubernetes deployment
* GitHub Actions CI/CD

---

## How it works

A question moves through several stages before the user receives an answer.

```text
User Question
      |
      v
Guardrails
      |
      v
Question Classifier
      |
      v
Schema Resolution
      |
      v
SQL Generation
      |
      v
SQL Validation
      |
      v
SQL Execution
      |
      +--------------------+
      |                    |
   Success               Error
      |                    |
      |              Fix SQL + Retry
      |                    |
      +--------------------+
      |
      v
Analysis / Root Cause
      |
      v
Anomaly Detection
      |
      v
Chart Generation
      |
      v
Business Summary
      |
      v
Final Answer
```

The exact flow depends on the type of question.

A simple lookup such as:

```text
What is the total revenue by region?
```

usually requires one SQL query.

A question such as:

```text
Why did the South region underperform?
```

requires a deeper investigation and may result in several supporting queries before the final answer is generated.

---

## Agent Workflow

The project separates responsibilities across different parts of the analytics pipeline.

### Guardrails

The guardrails run before any SQL reaches the database.

They prevent unsafe requests such as:

```text
Delete all orders from South
```

The application is designed around read-only analytics, so database modification requests are rejected.

---

### Question Classifier

The classifier determines what type of analysis the user is requesting.

For example:

```text
What was revenue in Q1?
```

is treated as a simple lookup.

```text
Why did revenue decline in Q1?
```

requires an investigative workflow.

This allows the system to avoid running an unnecessarily expensive reasoning pipeline for straightforward questions.

---

### Schema Resolution

Before generating SQL, the agent needs to understand which tables and columns are relevant.

For example, a question about:

```text
revenue by region
```

may require information from tables containing:

* orders
* customers
* regions
* products

The schema information is provided to the SQL generation step so the model does not have to guess database structure.

---

### SQL Generation

The SQL generator converts the user's question into a SQL query using the resolved schema.

Example:

```sql
SELECT
    region,
    SUM(revenue) AS total_revenue
FROM orders
WHERE order_date >= '2026-01-01'
  AND order_date < '2026-04-01'
GROUP BY region
ORDER BY total_revenue DESC;
```

The generated SQL is not executed immediately.

It first goes through the validator.

---

## SQL Validation

SQL validation is one of the most important parts of this project.

The validator checks queries before they can reach the database.

The application is designed to allow analytical `SELECT` operations while rejecting destructive operations such as:

```sql
DELETE
DROP
UPDATE
INSERT
ALTER
TRUNCATE
```

The system also checks:

* allowed tables
* query structure
* user permissions
* result limits
* unsafe SQL patterns

This creates an additional safety layer on top of the read-only PostgreSQL database user.

---

## Read-Only Database Access

The production database connection uses a dedicated read-only PostgreSQL user.

This means that even if an unsafe query somehow passed the application-level validation, the database user itself should not have permission to modify the underlying business data.

The intended access pattern is:

```text
Application Guardrails
        ↓
SQL Validator
        ↓
Read-Only PostgreSQL User
        ↓
AWS RDS
```

---

## Self-Healing SQL

Generated SQL will not always work on the first attempt.

A model might produce:

```sql
SELECT region_name
FROM orders;
```

when the actual column is:

```text
region
```

Instead of immediately returning the database error to the user, the agent can use the error message to correct the query and retry.

```text
Generated SQL
      |
      v
Execute
      |
      v
Database Error
      |
      v
Read Error Message
      |
      v
Generate Corrected SQL
      |
      v
Validate Again
      |
      v
Retry
```

The retry process is limited so the system does not enter an infinite correction loop.

---

## Investigative Questions

One part of this project that I found interesting was handling questions that cannot be answered with a single SQL statement.

For example:

```text
Why did the South region underperform?
```

The agent may need to investigate several possibilities:

```text
Did the number of orders decrease?

Did average order value decrease?

Did a specific product category decline?

Did customer activity decrease?

Was there a change compared with the previous period?
```

The system can generate smaller analytical questions, execute the required SQL for each one, compare the results, and rank the evidence before producing the final explanation.

This makes the project different from a basic text-to-SQL application that only returns a query and its result.

---

## Anomaly Detection

After the SQL result is returned, the application checks the data for unusual values.

Examples include:

* sudden revenue drops
* unexpected spikes
* missing values
* unusual category changes
* duplicate records
* values outside an expected range

For example, if one region suddenly increases by 200%, the system can flag it rather than presenting the number without context.

---

## Automatic Chart Selection

The application also decides how the result should be visualized.

Typical behavior:

```text
Time series         → Line chart
Category comparison → Bar chart
Proportions         → Pie chart
Correlation         → Scatter plot
Simple values       → Table / metric
```

This means the user does not need to manually choose a visualization for every question.

---

## Conversation Memory

The application keeps context from previous questions within the same conversation.

For example:

```text
User:
What was revenue by region last quarter?

User:
Now break that down by product line.
```

The second question does not contain the full original request.

Conversation memory allows the agent to understand that "that" refers to the previous revenue analysis and preserve the original time period and filters while adding the product breakdown.

---

## Example

### Question

```text
What was our revenue by region last quarter?
```

The pipeline might perform the following steps:

```text
1. Check guardrails
2. Identify relevant schema
3. Generate SQL
4. Validate SQL
5. Execute query
6. Scan results for anomalies
7. Choose a bar chart
8. Generate business explanation
```

### Follow-up

```text
Now break that down by product line.
```

The application uses the conversation context and generates a new query without requiring the user to repeat the entire original question.

---

## Tech Stack

### AI / Agent Layer

* Python
* Large Language Models
* LangChain
* LangGraph
* Prompt Engineering
* LangSmith

### Database

* PostgreSQL
* SQLAlchemy
* AWS RDS

### Backend

* FastAPI
* Uvicorn

### Frontend

* Streamlit

### Analytics

* Pandas
* Plotly / Matplotlib
* Statistical anomaly detection

### Caching

* Redis

### Cloud / Deployment

* AWS
* Amazon RDS
* Amazon ECR
* Amazon EKS
* Docker
* Docker Compose
* Kubernetes

### DevOps

* GitHub Actions
* CI/CD
* Pytest

---

## Project Structure

```text
sql-analytics-agent/
│
├── backend/
│   │
│   ├── src/
│   │   ├── agents/
│   │   │   ├── agent_factory.py
│   │   │   ├── nodes.py
│   │   │   ├── pipeline.py
│   │   │   └── state.py
│   │   │
│   │   ├── api/
│   │   │   ├── main.py
│   │   │   └── routes/
│   │   │
│   │   ├── tools/
│   │   │   ├── sql_tools.py
│   │   │   └── chart_tools.py
│   │   │
│   │   ├── prompts/
│   │   └── config.py
│   │
│   ├── tests/
│   ├── streamlit_app.py
│   ├── start.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .env.example
│   └── .gitignore
│
├── k8s/
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── redis-deployment.yaml
│   ├── app-deployment.yaml
│   ├── app-service.yaml
│   ├── hpa.yaml
│   └── ingress.yaml
│
├── .github/
│   └── workflows/
│
├── docker-compose.yml
└── README.md
```

---

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/sql-analytics-agent.git

cd sql-analytics-agent
```

---

### 2. Move to the backend

```bash
cd backend
```

---

### 3. Create a virtual environment

```bash
python -m venv venv
```

Windows Git Bash:

```bash
source venv/Scripts/activate
```

Mac/Linux:

```bash
source venv/bin/activate
```

---

### 4. Install dependencies

```bash
pip install --upgrade pip

pip install -r requirements.txt
```

---

## Environment Variables

Create the environment file:

```bash
cp .env.example .env
```

Example configuration:

```env
OPENAI_API_KEY=your_api_key

RDS_HOST=your_rds_endpoint
RDS_PORT=5432
RDS_DB=your_database
RDS_USER=sql_agent_readonly
RDS_PASSWORD=your_database_password

LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_key
```

If Redis is enabled, add the corresponding Redis configuration used by the project.

Do not commit `.env`, database credentials, API keys, or cloud credentials to GitHub.

---

## Run Locally

The project includes a startup script that starts both the FastAPI backend and Streamlit application.

```bash
cd backend

source venv/Scripts/activate

set -a
source .env
set +a

python start.py
```

Once started:

```text
API    → http://localhost:8000
UI     → http://localhost:8501
Health → http://localhost:8000/health
```

Open:

```text
http://localhost:8501
```

in your browser.

---

## Run With Docker

From the project root:

```bash
docker compose up --build
```

Once the containers start:

```text
Streamlit → http://localhost:8501
FastAPI   → http://localhost:8000
```

To stop:

```bash
docker compose down
```

---

## Example Questions

Some questions I use while testing the application:

### Simple analytics

```text
What is the total revenue by region in Q1?
```

```text
Show the top 10 customers by revenue.
```

```text
Compare monthly revenue for the last six months.
```

### Investigative analytics

```text
Why did the South region underperform?
```

```text
Why did revenue decline last quarter?
```

```text
Which factors contributed the most to the drop in sales?
```

### Follow-up questions

```text
Now break that down by product.
```

```text
Compare it with the previous quarter.
```

```text
Show only the South region.
```

### Guardrail test

```text
Delete all orders from South.
```

This should be rejected before reaching the database.

---

## Testing

Run the automated tests using:

```bash
cd backend

pytest tests/ -v
```

The tests are used to verify parts of the pipeline such as:

* guardrails
* SQL validation
* database interactions
* API behavior
* agent workflow

---

## Redis Caching

Repeated analytics requests do not always need to run the full agent workflow again.

Redis can be used to cache repeated:

```text
Question
   ↓
Generated SQL
   ↓
Query Result
```

This reduces unnecessary database and LLM calls for repeated questions.

The schema context can also be cached because rebuilding the same schema description for every request is unnecessary.

---

## LangSmith Tracing

LangSmith is used to trace the agent workflow and individual LLM calls.

This is particularly useful for investigative questions because one user request can result in several reasoning and SQL-generation calls.

Tracing makes it easier to inspect:

* prompts
* model responses
* execution time
* token usage
* failed steps
* retries
* root-cause reasoning flow

Enable tracing through:

```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_key
```

---

## AWS Deployment

The application is designed to work with PostgreSQL running on AWS RDS.

The broader deployment includes:

```text
User
  |
  v
Application
  |
  v
FastAPI / Streamlit
  |
  +------ Redis
  |
  v
AWS RDS PostgreSQL
```

Docker images can be stored in Amazon ECR and deployed using Kubernetes.

The repository contains Kubernetes manifests for:

* application deployment
* service
* configuration
* Redis
* horizontal pod autoscaling
* ingress

---

## CI/CD

The GitHub Actions workflow automates the deployment process.

```text
git push
   |
   v
GitHub Actions
   |
   v
Run Tests
   |
   v
Build Docker Image
   |
   v
Push to Amazon ECR
   |
   v
Deploy
   |
   v
Health Check
   |
   v
Rollback if deployment fails
```

This removes the need to manually rebuild and deploy the application after every change.

---

## Security

Database access is deliberately restricted because the application generates SQL dynamically.

The main safeguards include:

* read-only PostgreSQL user
* application-level guardrails
* SQL validation
* destructive statement blocking
* allowed-table validation
* result-size limits
* user permission checks
* query logging
* secrets kept outside source control

The executor is the part of the pipeline responsible for actually running SQL. SQL should only reach it after validation.

---

## What I learned from this project

The most useful part of building this project was understanding that text-to-SQL is only one part of an analytics agent.

Generating SQL is relatively straightforward. Making it safe and useful requires additional work around:

* schema understanding
* SQL validation
* error recovery
* database permissions
* multi-step analysis
* anomaly detection
* chart selection
* conversation context
* caching
* observability

I also found that there is an important difference between SQL that executes successfully and SQL that is actually correct.

A query can run without errors and still use the wrong join, double-count rows, or apply the wrong business filter. Because of that, validation, testing, anomaly checks, and human review are important parts of building this type of system.

---

## Current Limitations

There are still situations where human judgement is required.

For example:

* ambiguous business questions
* deciding which new metrics should be tracked
* investigating causes that are not represented in the database
* data quality problems in the source systems
* schema changes that are not reflected in the agent context
* business-specific definitions that have not been provided to the system

The agent is designed to reduce repetitive analytics work, not replace the judgement of an experienced analyst.

---

## Future Improvements

Some improvements I would like to add:

* stronger role-based access control
* support for additional databases
* improved semantic schema matching
* better data quality checks
* scheduled reports
* email / Slack report delivery
* query optimization recommendations
* improved conversation memory
* richer analytics visualizations
* better evaluation of generated SQL
* user authentication
* more detailed usage and cost monitoring

---

## Disclaimer

This project is intended as a learning and portfolio project.

The results produced by the agent should be validated before they are used for important business or financial decisions.
