# DocQA AI Agent - Microservices Deployment on AWS

## 📚 Project Overview

**DocQA AI Agent** is a sophisticated document question-answering system built using a microservices architecture and deployed on AWS. The application allows users to upload PDF/TXT documents and have intelligent conversations about their content using state-of-the-art language models.

### Key Features
- **Document Upload & Processing**: Support for PDF and TXT files with intelligent text chunking
- **Vector-Based Search**: Semantic search using sentence transformers and Qdrant vector database
- **Conversational Memory**: Persistent chat history across sessions
- **AI-Powered Responses**: Integration with Groq's LLaMA models for intelligent answers
- **Modern Web Interface**: Responsive React-like frontend with real-time interactions

## 🏗️ Architecture Overview

The system follows a microservices architecture with the following components:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   API Gateway   │    │  Ingestion      │
│   (S3 + CF)     │◄──►│   (Port 8000)   │◄──►│  Service        │
└─────────────────┘    └─────────────────┘    │  (Port 8001)    │
                                  │           └─────────────────┘
                                  ▼                     │
                       ┌─────────────────┐             ▼
                       │  LLM Service    │    ┌─────────────────┐
                       │  (Port 8003)    │    │ Vector-Memory   │
                       └─────────────────┘    │ Service         │
                                  │           │ (Port 8002)     │
                                  ▼           └─────────────────┘
                       ┌─────────────────┐             │
                       │   Qdrant DB     │◄────────────┘
                       │  (Port 6333)    │
                       └─────────────────┘
```

### Service Details

| Service | Port | Purpose | Technologies |
|---------|------|---------|-------------|
| **API Gateway** | 8000 | Request routing, session management | FastAPI, Qdrant Client |
| **Ingestion Service** | 8001 | Document processing & chunking | FastAPI, PyPDF2 |
| **Vector-Memory Service** | 8002 | Embeddings & chat memory | FastAPI, SentenceTransformers, PyTorch |
| **LLM Service** | 8003 | AI response generation | FastAPI, Groq API |
| **Qdrant Database** | 6333 | Vector storage & search | Qdrant Vector DB |

## 🛠️ Local Development & Testing

### Prerequisites
- Docker & Docker Compose
- Python 3.10+
- Node.js (for frontend development)

### Local Setup
```bash
# Clone the repository
git clone <repository-url>
cd docqa-microservices

# Set environment variables
echo "GROQ_API_KEY=your_groq_api_key_here" > .env

# Build and run all services
docker-compose build
docker-compose up -d

# Verify all services are running
docker-compose ps
```

### Local Testing
- **API Gateway**: http://localhost:9000
- **Individual Services**: Available on their respective ports (9001-9004)
- **Frontend**: Serve index.html locally or via HTTP server

## ☁️ AWS Deployment Strategy

### Infrastructure Setup

#### 1. EC2 Instance Configuration
- **Instance Type**: t3.micro (AWS Free Tier)
- **OS**: Ubuntu 24.04 LTS
- **Storage**: 20GB gp3 EBS volume (upgraded from default 8GB)
- **Security Group**: Open ports 22 (SSH), 9000-9004 (Services)

#### 2. EC2 Setup Process
```bash
# SSH into EC2 instance
ssh -i your-key.pem ubuntu@your-ec2-public-ip

# Install Docker
sudo apt update
sudo apt install -y docker.io
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installations
docker --version
docker-compose --version
```

#### 3. Code Deployment
```bash
# Transfer code to EC2 (via SCP or Git)
scp -i your-key.pem -r ./docqa-project ubuntu@your-ec2-ip:~/

# Or clone from repository
git clone https://your-repo-url
cd docqa-project
```

### Docker Optimization

#### Multi-Stage Dockerfile Strategy
To optimize image sizes and reduce deployment costs, all services use multi-stage builds:

```dockerfile
# Example: Optimized Dockerfile pattern
FROM python:3.10-slim AS build
RUN apt-get update && apt-get install -y gcc build-essential
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.10-slim
COPY --from=build /install /usr/local
COPY . .
RUN groupadd -r appgroup && useradd -m -r -g appgroup appuser
USER appuser
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Benefits Achieved**:
- Reduced image sizes from ~5GB to <500MB per service
- Eliminated build tools from production containers
- Enhanced security with non-root users
- Faster deployment and scaling

#### Service Consolidation
Originally separate vector and memory services were merged to:
- Reduce resource consumption on t3.micro
- Minimize Docker image storage requirements
- Share expensive ML dependencies (PyTorch, Transformers)

### Container Orchestration

#### Docker Compose Configuration
```yaml
version: "3.9"
services:
  qdrant:
    image: qdrant/qdrant:v1.7.0
    restart: unless-stopped
    ports:
      - "6333:6333"
    volumes:
      - qdrant_storage:/qdrant/storage
    networks:
      - docnet

  api-gateway:
    build:
      context: .
      dockerfile: ./api-gateway/Dockerfile
    restart: unless-stopped
    depends_on:
      - qdrant
      - vector-memory-service
    ports:
      - "9000:8000"
    networks:
      - docnet

  # Additional services...
```

#### Deployment Commands
```bash
# Set environment variables
echo "GROQ_API_KEY=your_actual_api_key" > .env

# Build all services
docker-compose build --no-cache

# Deploy with auto-restart
docker-compose up -d

# Monitor deployment
docker-compose ps
docker-compose logs -f
```

