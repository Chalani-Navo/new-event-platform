NEW EVENT - KUBERNETES MANIFESTS

Place these files inside:
NEW-EVENT-PLATFORM/kubernetes/

IMPORTANT BEFORE APPLYING
1. Create Amazon RDS PostgreSQL.
2. Edit 02-secret-template.yaml:
   - Replace CHANGE_ME passwords.
   - Replace YOUR_RDS_ENDPOINT.
3. Deploy ClickHouse using Helm.
4. Confirm the ClickHouse Kubernetes Service name.
   - These files currently expect the host name: clickhouse
   - If Helm creates a different service name, update CLICKHOUSE_HOST in 01-configmap.yaml.
5. Install the NGINX Ingress Controller before applying 20-ingress.yaml.
6. Install Kubernetes Metrics Server before applying 30-hpa.yaml.

FRONTEND ANALYTICS IMPORTANT
Your browser cannot use localhost:5003 after cloud deployment.
Update frontend/js/analytics.js so its analytics endpoint is:

    /analytics-api/api/v1/analytics

Then rebuild and push the frontend image again:

    docker compose build frontend
    docker tag new-event-platform-frontend:latest 790304250595.dkr.ecr.ap-southeast-1.amazonaws.com/frontend:latest
    docker push 790304250595.dkr.ecr.ap-southeast-1.amazonaws.com/frontend:latest

APPLY ORDER
    kubectl apply -f 00-namespace.yaml
    kubectl apply -f 01-configmap.yaml
    kubectl apply -f 02-secret-template.yaml
    kubectl apply -f 10-frontend.yaml
    kubectl apply -f 11-event-service.yaml
    kubectl apply -f 12-program-service.yaml
    kubectl apply -f 13-registration-service.yaml
    kubectl apply -f 14-analytics-service.yaml
    kubectl apply -f 20-ingress.yaml
    kubectl apply -f 30-hpa.yaml

CHECK
    kubectl get pods -n new-event
    kubectl get services -n new-event
    kubectl get ingress -n new-event
    kubectl get hpa -n new-event

NOTE
The exact environment-variable names must match your Flask code.
These files assume:
- All three transactional services use DATABASE_URL.
- Registration Service uses EVENT_SERVICE_URL.
- Analytics Service uses CLICKHOUSE_HOST, CLICKHOUSE_PORT,
  CLICKHOUSE_DATABASE, CLICKHOUSE_USER and CLICKHOUSE_PASSWORD.
