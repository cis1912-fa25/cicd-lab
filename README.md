+++
title = "CI/CD with GitHub Actions"
date = 2025-11-13
description = "Build a complete CI/CD pipeline using GitHub Actions and Docker Hub"
+++

# CI/CD with GitHub Actions

<!-- TODO: Add GitHub Classroom link or commit hash -->

## Introduction

In this lab, we'll build a complete CI/CD pipeline for a simple FastAPI application using GitHub Actions. When you open a pull request, GitHub Actions will automatically run your tests, build your Docker image, and report the results back as a comment. When you merge to main, it will build and push your Docker image to Docker Hub, making it available for deployment anywhere (which makes this a Continuous Delivery instead of Continuous Deployment).

By the end of this lab, you'll have a better understanding of how industry teams automate their software delivery pipelines starting from pull requests to deployment ready images.

## Prerequisites

You'll need to first sign up for a Docker Hub account at <https://hub.docker.com>.

## Provided Code

Take a look through the provided code:

```text
cicd-lab/
├── app/
│   ├── __init__.py
│   └── main.py          # FastAPI application
├── tests/
│   ├── __init__.py
│   └── test_main.py     # Pytest tests
├── Dockerfile           # Container definition
├── pyproject.toml       # Python dependencies (uv)
└── README.md
```

This should be a familiar setup that uses `uv` and Docker. The FastAPI application we've provided is a simple "echo" webserver. It has two endpoints GET `/echo` and GET `/echo/<name>` that return `Hello, World!` or `Hello, <name>!`. Importantly, we've included a new folder `tests/` that implements unit tests using `pytest`. These will be used for our CI.

## Understanding the CI/CD Workflow

Before we dive into implementation, let's understand what we're building:

```mermaid
graph LR
    A[Developer pushes code] --> B[GitHub detects change]
    B --> C{Which branch?}
    C -->|Pull Request| D[CI Workflow]
    C -->|Main Branch| E[CD Workflow]

    D --> D1[Run Tests in Container]
    D1 --> D2[Build Docker Image]
    D2 --> D3[Post Results as PR Comment]

    E --> E1[Run Tests]
    E1 --> E2[Build Docker Image]
    E2 --> E3[Push to Docker Hub]
    E3 --> E4[Tag with version]
```

**Continuous Integration (CI)** runs on every pull request:

- Builds the Docker image
- Runs tests inside the container
- Reports results back to the PR

**Continuous Deployment (CD)** runs when code merges to main (after a PR lands):

- Builds the Docker image
- Runs tests to verify
- Pushes the image to Docker Hub with proper tags
- Makes the image available for deployment

## Part 1: Testing Locally

Before we automate anything, let's verify our application works locally.

```bash
# build the docker image
docker build -t echo-api:local .
# run the container
docker run -d -p 8000:8000 --name echo-api echo-api:local
# test the endpoints
curl http://localhost:8000/echo
curl http://localhost:8000/echo/Student
```

You should see the output:

```bash
{"message":"Hello, World!"}
{"message":"Hello, Student!"}
```

**Run the tests:**

Now, let's run the pytest suite. First, install dependencies locally:

```bash
uv sync
```

Then run pytest:

```bash
uv run pytest -v
```

