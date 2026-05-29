# ITU-MiniTwit System

## Dashboards
* **SonarCloud Static Analysis:** [View SonarCloud Dashboard](https://sonarcloud.io/project/overview?id=jskoven_Devops2026_jklo_jakst_aing_asjo_mbln)
* **Codacy Quality Assessment:** [View Codacy Dashboard](https://app.codacy.com/organizations/gh/jskoven/dashboard)
* **Production Monitoring & Telemetry (Grafana):** `http://161.35.68.148:3000` *(logs via Loki, metrics via Prometheus)*

---

## 1. Local Development

To run the system locally without interacting with cloud infrastructure, you only need **Docker** installed on your machine. 

We have a separate docker-compose file (`docker-compose.dev.yml`) that creates a local database container and handles services automatically

### Running it Locally
1. Clone the repository:
   ```bash
   git clone [https://github.com/jskoven/Devops2026_jklo_jakst_aing_asjo_mbln.git](https://github.com/jskoven/Devops2026_jklo_jakst_aing_asjo_mbln.git)
   cd Devops2026_jklo_jakst_aing_asjo_mbln
   ```
2. Build and launch the application, local database, and monitoring services in docker:
   ```bash
   docker compose -f docker-compose-dev.yml up --build
   ```
3. The services will then run on:
   * **Web Application:** `http://localhost:8080`
   * **Prometheus:** `http://localhost:9090`
   * **Loki:** Port `3100`

  If you want to remove containers and associated volumes you can run: 
   ```bash
   docker compose -f docker-compose-dev.yml down -v 
   ```


### Running Tests
1. The test suite can be run in docker as well. To run the tests first navigate to the test folder:
```bash
cd test/
```
2. From here, run the docker compose file associated with the tests. 
```
docker compose -f docker-compose.yml up --build 
```
The command will install nescessary requirements build a local application and database, and run the test against these instances. 

Once the test are finished, you want to remove the containers and volumes built in the test suite. Run the command below to do so: 

```
docker compose -f docker-compose.yml down -v 
```

---

## 2. Tech Stack
Our production environment is decoupled across multiple services:
* **Application:** FastAPI (Python 3.12)
* **Database:** A standalone PostgreSQL server separated from the application servers
* **Orchestration:** A Docker Swarm manages 3 minitwit replicas across 2 production servers using an overlay network.
* **Observability:** Promtail log shipping, Loki log aggregator, Prometheus metric scraper, and Grafana dashboards.

---

## 3. Production deployment
Because our system uses Infrastructure as Code, the production application is fully managed by the CI/CD pipeline. To replicate our exact production environment on your own, follow these steps:

### Prerequisites
1. **Infrastructure:** Start two servers running Docker for your Docker Swarm cluster (one as a Manager, one joined as a Worker), and one isolated server running PostgreSQL.
2. **GitHub Repository Secrets:** In your fork or repository, configure the following secrets:
   * `DIGITAL_OCEAN_MANAGER_IP`: The public IP address of your Swarm manager server.
   * `DEPLOYMENT_SSH_KEY`: A private SSH key allowing access to execute commands on the Manager server.
   * `DOCKER_HUB_USERNAME` / `DOCKER_HUB_TOKEN`: Credentials used to build and pull the images to DockerHub.
   * `PRODUCTION_DATABASE_URL`: The connection string pointing to your standalone PostgreSQL server.

### Automatic deployment
Once these secrets are set, pushing changes to your main branch automatically triggers the workflow in `.github/workflows/deployment.yml`. 

The pipeline will compile images via Docker Buildx, push them to Docker Hub, SSH into your cluster manager, and execute:
```bash
docker stack deploy --with-registry-auth -c docker-compose.yml minitwit
```

## 4. Automated Production Deployment (Terraform & Swarm)

### Local Tooling Requirements
Before running the deployment script, ensure you have the following components installed:
* **Terraform CLI:** 
* **Docker Engine / CLI:**
* **SSH Client Tools:** 

### Setup & Configuration

#### Generate the Project SSH Key Pair
The cluster requires a dedicated SSH key pair to create a secure connections between the droplets. Run this command from the root of the repository to generate them exactly where the scripts expect them:

```bash
mkdir -p ssh_key
ssh-keygen -t rsa -b 4096 -q -N '' -f ./ssh_key/terraform
```
*(Note: The `./secrets` configuration file and the `./ssh_key/` directory are explicitly blocked inside our `.gitignore` to prevent leaking private credentials to public version control platforms).*

#### Generate a DigitalOcean Token
1. Log in to DigitalOcean
2. Navigate to the API section on the navigation menu.
3. Under the Tokens/Keys tab, select Generate New Token.
4. Define a token name and ensure it is granted Full Access
5. Copy the generated string

#### Populate Local Secrets Environment
Create a new file named exactly `secrets` in the root of the repository. Add the following two lines, replacing the placeholder strings with your platform credentials:

```bash
export TF_VAR_do_token="your_actual_digital_ocean_api_token_here"
export DOCKER_USERNAME=jskoven
```

### System Deployment

Once your keys are generated and your secrets file is configured, the entire live platform can be built and deployed with a single command:

```bash
# Grant execution permissions to the script
chmod +x deploy.sh

# Execute the deployment
./deploy.sh
```
### Tearing Down
To dismantle the stack and remove droplets from DigitalOcean, run this command:

```bash
source secrets
terraform destroy -auto-approve
```