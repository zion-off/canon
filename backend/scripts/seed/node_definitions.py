"""Seed data node definitions for the Canon knowledge graph.

26 nodes representing a realistic engineering organization's knowledge base,
centered around a payment service cascade failure narrative.
"""

TENANT_ID = "6a1b487792af37cb4bc76910"

# Services
PAYMENTS_SERVICE = "aa0000000000000000000001"
ORDER_SERVICE = "aa0000000000000000000002"
INVENTORY_SERVICE = "aa0000000000000000000003"
NOTIFICATION_SERVICE = "aa0000000000000000000004"
API_GATEWAY = "aa0000000000000000000005"

# Incidents
CASCADE_FAILURE = "bb0000000000000000000001"
REDIS_SPLIT_BRAIN = "bb0000000000000000000002"
API_GATEWAY_MEMORY_LEAK = "bb0000000000000000000003"

# Conventions
EXPONENTIAL_BACKOFF = "cc0000000000000000000001"
GRPC_COMMUNICATION = "cc0000000000000000000002"
CIRCUIT_BREAKER = "cc0000000000000000000003"

# Decisions
EVENT_SOURCING = "dd0000000000000000000001"
GRPC_STANDARD = "dd0000000000000000000002"
CIRCUIT_BREAKER_ADOPTION = "dd0000000000000000000003"
EXPONENTIAL_BACKOFF_RETRIES = "dd0000000000000000000004"
API_GATEWAY_UNIFIED = "dd0000000000000000000005"
IDEMPOTENT_CONSUMERS = "dd0000000000000000000006"

# Teams
PLATFORM_TEAM = "ee0000000000000000000001"
PAYMENTS_TEAM = "ee0000000000000000000002"

# Knowledge
DEPLOYMENT_ARCH = "ff0000000000000000000001"
ONCALL_ROTATION = "ff0000000000000000000002"
INCIDENT_RUNBOOK = "ff0000000000000000000003"

# Projects
PAYMENTS_V2 = "a10000000000000000000001"
INVENTORY_CB_ROLLOUT = "a10000000000000000000002"
NOTIFICATION_WEBSOCKET = "a10000000000000000000003"
REDIS_UPGRADE = "a10000000000000000000004"

# New nodes for better clustering
PAYMENT_PROVIDERS = "aa0000000000000000000006"  # Payment provider integrations
AUTH_SERVICE = "aa0000000000000000000007"  # Authentication service
JWT_VALIDATION = "cc0000000000000000000004"  # JWT validation convention
EVENT_SCHEMA_REGISTRY = "dd0000000000000000000007"  # Event schema registry decision
LOAD_TESTING = "ff0000000000000000000004"  # Load testing setup