Pytest will automatically look for any tests in our directory and execute them. The `-v` is simply to print verbose output. You can read more about [pytest at its documentation](https://docs.pytest.org/en/stable/index.html) if you're interested. You should see something like:

```bash
tests/test_main.py::test_echo PASSED
tests/test_main.py::test_echo_name PASSED

====== 2 passed in 0.24s ======
```

**Clean up:**

```bash
docker stop echo-api
docker rm echo-api
```

Great! Now that we know everything works locally, let's automate this with GitHub Actions.

## Part 2: Creating the CI Workflow

GitHub Actions workflows are defined in YAML files under `.github/workflows/`. This is the beauty of GitHub Actions, we don't need to spin up any additional infrastructure to run our CI/CD pipelines, GitHub handles all of it for us automatically based on the files we define! Otherwise, you would need to spin up various pieces of infrastructure, such as nodes to watch the repository and worker nodes to execute each step in the pipelines.

Let's create our first workflow. First, create the github workflow directory:

```bash
mkdir -p .github/workflows
```

Then, create a file `.github/workflows/ci.yaml` and put the following inside:

```yaml
name: CI - Pull Request Checks

on:
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v5

      - name: Install uv
        uses: astral-sh/setup-uv@v6

      - name: Install project
        run: uv sync --locked --all-extras --dev

      - name: Run unit tests
        run: |
          uv run pytest -v

      - name: Build Docker image
        run: |
          docker build -t echo-api:test .
```

Let's break down what this workflow does:

**Trigger**: This is the `on:` object. Runs automatically when a pull request targets the main branch.

**Job**: Defines a single job `test:`. Runs on GitHub's Ubuntu runners (free for public repos). This job has multiple steps:

1. **Checkout code**: Gets your repository code using an action provided by GitHub
2. **Install uv**: Installs uv using an action provided by Astral
3. **Install project**: Runs uv sync to install dependencies for our project
4. **Run unit tests**: Runs pytest to execute unit tests
5. **Build Docker image**: Builds image using Docker

If you're interested, the [workflow syntax documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax) may be helpful in understanding what's happening exactly as well as what is possible.

**Commit and push this workflow:**

```bash
git add .github/workflows/ci.yaml
git commit -m "Add CI workflow for pull requests"
git push origin main
```

By pushing this to our repository, we've effectively deployed our GitHub workflow!

## Part 3: Testing the CI Workflow

Now let's see our CI in action. We'll create a pull request and watch GitHub Actions work.

**Create a new branch:**

```bash
git checkout -b add-health-endpoint
```

**Add a health check endpoint to `app/main.py`:**

```python
@app.get("/health")
def health():
    return {"status": "healthy"}
```

**Add a test for the new endpoint in `tests/test_main.py`:**

```python
def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
```

**Commit and push:**

```bash
git add app/main.py tests/test_main.py
git commit -m "Add health check endpoint"
git push origin add-health-endpoint
```

**Create a pull request:**

- Go to your repository on GitHub
- Click "Pull requests" → "New pull request"
- Select your `add-health-endpoint` branch
- Click "Create pull request"

**Watch the workflow run:**

- You'll see a yellow dot next to your commit that changes to a green checkmark (or red X if it fails)
- Click "Details" to see the full workflow execution logs
- You should see all steps complete successfully

This is great, but wouldn't it be nice to see the test results directly in the PR? Let's add that.

## Part 4: Adding PR Comments with Test Results

We'll enhance our CI workflow to post test results as a comment on the PR. This gives reviewers immediate visibility into what passed or failed.

**Update `.github/workflows/ci.yaml`:**

```yaml
name: CI - Pull Request Checks

on:
  pull_request:
    branches: [ main ]

permissions:
  contents: read
  pull-requests: write

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Build Docker image
        run: |
          docker build -t echo-api:test .

      - name: Run container
        run: |
          docker run -d -p 8000:8000 --name echo-api echo-api:test
          sleep 3

      - name: Install test dependencies
        run: |
          pip install pytest httpx

      - name: Run tests and capture output
        id: pytest
        run: |
          set +e  # Don't exit on failure
          pytest tests/ -v --tb=short > test_output.txt 2>&1
          TEST_EXIT_CODE=$?
          echo "exit_code=$TEST_EXIT_CODE" >> $GITHUB_OUTPUT
          cat test_output.txt
          exit $TEST_EXIT_CODE

      - name: Post test results to PR
        if: always()
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const testOutput = fs.readFileSync('test_output.txt', 'utf8');
            const exitCode = '${{ steps.pytest.outputs.exit_code }}';
            const status = exitCode === '0' ? '✅ All tests passed!' : '❌ Tests failed';

            const body = `## ${status}

            <details>
            <summary>Test Results</summary>

            \`\`\`
            ${testOutput}
            \`\`\`

            </details>`;

            github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: body
            });
```

**What changed?**

1. **Permissions**: Added `pull-requests: write` so the workflow can comment on PRs.
2. **Run tests step**: Now captures output to a file and stores the exit code.
3. **Post results step**: Uses GitHub's script action to post a formatted comment with test results.
4. **if: always()**: Ensures the comment is posted even if tests fail. Otherwise, any steps after a step fails will not run.

**Commit and push the update:**
```bash
git checkout main
git pull
git checkout add-health-endpoint
git merge main
git add .github/workflows/ci.yml
git commit -m "Add test results commenting to CI"
git push
```

Go back to your PR and watch the new workflow run. When it completes, you should see a comment appear with your test results!

## Part 5: Setting up CD

Before we can push images to Docker Hub, we need to do some configuration to get GitHub Actions a token to use.

**Create a Docker Hub access token:**
1. Log in to https://hub.docker.com
2. Click your username → "Account Settings"
3. Go to "Security" → "New Access Token"
4. Name it "github-actions" and click "Generate"
5. **Copy the token immediately** (you won't see it again)

**Create a repository on Docker Hub:**
1. Go to "Repositories" → "Create Repository"
2. Name it `echo-api` (or whatever you prefer)
3. Set visibility to "Public"
4. Click "Create"

These secrets are encrypted and only available to your workflows. You should never commit credentials to your repository!

## Part 6: Creating the CD Workflow

Now let's create a separate workflow that runs when code is merged to main. This will build and push our Docker image to Docker Hub.

**Create `.github/workflows/cd.yml`:**

```yaml
name: CD - Deploy to Docker Hub

on:
  push:
    branches: [ main ]