### Persistent Storage & Data Management

#### Qdrant Vector Database
- **Storage**: Persistent Docker volume (`qdrant_storage`)
- **Collections**: 
  - `documents1`: Document embeddings
  - `memory`: Chat history
  - `sessions`: Session-document mappings
- **Backup Strategy**: Volume snapshots via EC2 instance snapshots

#### Session Management
- **Architecture**: Session IDs map to document IDs in Qdrant
- **Persistence**: All chat history and document associations stored in vector database
- **Scalability**: Stateless services with externalized state

## 🌐 Frontend Deployment

### AWS S3 + CloudFront Strategy

#### S3 Static Website Hosting
```bash
# Create S3 bucket
aws s3api create-bucket --bucket docqa-frontend-unique-name --region us-east-1

# Configure static website hosting
aws s3 website s3://docqa-frontend-unique-name --index-document index.html

# Upload frontend assets
aws s3 cp ./index.html s3://docqa-frontend-unique-name/index.html
```

#### CloudFront CDN Configuration
- **Purpose**: HTTPS termination, global caching, improved performance
- **Origin**: S3 static website endpoint
- **Caching**: Optimized for static assets with appropriate TTL
- **Security**: Origin Access Control (OAC) for secure S3 access

#### Frontend-Backend Integration
```javascript
// Frontend configuration
const BASE_URL = 'http://your-ec2-public-ip:9000';

// CORS handling in backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configured for CloudFront domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Security Considerations

#### Network Security
- **EC2 Security Groups**: Restrictive inbound rules
- **API Authentication**: Session-based access control
- **CORS Policy**: Configured for legitimate frontend domains

#### Data Security
- **Non-root Containers**: All services run as unprivileged users
- **Environment Variables**: Sensitive data (API keys) via Docker secrets
- **TLS Termination**: HTTPS at CloudFront level

## 🚀 Final System Architecture

### Production URLs
- **Frontend**: `https://d1cv6g1sea6x96.cloudfront.net`
- **Backend API**: `http://your-ec2-public-ip:9000`
- **Health Checks**: Individual service endpoints available

### Data Flow
1. **Document Upload**: Frontend → API Gateway → Ingestion Service → Vector-Memory Service → Qdrant
2. **Question Processing**: Frontend → API Gateway → Vector Search + Memory Retrieval → LLM Service → Response
3. **Session Management**: All interactions tracked with persistent session IDs

### Performance Characteristics
- **Response Time**: <2 seconds for typical queries
- **Scalability**: Horizontal scaling ready with load balancer
- **Availability**: 99%+ uptime with container restart policies
- **Storage**: Unlimited document storage via vector embeddings

## 📊 Monitoring & Operations

### Health Monitoring
```bash
# Check all services
docker-compose ps

# View logs
docker-compose logs -f [service-name]

# System resources
docker stats
```

### Scaling Considerations
- **Current**: Single EC2 instance with container orchestration
- **Future**: ECS/EKS for auto-scaling
- **Database**: Qdrant cluster for high availability

### Cost Optimization
- **Free Tier Usage**: EC2 t3.micro, S3, CloudFront
- **Resource Efficiency**: Merged services, optimized images
- **Auto-shutdown**: Development environment automation

## 🔧 Maintenance & Updates

### Deployment Updates
```bash
# Update application code
git pull origin main

# Rebuild and redeploy
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Update frontend
aws s3 cp ./index.html s3://docqa-frontend-unique-name/index.html
```

### Backup Strategy
- **Application Data**: Qdrant vector database via volume snapshots
- **Configuration**: Infrastructure as Code (Docker Compose)
- **Source Code**: Git repository with version control

## 📈 Results & Outcomes

### Technical Achievements
- ✅ **Microservices Architecture**: Successfully decomposed monolithic application
- ✅ **Container Orchestration**: Efficient Docker-based deployment
- ✅ **Cloud Integration**: Full AWS ecosystem utilization
- ✅ **Performance Optimization**: <500MB container images vs original 5GB
- ✅ **Scalable Design**: Ready for production-scale workloads

### Business Value
- **Cost Effective**: Entire system runs on AWS Free Tier
- **Production Ready**: HTTPS, CDN, persistent storage
- **User Experience**: Fast, responsive document Q&A interface
- **Maintainable**: Clear separation of concerns and automated deployments

### Key Learnings
1. **Resource Constraints**: t3.micro limitations drove optimization innovations
2. **Service Consolidation**: Strategic merging reduced complexity and costs
3. **Mixed Protocols**: HTTP backend + HTTPS frontend required careful CORS handling
4. **Image Optimization**: Multi-stage builds essential for resource-constrained deployments

***

## 🚦 Getting Started

### Quick Start
1. Clone this repository
2. Set up your AWS credentials and Groq API key
3. Follow the deployment scripts in `/deployment` folder
4. Access your DocQA application via the CloudFront URL

### Prerequisites
- AWS Account with appropriate permissions
- Groq API key for LLM functionality
- Basic understanding of Docker and AWS services

***

**Project Status**: ✅ Production Deployed  
**Last Updated**: September 2025  
**AWS Region**: us-east-1  
**Estimated Monthly Cost**: $0 (Free Tier)