NODES = [
    # === SERVICES (5) ===
    {
        "_id": PAYMENTS_SERVICE,
        "name": "Payments service",
        "description": "Core payment processing service handling transactions, refunds, and payment method validation",
        "content": "Handles all payment operations including authorization, capture, and refunds. Integrates with Stripe and PayPal gateways. Critical path for order completion flow.",
        "status": "active",
        "tags": ["service", "backend", "payments"],
        "related_entity_ids": [
            ORDER_SERVICE,
            NOTIFICATION_SERVICE,
            CASCADE_FAILURE,
            PAYMENTS_TEAM,
            PAYMENTS_V2,
        ],
        "metadata": {
            "criticality": "high",
            "dependencies": ["order-service", "notification-service"],
            "team": "payments",
        },
        "createdAt": "2024-08-15T10:00:00+00:00",
        "updatedAt": "2025-01-20T14:30:00+00:00",
    },
    {
        "_id": ORDER_SERVICE,
        "name": "Order service",
        "description": "Manages order lifecycle from creation through fulfillment using event sourcing pattern",
        "content": "Orchestrates order workflow including inventory checks, payment processing, and fulfillment. Uses Kafka for event-driven architecture. Emits order lifecycle events consumed by downstream services.",
        "status": "active",
        "tags": ["service", "backend", "orders"],
        "related_entity_ids": [
            PAYMENTS_SERVICE,
            INVENTORY_SERVICE,
            CASCADE_FAILURE,
            EVENT_SOURCING,
            GRPC_STANDARD,
        ],
        "metadata": {
            "criticality": "high",
            "dependencies": ["payments-service", "inventory-service"],
            "team": "platform",
            "architecture": "event-sourcing",
        },
        "createdAt": "2024-08-15T10:00:00+00:00",
        "updatedAt": "2025-01-15T09:20:00+00:00",
    },
    {
        "_id": INVENTORY_SERVICE,
        "name": "Inventory service",
        "description": "Real-time inventory tracking and reservation system with circuit breaker protection",
        "content": "Manages stock levels across multiple warehouses. Provides reservation API for order service. Implements circuit breaker pattern to prevent cascade failures during high load.",
        "status": "active",
        "tags": ["service", "backend", "inventory"],
        "related_entity_ids": [
            CIRCUIT_BREAKER,
            INVENTORY_CB_ROLLOUT,
        ],
        "metadata": {
            "criticality": "high",
            "dependencies": [],
            "team": "platform",
            "pattern": "circuit-breaker",
        },
        "createdAt": "2024-08-15T10:00:00+00:00",
        "updatedAt": "2025-01-18T16:45:00+00:00",
    },
    {
        "_id": NOTIFICATION_SERVICE,
        "name": "Notification service",
        "description": "Multi-channel notification delivery system handling email, SMS, and push notifications",
        "content": "Consumes events from payment and order services to send user notifications. Supports email (SendGrid), SMS (Twilio), and push notifications. Currently migrating from polling to WebSocket-based event consumption.",
        "status": "active",
        "tags": ["service", "backend", "notifications"],
        "related_entity_ids": [
            PAYMENTS_SERVICE,
            NOTIFICATION_WEBSOCKET,
        ],
        "metadata": {
            "criticality": "medium",
            "dependencies": ["payments-service"],
            "team": "platform",
        },
        "createdAt": "2024-09-01T11:00:00+00:00",
        "updatedAt": "2025-01-22T10:15:00+00:00",
    },
    {
        "_id": API_GATEWAY,
        "name": "API gateway",
        "description": "Unified entry point for all client requests providing authentication, rate limiting, and request routing",
        "content": "Kong-based API gateway handling all external traffic. Implements JWT validation, rate limiting, and request transformation. Routes to backend microservices via gRPC. Recently recovered from memory leak incident.",
        "status": "active",
        "tags": ["service", "backend", "gateway"],
        "related_entity_ids": [
            API_GATEWAY_UNIFIED,
            API_GATEWAY_MEMORY_LEAK,
        ],
        "metadata": {
            "criticality": "high",
            "dependencies": [],
            "team": "platform",
            "technology": "Kong",
        },
        "createdAt": "2024-08-20T13:00:00+00:00",
        "updatedAt": "2025-01-25T11:30:00+00:00",
    },
    
    # === INCIDENTS (3) ===
    {
        "_id": CASCADE_FAILURE,
        "name": "Payment timeout cascade failure",
        "description": "SEV-1 incident where naive fixed-delay retries caused thundering herd, taking down payment, order, and inventory services",
        "content": "Payment service used 500ms fixed-delay retries without jitter during inventory slowness. Created synchronized retry storm amplifying load 40x. All three services became unresponsive for 20 minutes. Manual circuit breaker engagement required.",
        "status": "resolved",
        "tags": ["incident", "outage", "cascade failure", "retry storm"],
        "related_entity_ids": [
            PAYMENTS_SERVICE,
            ORDER_SERVICE,
            INVENTORY_SERVICE,
            EXPONENTIAL_BACKOFF,
            EXPONENTIAL_BACKOFF_RETRIES,
            INCIDENT_RUNBOOK,
        ],
        "metadata": {
            "severity": "SEV-1",
            "rootCause": "Fixed-delay retries without jitter caused thundering herd",
            "duration": "20 minutes",
            "date": "2025-01-08",
            "impact": "Payment, order, and inventory services unavailable",
        },
        "createdAt": "2025-01-08T14:30:00+00:00",
        "updatedAt": "2025-01-09T11:00:00+00:00",
    },
    {
        "_id": REDIS_SPLIT_BRAIN,
        "name": "Redis cluster split-brain",
        "description": "Network partition caused Redis cluster to accept writes on both sides, resulting in data inconsistency",
        "content": "Network switch failure partitioned Redis cluster. Both partitions elected masters and accepted writes for 8 minutes. Required manual reconciliation of conflicting keys. Led to Redis 6 to 7 upgrade with improved partition handling.",
        "status": "resolved",
        "tags": ["incident", "outage", "data consistency"],
        "related_entity_ids": [
            REDIS_UPGRADE,
            INCIDENT_RUNBOOK,
        ],
        "metadata": {
            "severity": "SEV-2",
            "rootCause": "Network partition with insufficient quorum configuration",
            "duration": "8 minutes write conflict window",
            "date": "2024-11-15",
            "dataLoss": "12 conflicting keys required manual merge",
        },
        "createdAt": "2024-11-15T16:20:00+00:00",
        "updatedAt": "2024-11-20T09:00:00+00:00",
    },
    {
        "_id": API_GATEWAY_MEMORY_LEAK,
        "name": "API gateway memory leak",
        "description": "Connection pool exhaustion in Kong gateway caused by unclosed HTTP connections during high traffic",
        "content": "Memory usage grew linearly with request volume due to connection pool not releasing idle connections. Gateway OOM-killed after 6 hours of peak traffic. Fixed by configuring connection TTL and pool size limits. Influenced API gateway unified entry decision.",
        "status": "resolved",
        "tags": ["incident", "outage", "memory leak"],
        "related_entity_ids": [
            API_GATEWAY,
            API_GATEWAY_UNIFIED,
            INCIDENT_RUNBOOK,
        ],
        "metadata": {
            "severity": "SEV-2",
            "rootCause": "Kong connection pool not releasing idle connections",
            "duration": "6 hours until OOM",
            "date": "2024-12-03",
            "fix": "Configured connection TTL and max pool size",
        },
        "createdAt": "2024-12-03T08:45:00+00:00",
        "updatedAt": "2024-12-05T14:20:00+00:00",
    },
    
    # === CONVENTIONS (3) ===
    {
        "_id": EXPONENTIAL_BACKOFF,
        "name": "Exponential backoff with jitter",
        "description": "Retry pattern using exponential delays with random jitter to prevent thundering herd in distributed systems",
        "content": "All retry logic must use exponential backoff (base * 2^attempt) plus random jitter (0-25% of delay). Prevents synchronized retry storms. Adopted after cascade failure incident demonstrated danger of fixed-delay retries.",
        "status": "active",
        "tags": ["convention", "architecture", "retry"],
        "related_entity_ids": [
            CASCADE_FAILURE,
            EXPONENTIAL_BACKOFF_RETRIES,
        ],
        "metadata": {
            "rationale": "Prevents thundering herd from synchronized retries",
            "adoptionDate": "2025-01-15",
        },
        "createdAt": "2025-01-15T10:00:00+00:00",
        "updatedAt": "2025-01-15T10:00:00+00:00",
    },
    {
        "_id": GRPC_COMMUNICATION,
        "name": "gRPC for inter-service communication",
        "description": "Standard protocol for service-to-service calls providing type safety, performance, and built-in load balancing",
        "content": "All inter-service communication uses gRPC with Protocol Buffers. Provides strong typing via .proto files, efficient binary serialization, and HTTP/2 multiplexing. Replaced REST/JSON for internal APIs.",
        "status": "active",
        "tags": ["convention", "architecture", "communication"],
        "related_entity_ids": [
            GRPC_STANDARD,
        ],
        "metadata": {
            "benefits": ["Type safety", "Performance", "Built-in load balancing"],
            "adoptionDate": "2024-10-01",
        },
        "createdAt": "2024-10-01T09:00:00+00:00",
        "updatedAt": "2024-10-01T09:00:00+00:00",
    },
    {
        "_id": CIRCUIT_BREAKER,
        "name": "Circuit breaker on critical paths",
        "description": "Fault isolation pattern that prevents cascade failures by failing fast when downstream services are unhealthy",
        "content": "All critical service dependencies must implement circuit breakers. Three states: closed (normal), open (failing fast), half-open (testing recovery). Prevents cascade failures by stopping requests to unhealthy services.",
        "status": "active",
        "tags": ["convention", "architecture", "resilience"],
        "related_entity_ids": [
            CIRCUIT_BREAKER_ADOPTION,
            INVENTORY_SERVICE,
        ],
        "metadata": {
            "states": ["closed", "open", "half-open"],
            "adoptionDate": "2024-11-20",
        },
        "createdAt": "2024-11-20T11:00:00+00:00",
        "updatedAt": "2024-11-20T11:00:00+00:00",
    },
    
    # === DECISIONS (6) ===
    {
        "_id": EVENT_SOURCING,
        "name": "Event sourcing for orders",
        "description": "ADR-042: Adopt event sourcing with Kafka for order lifecycle to enable audit trail and event-driven integrations",
        "content": "Store order state as immutable event stream in Kafka rather than mutable database rows. Enables complete audit trail, temporal queries, and event-driven integrations. Services must implement idempotent consumers.",
        "status": "active",
        "tags": ["decision", "architecture", "event sourcing", "orders"],
        "related_entity_ids": [
            ORDER_SERVICE,
            IDEMPOTENT_CONSUMERS,
        ],
        "metadata": {
            "adrNumber": 42,
            "rationale": "Audit trail and event-driven architecture",
            "tradeoffs": "Increased complexity, eventual consistency",
            "decidedDate": "2024-09-15",
        },
        "createdAt": "2024-09-15T14:00:00+00:00",
        "updatedAt": "2024-09-15T14:00:00+00:00",
    },
    {
        "_id": GRPC_STANDARD,
        "name": "gRPC as standard",
        "description": "ADR-038: Standardize on gRPC for all inter-service communication replacing REST/JSON internal APIs",
        "content": "All new services must use gRPC. Existing REST services migrate during next major refactor. Provides type safety, performance, and consistent API contracts across platform.",
        "status": "active",
        "tags": ["decision", "architecture", "communication"],
        "related_entity_ids": [
            GRPC_COMMUNICATION,
            ORDER_SERVICE,
            INVENTORY_SERVICE,
        ],
        "metadata": {
            "adrNumber": 38,
            "rationale": "Type safety and performance over REST",
            "decidedDate": "2024-09-20",
        },
        "createdAt": "2024-09-20T10:30:00+00:00",
        "updatedAt": "2024-09-20T10:30:00+00:00",
    },
    {
        "_id": CIRCUIT_BREAKER_ADOPTION,
        "name": "Circuit breaker adoption",
        "description": "ADR-045: Mandate circuit breakers on all critical service dependencies to prevent cascade failures",
        "content": "All services calling external or critical dependencies must implement circuit breakers. Use Hystrix or Resilience4j. Configure based on service SLOs. Rollout tracked via project milestones.",
        "status": "active",
        "tags": ["decision", "architecture", "resilience"],
        "related_entity_ids": [
            CIRCUIT_BREAKER,
            INVENTORY_CB_ROLLOUT,
        ],
        "metadata": {
            "adrNumber": 45,
            "rationale": "Prevent cascade failures across platform",
            "decidedDate": "2024-11-20",
        },
        "createdAt": "2024-11-20T15:00:00+00:00",
        "updatedAt": "2024-11-20T15:00:00+00:00",
    },
    {
        "_id": EXPONENTIAL_BACKOFF_RETRIES,
        "name": "Exponential backoff retries",
        "description": "ADR-047: Mandate exponential backoff with jitter for all retry logic to prevent thundering herd scenarios",
        "content": "All retry implementations must use exponential backoff with jitter. Fixed-delay retries are prohibited. Base delay and max attempts configurable per service. Adopted in response to cascade failure incident.",
        "status": "active",
        "tags": ["decision", "architecture", "retry"],
        "related_entity_ids": [
            EXPONENTIAL_BACKOFF,
            CASCADE_FAILURE,
            PAYMENTS_V2,
        ],
        "metadata": {
            "adrNumber": 47,
            "rationale": "Prevent thundering herd from synchronized retries",
            "decidedDate": "2025-01-15",
        },
        "createdAt": "2025-01-15T11:00:00+00:00",
        "updatedAt": "2025-01-15T11:00:00+00:00",
    },
    {
        "_id": API_GATEWAY_UNIFIED,
        "name": "API gateway unified entry",
        "description": "ADR-041: Consolidate all client traffic through single Kong gateway for consistent auth, rate limiting, and observability",
        "content": "All external API traffic routes through unified Kong gateway. Provides centralized authentication, rate limiting, request transformation, and observability. Influenced by memory leak incident that highlighted need for proper connection management.",
        "status": "active",
        "tags": ["decision", "architecture", "gateway"],
        "related_entity_ids": [
            API_GATEWAY,
            API_GATEWAY_MEMORY_LEAK,
        ],
        "metadata": {
            "adrNumber": 41,
            "rationale": "Centralized control and observability",
            "decidedDate": "2024-10-10",
        },
        "createdAt": "2024-10-10T13:00:00+00:00",
        "updatedAt": "2024-10-10T13:00:00+00:00",
    },
    {
        "_id": IDEMPOTENT_CONSUMERS,
        "name": "Idempotent event consumers",
        "description": "ADR-043: All event consumers must be idempotent to handle at-least-once delivery from Kafka",
        "content": "Event consumers must handle duplicate messages gracefully. Use deduplication keys or idempotent operations. Required because Kafka provides at-least-once delivery guarantee.",
        "status": "active",
        "tags": ["decision", "architecture", "event sourcing"],
        "related_entity_ids": [
            EVENT_SOURCING,
        ],
        "metadata": {
            "adrNumber": 43,
            "rationale": "Handle at-least-once delivery from Kafka",
            "decidedDate": "2024-09-18",
        },
        "createdAt": "2024-09-18T10:00:00+00:00",
        "updatedAt": "2024-09-18T10:00:00+00:00",
    },
    
    # === TEAMS (2) ===
    {
        "_id": PLATFORM_TEAM,
        "name": "Platform team",
        "description": "Engineering team owning core infrastructure, shared services, and platform-wide architectural decisions",
        "content": "Responsible for API gateway, order service, inventory service, and shared infrastructure. Manages deployment pipelines and on-call rotation. Drives platform-wide conventions and decisions.",
        "status": "active",
        "tags": ["team", "platform"],
        "related_entity_ids": [
            ORDER_SERVICE,
            INVENTORY_SERVICE,
            API_GATEWAY,
            DEPLOYMENT_ARCH,
            ONCALL_ROTATION,
            INCIDENT_RUNBOOK,
        ],
        "metadata": {
            "headcount": 8,
            "focus": "Core infrastructure and shared services",
        },
        "createdAt": "2024-08-01T09:00:00+00:00",
        "updatedAt": "2025-01-10T10:00:00+00:00",
    },
    {
        "_id": PAYMENTS_TEAM,
        "name": "Payments team",
        "description": "Specialized team owning payment processing, fraud detection, and payment provider integrations",
        "content": "Owns payments service and all payment-related functionality. Manages Stripe and PayPal integrations. Currently driving payments v2 migration to adopt exponential backoff and improve resilience.",
        "status": "active",
        "tags": ["team", "payments"],
        "related_entity_ids": [
            PAYMENTS_SERVICE,
            PAYMENTS_V2,
        ],
        "metadata": {
            "headcount": 5,
            "focus": "Payment processing and provider integrations",
        },
        "createdAt": "2024-08-01T09:00:00+00:00",
        "updatedAt": "2025-01-20T09:00:00+00:00",
    },
    
    # === KNOWLEDGE (3) ===
    {
        "_id": DEPLOYMENT_ARCH,
        "name": "Deployment architecture",
        "description": "Kubernetes-based microservices deployment with Istio service mesh, GitOps via ArgoCD, and multi-region active-active setup",
        "content": "All services deploy to Kubernetes clusters managed by platform team. Istio provides service mesh for traffic management and observability. ArgoCD handles GitOps deployments. Production runs active-active across us-east-1 and us-west-2.",
        "status": "active",
        "tags": ["knowledge", "infrastructure", "deployment"],
        "related_entity_ids": [
            PLATFORM_TEAM,
        ],
        "metadata": {
            "technology": ["Kubernetes", "Istio", "ArgoCD"],
            "regions": ["us-east-1", "us-west-2"],
        },
        "createdAt": "2024-08-10T11:00:00+00:00",
        "updatedAt": "2025-01-05T14:00:00+00:00",
    },
    {
        "_id": ONCALL_ROTATION,
        "name": "On-call rotation",
        "description": "Weekly on-call rotation across platform team with PagerDuty escalation and 15-minute response SLA",
        "content": "Platform team members rotate weekly on-call duty. PagerDuty handles alerting and escalation. SEV-1 requires 15-minute response, SEV-2 requires 1 hour. On-call engineer follows incident response runbook.",
        "status": "active",
        "tags": ["knowledge", "operations", "on-call"],
        "related_entity_ids": [
            PLATFORM_TEAM,
            INCIDENT_RUNBOOK,
        ],
        "metadata": {
            "rotation": "Weekly",
            "sla": {"SEV-1": "15 minutes", "SEV-2": "1 hour"},
        },
        "createdAt": "2024-08-05T10:00:00+00:00",
        "updatedAt": "2025-01-12T09:00:00+00:00",
    },
    {
        "_id": INCIDENT_RUNBOOK,
        "name": "Incident response runbook",
        "description": "Step-by-step procedures for responding to SEV-1 and SEV-2 incidents including communication templates and escalation paths",
        "content": "Standardized incident response process: detect, assess, mitigate, resolve, post-mortem. Includes communication templates for stakeholders, escalation paths to engineering leadership, and post-incident review requirements.",
        "status": "active",
        "tags": ["knowledge", "operations", "incident response"],
        "related_entity_ids": [
            CASCADE_FAILURE,
            REDIS_SPLIT_BRAIN,
            API_GATEWAY_MEMORY_LEAK,
            PLATFORM_TEAM,
            ONCALL_ROTATION,
        ],
        "metadata": {
            "process": ["Detect", "Assess", "Mitigate", "Resolve", "Post-mortem"],
            "lastUpdated": "2025-01-10",
        },
        "createdAt": "2024-08-05T11:00:00+00:00",
        "updatedAt": "2025-01-10T15:00:00+00:00",
    },
    
    # === PROJECTS (4) ===
    {
        "_id": PAYMENTS_V2,
        "name": "Migrate payments to v2",
        "description": "Refactoring payments service to adopt exponential backoff retries and improve error handling based on cascade failure lessons",
        "content": "Replacing naive fixed-delay retries with exponential backoff plus jitter. Adding circuit breakers for external payment providers. Improving observability with distributed tracing. Target completion Q1 2025.",
        "status": "in_progress",
        "tags": ["project", "migration", "payments"],
        "related_entity_ids": [
            PAYMENTS_SERVICE,
            PAYMENTS_TEAM,
            EXPONENTIAL_BACKOFF_RETRIES,
        ],
        "metadata": {
            "targetDate": "2025-03-31",
            "progress": "65%",
            "driver": "Cascade failure incident response",
        },
        "createdAt": "2025-01-20T10:00:00+00:00",
        "updatedAt": "2025-01-25T16:00:00+00:00",
    },
    {
        "_id": INVENTORY_CB_ROLLOUT,
        "name": "Inventory circuit breaker rollout",
        "description": "Implementing circuit breakers on all inventory service dependencies per ADR-045 to prevent cascade failures",
        "content": "Adding Resilience4j circuit breakers to inventory service calls. Configuring thresholds based on service SLOs. Testing failure scenarios in staging. Rollout tracked as part of platform-wide circuit breaker adoption.",
        "status": "in_progress",
        "tags": ["project", "migration", "resilience"],
        "related_entity_ids": [
            INVENTORY_SERVICE,
            CIRCUIT_BREAKER_ADOPTION,
        ],
        "metadata": {
            "targetDate": "2025-02-28",
            "progress": "80%",
            "technology": "Resilience4j",
        },
        "createdAt": "2024-12-01T09:00:00+00:00",
        "updatedAt": "2025-01-22T11:00:00+00:00",
    },
    {
        "_id": NOTIFICATION_WEBSOCKET,
        "name": "Notification websocket migration",
        "description": "Migrating notification service from polling-based to WebSocket-based event consumption for real-time delivery",
        "content": "Replacing 5-second polling with persistent WebSocket connections to Kafka. Reduces notification latency from 5s average to sub-100ms. Improves resource utilization by eliminating constant polling.",
        "status": "in_progress",
        "tags": ["project", "migration", "notifications"],
        "related_entity_ids": [
            NOTIFICATION_SERVICE,
        ],
        "metadata": {
            "targetDate": "2025-02-15",
            "progress": "45%",
            "benefit": "Reduce latency from 5s to <100ms",
        },
        "createdAt": "2024-12-15T10:00:00+00:00",
        "updatedAt": "2025-01-18T14:00:00+00:00",
    },
    {
        "_id": REDIS_UPGRADE,
        "name": "Redis 6 to 7 upgrade",
        "description": "Upgrading Redis clusters from version 6 to 7 to improve partition handling and add new data structure support",
        "content": "Redis 7 provides better split-brain handling with improved quorum configuration. Adds support for new data structures needed by order service. Migration completed successfully with zero downtime using blue-green deployment.",
        "status": "completed",
        "tags": ["project", "migration", "infrastructure"],
        "related_entity_ids": [
            REDIS_SPLIT_BRAIN,
        ],
        "metadata": {
            "completedDate": "2025-01-05",
            "benefit": "Improved partition handling and new data structures",
            "downtime": "Zero (blue-green deployment)",
        },
        "createdAt": "2024-11-20T09:00:00+00:00",
        "updatedAt": "2025-01-05T17:00:00+00:00",
    },
    
    # === NEW NODES FOR BETTER CLUSTERING ===
    {
        "_id": PAYMENT_PROVIDERS,
        "name": "Payment provider integrations",
        "description": "Stripe and PayPal gateway integrations handling authorization, capture, refunds, and webhook processing",
        "content": "Manages connections to Stripe and PayPal APIs. Handles payment authorization, capture on order fulfillment, refunds, and webhook event processing. Implements retry logic with circuit breakers for external API calls.",
        "status": "active",
        "tags": ["service", "backend", "payments", "external"],
        "related_entity_ids": [
            PAYMENTS_SERVICE,
        ],
        "metadata": {
            "providers": ["Stripe", "PayPal"],
            "criticality": "high",
            "team": "payments",
        },
        "createdAt": "2024-08-15T10:00:00+00:00",
        "updatedAt": "2025-01-20T14:30:00+00:00",
    },
    {
        "_id": AUTH_SERVICE,
        "name": "Authentication service",
        "description": "Centralized authentication service handling user login, token issuance, and session management",
        "content": "Provides JWT-based authentication for all services. Handles user credentials, issues access and refresh tokens, manages sessions. Integrates with API gateway for request validation.",
        "status": "active",
        "tags": ["service", "backend", "authentication"],
        "related_entity_ids": [
            JWT_VALIDATION,
        ],
        "metadata": {
            "criticality": "high",
            "dependencies": [],
            "team": "platform",
        },
        "createdAt": "2024-08-20T11:00:00+00:00",
        "updatedAt": "2025-01-15T09:00:00+00:00",
    },
    {
        "_id": JWT_VALIDATION,
        "name": "JWT validation convention",
        "description": "Standardized JWT validation pattern using RS256 with public key distribution via JWKS endpoint",
        "content": "All services validate JWTs using RS256 algorithm. Public keys distributed via JWKS endpoint from auth service. Tokens include user ID, roles, and expiration. Refresh token rotation implemented for security.",
        "status": "active",
        "tags": ["convention", "architecture", "authentication"],
        "related_entity_ids": [
            AUTH_SERVICE,
        ],
        "metadata": {
            "algorithm": "RS256",
            "adoptionDate": "2024-09-01",
        },
        "createdAt": "2024-09-01T10:00:00+00:00",
        "updatedAt": "2024-09-01T10:00:00+00:00",
    },
    {
        "_id": EVENT_SCHEMA_REGISTRY,
        "name": "Event schema registry",
        "description": "ADR-044: Centralized schema registry for all Kafka events using JSON Schema with backward compatibility enforcement",
        "content": "All event producers must register schemas in the registry. Enforces backward compatibility to prevent breaking consumers. Provides schema validation at build time and runtime. Versioned with semantic versioning.",
        "status": "active",
        "tags": ["decision", "architecture", "event sourcing"],
        "related_entity_ids": [
            EVENT_SOURCING,
        ],
        "metadata": {
            "adrNumber": 44,
            "rationale": "Prevent breaking changes in event contracts",
            "decidedDate": "2024-09-25",
        },
        "createdAt": "2024-09-25T14:00:00+00:00",
        "updatedAt": "2024-09-25T14:00:00+00:00",
    },
    {
        "_id": LOAD_TESTING,
        "name": "Load testing setup",
        "description": "Automated load testing infrastructure using k6 for performance validation and capacity planning",
        "content": "CI/CD pipeline includes load tests using k6 scripts. Runs against staging environment before production deployments. Discovered the thundering herd issue during cascade failure investigation. Baseline performance metrics tracked over time.",
        "status": "active",
        "tags": ["knowledge", "testing", "performance"],
        "related_entity_ids": [
            CASCADE_FAILURE,
        ],
        "metadata": {
            "technology": ["k6", "Grafana"],
            "lastRun": "2025-01-20",
        },
        "createdAt": "2024-10-15T09:00:00+00:00",
        "updatedAt": "2025-01-20T16:00:00+00:00",
    },
]


def build_embedding_text(node: dict) -> str:
    """Build concise, retrieval-optimized embedding text from a node.
    
    Pattern: {name} [{status}]\\n{description}\\nTags: {comma-separated}
    
    This concise format focuses on semantic signals that help vector search
    without diluting the embedding with procedural content like timelines.
    """
    header = f"{node['name']} [{node['status']}]"
    description = node["description"]
    tags = "Tags: " + ", ".join(node["tags"])
    return f"{header}\n{description}\n{tags}"