jobs:
  build-and-push:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v5

      - name: Install uv
        uses: astral-sh/setup-uv@v6

      - name: Install project
        run: uv sync --locked --all-extras --dev

      - name: Run unit tests
        run: uv run pytest -v

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_TOKEN }}

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ secrets.DOCKER_USERNAME }}/echo-api:latest
```

This workflow begins quite similarly to what we have defined for our CI workflow. Namely, we install uv and dependencies, then run tests. However, then, we additionally build

**Trigger**: Runs on every push to main (i.e., when PRs are merged)

**Docker Buildx**: Advanced builder with better caching and multi-platform support

**Login**: Authenticates to Docker Hub using your secrets

**Metadata extraction**: Automatically generates image tags:
- `main-<git-sha>`: Unique tag for this commit
- `latest`: Always points to the most recent main build

**Build and test**: Runs tests before pushing (safety check)

**Build and push**: Uses GitHub Actions cache to speed up builds

**Commit the CD workflow:**
```bash
git checkout main
git pull
git add .github/workflows/cd.yml
git commit -m "Add CD workflow for Docker Hub deployment"
git push origin main
```

## Part 7: Watching the Full Pipeline

Now let's see the complete CI/CD pipeline in action!

**Merge your pull request:**
- Go to your PR on GitHub
- Click "Merge pull request"
- Confirm the merge

**Watch what happens:**

1. **CI workflow completes** on the PR (should already be green)
2. **CD workflow triggers** automatically when main is updated
3. **Go to Actions tab** and watch the "CD - Deploy to Docker Hub" workflow

When it completes:
- Go to Docker Hub → Your repository
- You should see two tags:
  - `latest`
  - `main-<commit-sha>`

**Test the deployed image:**

Anyone can now pull and run your image:

```bash
docker pull <your-dockerhub-username>/echo-api:latest
docker run -d -p 8000:8000 --name production-api <your-dockerhub-username>/echo-api:latest
curl http://localhost:8000/health
```

You should see:
```json
{"status":"healthy"}
```

This is a production-ready image that was automatically built, tested, and deployed by your CI/CD pipeline!

## Understanding the Complete Pipeline

Let's trace what happens from code to deployment:

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant GH as GitHub
    participant CI as CI Workflow
    participant CD as CD Workflow
    participant DH as Docker Hub
    participant Prod as Production

    Dev->>GH: Push branch & open PR
    GH->>CI: Trigger CI workflow
    CI->>CI: Build Docker image
    CI->>CI: Run tests in container
    CI->>GH: Post test results as comment

    Dev->>GH: Merge PR to main
    GH->>CD: Trigger CD workflow
    CD->>CD: Build Docker image
    CD->>CD: Run tests
    CD->>DH: Push image with tags

    Prod->>DH: Pull latest image
    Prod->>Prod: Deploy container
```

**Why this architecture matters:**

1. **Fast Feedback**: Developers see test results immediately on PRs
2. **Quality Gates**: Nothing reaches main without passing tests
3. **Automation**: Zero manual steps from commit to deployment
4. **Reproducibility**: Every build is identical and traceable
5. **Rollback**: Can deploy any previous version using commit SHA tags

## Real-World Extensions

In production environments, you'd typically extend this pipeline with:

**Security Scanning**:
```yaml
- name: Run Trivy security scan
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: ${{ secrets.DOCKER_USERNAME }}/echo-api:latest
    format: 'sarif'
    output: 'trivy-results.sarif'
```

**Code Coverage**:
```yaml
- name: Generate coverage report
  run: |
    pytest tests/ --cov=app --cov-report=html

- name: Upload coverage to PR
  # Post coverage percentage as PR comment
```

**Multi-environment Deployment**:
- Deploy to staging automatically on main
- Deploy to production with manual approval
- Use different tags for different environments

**Kubernetes Integration**:
- Update Kubernetes manifests with new image tags
- Trigger ArgoCD or Flux to sync changes
- Automated canary or blue-green deployments

## Cleanup

**Stop and remove local containers:**
```bash
docker stop production-api
docker rm production-api
```

**Optional - Remove Docker images:**
```bash
docker rmi echo-api:local
docker rmi echo-api:test
docker rmi <your-dockerhub-username>/echo-api:latest
```

**Keep your GitHub repository** - this is a portfolio piece showing you understand CI/CD!

## Key Takeaways

You've built a complete CI/CD pipeline that:

✅ Automatically tests every pull request
✅ Posts test results as PR comments
✅ Builds and pushes Docker images on merge
✅ Tags images with commit SHAs for traceability
✅ Uses GitHub Actions cache for faster builds
✅ Manages secrets securely

This is the foundation of how professional teams ship software. Every code change is automatically validated, built, and made ready for deployment. No manual steps, no "it works on my machine" problems, just reliable, repeatable delivery.

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Build Push Action](https://github.com/docker/build-push-action)
- [Docker Hub Quickstart](https://docs.docker.com/docker-hub/quickstart/)
- [FastAPI Testing Guide](https://fastapi.tiangolo.com/tutorial/testing/)
- [Semantic Versioning](https://semver.org/)
