# Deploying Probashi Shield to AWS

Owner: Agent 1. This guide deploys the backend container. A short note on the frontend is at the end.

> Status: these steps were written from the AWS documentation linked below and have **not** been run against a real AWS account yet. The Docker image has also not been built yet (Docker was not running on the machine where this was written). Expect to adjust small details the first time.

## Which service, and why

**Choice: Amazon ECS on Fargate, created through ECS Express Mode.**

| Option | Verdict |
| --- | --- |
| AWS App Runner | Was the simplest option, but AWS closed it to new customers on 30 April 2026 and recommends ECS Express Mode instead ([AWS notice](https://docs.aws.amazon.com/apprunner/latest/dg/apprunner-availability-change.html)). A new student account cannot rely on it. |
| ECS Fargate, set up by hand | Works, but you create the cluster, task definition, load balancer, target group, security groups, HTTPS certificate and auto scaling yourself. Too many steps for a small team. |
| **ECS Fargate via Express Mode** | One command (or one console form) takes a container image and creates all of the above, with an HTTPS URL. No servers to patch. No extra charge for Express Mode itself ([overview](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/express-service-overview.html)). |

The trade-off: Express Mode always creates an Application Load Balancer, which has a fixed monthly cost even with zero traffic (see costs below).

## What you need first

- An AWS account, with a [default VPC](https://docs.aws.amazon.com/vpc/latest/userguide/default-vpc.html) in the region you pick (new accounts have one).
- [AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html), configured with `aws configure`.
- Docker running locally.
- The API keys the real modules need (see the env var table).

Set these once per terminal. Pick the region closest to your users that supports Express Mode; `ap-south-1` (Mumbai) is used here as an example only.

```bash
export AWS_REGION=ap-south-1
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export REPO=probashi-backend
export IMAGE=$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO
```

## Step 1 — Build the image and push it to ECR

Run from the repo root.

```bash
aws ecr create-repository --repository-name $REPO --region $AWS_REGION

aws ecr get-login-password --region $AWS_REGION \
  | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

export TAG=$(git rev-parse --short HEAD)
docker build --platform linux/arm64 -f backend/Dockerfile -t $IMAGE:$TAG .
docker push $IMAGE:$TAG
```

`linux/arm64` matches `--cpu-architecture ARM64` in step 4. ARM (Graviton) Fargate is cheaper than x86, and builds natively on Apple Silicon laptops. On an Intel/AMD laptop, either keep `--platform linux/arm64` (slower, emulated build) or use `linux/amd64` here and `X86_64` in step 4.

## Step 2 — Store the secrets

Never put API keys in the image or in plain environment variables. Store each as a `SecureString` in Systems Manager Parameter Store (no charge for standard parameters):

```bash
aws ssm put-parameter --region $AWS_REGION --type SecureString \
  --name /probashi/ANTHROPIC_API_KEY --value 'paste-the-key-here'
```

Repeat for every secret the voice module needs once Agent 4 names them.

## Step 3 — Create the two IAM roles (once per account)

These commands are from the [Express Mode CLI tutorial](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/express-service-getting-started.html).

```bash
aws iam create-role --role-name ecsTaskExecutionRole \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ecs-tasks.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
aws iam attach-role-policy --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

aws iam create-role --role-name ecsInfrastructureRoleForExpressServices \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Sid":"AllowAccessInfrastructureForECSExpressServices","Effect":"Allow","Principal":{"Service":"ecs.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
aws iam attach-role-policy --role-name ecsInfrastructureRoleForExpressServices \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSInfrastructureRoleforExpressGatewayServices
```

Let the execution role read the secrets from step 2:

```bash
aws iam put-role-policy --role-name ecsTaskExecutionRole --policy-name probashi-read-secrets \
  --policy-document "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":\"ssm:GetParameters\",\"Resource\":\"arn:aws:ssm:$AWS_REGION:$ACCOUNT_ID:parameter/probashi/*\"}]}"
```

New roles can take about a minute to become usable. If step 4 fails with an assume-role error, wait and retry.

## Step 4 — Create the service

Replace the `CORS_ORIGINS` value with the real frontend URL.

```bash
aws ecs create-express-gateway-service --region $AWS_REGION \
  --service-name probashi-backend \
  --execution-role-arn arn:aws:iam::$ACCOUNT_ID:role/ecsTaskExecutionRole \
  --infrastructure-role-arn arn:aws:iam::$ACCOUNT_ID:role/ecsInfrastructureRoleForExpressServices \
  --cpu 512 --memory 1024 --cpu-architecture ARM64 \
  --health-check-path /health \
  --scaling-target '{"minTaskCount":1,"maxTaskCount":2}' \
  --primary-container "{
    \"image\": \"$IMAGE:$TAG\",
    \"containerPort\": 8000,
    \"environment\": [
      {\"name\": \"USE_STUBS\", \"value\": \"false\"},
      {\"name\": \"CORS_ORIGINS\", \"value\": \"https://YOUR-FRONTEND-DOMAIN\"},
      {\"name\": \"LLM_PROVIDER\", \"value\": \"anthropic\"},
      {\"name\": \"LLM_MODEL\", \"value\": \"claude-sonnet-5-5\"},
      {\"name\": \"LOG_LEVEL\", \"value\": \"INFO\"}
    ],
    \"secrets\": [
      {\"name\": \"ANTHROPIC_API_KEY\", \"valueFrom\": \"arn:aws:ssm:$AWS_REGION:$ACCOUNT_ID:parameter/probashi/ANTHROPIC_API_KEY\"}
    ]
  }" \
  --monitor-resources
```

Parameter names and formats are from the [CreateExpressGatewayService API reference](https://docs.aws.amazon.com/AmazonECS/latest/APIReference/API_CreateExpressGatewayService.html). `--health-check-path /health` matters: the default is `/ping`, which this API does not serve, so tasks would be marked unhealthy.

Prefer clicking? The [console walkthrough](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/express-service-first-run.html) asks for the same things (image, port 8000, health check path `/health`, env vars) and can create both IAM roles for you.

## Step 5 — Check it

The service URL has the form `https://probashi-backend.ecs.<region>.on.aws/`.

```bash
export API=https://probashi-backend.ecs.$AWS_REGION.on.aws
curl $API/health                 # "stubs": [] means real modules are in use
curl -X POST $API/api/check -F 'text=...'
```

Then set the frontend's `VITE_API_URL` to this URL and rebuild the frontend.

Logs go to CloudWatch Logs as one JSON object per line, with passport and visa numbers masked.

## Updating and removing

```bash
# Deploy a new version: build and push a new tag (step 1), then
aws ecs update-express-gateway-service --region $AWS_REGION \
  --service-arn arn:aws:ecs:$AWS_REGION:$ACCOUNT_ID:service/default/probashi-backend \
  --primary-container "{\"image\": \"$IMAGE:$TAG\", \"containerPort\": 8000}" --monitor-resources

# Stop paying: delete the service after the demo
aws ecs delete-express-gateway-service --region $AWS_REGION \
  --service-arn arn:aws:ecs:$AWS_REGION:$ACCOUNT_ID:service/default/probashi-backend --monitor-resources
```

TODO (unverified): the `update` and `delete` command flags above follow the naming of the create command but were not checked against the reference. Confirm with `aws ecs update-express-gateway-service help`. In particular, check whether an update keeps the existing environment and secrets or needs them passed again.

## Environment variables

| Variable | Where | Value in production | Notes |
| --- | --- | --- | --- |
| `USE_STUBS` | environment | `false` | `true` serves fake, always-amber answers. Never use `true` for real users. |
| `CORS_ORIGINS` | environment | the frontend URL | Comma-separated list. Browsers from other origins are refused. |
| `MAX_UPLOAD_MB` | environment | `10` (default) | Whole-request limit. |
| `LOG_LEVEL` | environment | `INFO` (default) | |
| `LLM_PROVIDER` | environment | `anthropic` (default) | Read by `probashi/llm.py`. |
| `LLM_MODEL` | environment | `claude-sonnet-5-5` (default) | Read by `probashi/llm.py`. |
| `ANTHROPIC_API_KEY` | **secret** | from Parameter Store | Needed when `LLM_PROVIDER=anthropic`. |
| `VOICE_STT_PROVIDER`, `VOICE_TTS_PROVIDER` | environment | TODO (Agent 4) | Plus whatever API keys those providers need, as secrets. |

## Estimated monthly cost

This is an estimate built on stated assumptions, not a quote. Check the [AWS Pricing Calculator](https://calculator.aws/) for your region before relying on it.

Assumptions:

- One task, running all month (730 hours), 0.5 vCPU and 1 GB, ARM64. No scale-out.
- Demo-level traffic: well under 1 GB of data per month, a few hundred checks.
- Fargate rates are the US East (N. Virginia) Linux/ARM rates shown on the [Fargate pricing page](https://aws.amazon.com/fargate/pricing/) when this was written: $0.0000089944 per vCPU-second and $0.0000009889 per GB-second. **Other regions, including Mumbai, have different rates.**
- Load balancer and public IPv4 figures are from memory of AWS's US East list prices and are **unverified**: confirm on the [ELB](https://aws.amazon.com/elasticloadbalancing/pricing/) and [VPC](https://aws.amazon.com/vpc/pricing/) pricing pages.
- No free tier or credits applied.

| Item | Working | Approx. per month |
| --- | --- | --- |
| Fargate task | (0.5 × $0.03238 + 1 × $0.00356) per hour × 730 h | $14 |
| Application Load Balancer | about $0.0225 per hour × 730 h, plus small usage charges (unverified) | $16–18 |
| Public IPv4 addresses | about $0.005 per hour each; assume 3 (2 for the load balancer, 1 for the task) (unverified) | $11 |
| CloudWatch Logs, ECR storage, Parameter Store | small at demo volume | under $2 |
| **AWS total** | | **roughly $45 per month** |

Not included: the LLM and speech API bills. Those depend on the providers and on how many checks are run, and will likely matter more than the AWS bill once there is real usage.

Ways to spend less: delete the service when not demoing (the load balancer is most of the idle cost), and ask about AWS credits for students or the event.

## Frontend

The frontend is Agent 5's. It is a static Vite build, so it does not need a container in production: build it with `VITE_API_URL` set to the backend URL and host the `frontend/dist` folder on any static host (for example AWS Amplify Hosting, or S3 with CloudFront). Then put that site's URL in the backend's `CORS_ORIGINS`.

## Privacy checklist for deployment

- The container has no volume and the API writes no uploads to disk.
- Do not enable load balancer access logs or request-body logging without reviewing what they capture.
- Keep `USE_STUBS=false` and check `/health` after every deploy.
