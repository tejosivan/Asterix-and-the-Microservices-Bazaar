# Asterix and the Microservices Bazaar

This project was undertaken as part of UMass Compsci 677 (Spring '25) by Tejas Sivan and Deepesh Suranjandass. The submitted Readme can be found below. The questionnaire can be found in Questionnaire.md.

Lab 3 - Replication, Caching, and Fault Tolerance

## Overview

This project implements a distributed system with replication, caching, and fault tolerance capabilities. It includes a basic implementation and an optional Paxos-based consensus protocol for extra credit.

## System Components

- **Catalog Service**: Manages stock information
- **Order Service**: Handles trade orders with replication
- **Frontend Service**: Provides client interface with caching
- **Paxos Implementation**: Optional consensus protocol for order service replication

## Prerequisites

- Python 3.x
- Required Python packages (see `requirements.txt`):
  - requests >= 2.25.1
  - matplotlib >= 3.5.1
  - pandas >= 1.3.5
  - numpy >= 1.21.5

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/your-username/your-repo.git
   cd your-repo
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the System

### Basic Implementation

#### 1. Start Catalog Service

```bash
python src/catalog/catalog.py
```

#### 2. Start Order Service Replicas

```bash
# Primary replica (ID 0)
python src/order/order.py 0

# Follower replica (ID 1)
python src/order/order.py 1

# Follower replica (ID 2)
python src/order/order.py 2
```

#### 3. Start Frontend Service

```bash
# With cache enabled (default)
python src/frontend/frontend.py

# With cache disabled
python src/frontend/frontend.py --cache=false
```

#### 4. Start simple client

```bash
# With p=0.8
python src/client/client.py 0.8

```

### Running Tests

```bash
cd src/client
python testclient.py ( This will create a bunch of .txt and .log files which are important for us to visualize and analyse at all situations)
python runclients.py
```

The test suite will:

- Run 5 clients with different p values (0.0, 0.2, 0.4, 0.6, 0.8)
- Test with cache enabled and disabled
- Generate performance plots
- Test fault tolerance

### Paxos Implementation (Extra Credit)

```bash
cd paxos_implementation

# Start Paxos-enabled order service replicas
python paxos_order.py 0
python paxos_order.py 1
python paxos_order.py 2

# Run Paxos consensus tests
python paxos_test.py
```

## Output Files

After running the tests, the following files will be generated:

- `latency_results.csv`: Raw latency data
- `latency_comparison_plot.png`: Performance comparison plots
- `cache_replacement_visualization.png`: Cache behavior visualization
- `latency_during_failures.png`: System behavior during failures

## AWS Deployment

### 1. Set Up AWS Instance

- Launch a t2.medium instance in us-east-1 region with Amazon Linux 2
- Select a key pair (.pem file) during instance creation
- Configure security group to allow inbound traffic on ports:
  - 5555 (Frontend)
  - 6666 (Catalog)
  - 7777-7779 (Order Service)

### 2. Connect to AWS Instance

```bash
# Set proper permissions for your key file
chmod 400 your-key-file.pem

# Connect to your instance
ssh -i your-key-file.pem ec2-user@your-instance-public-dns
```

### 3. Environment Setup

```bash
# Update system packages
sudo yum update -y

# Install required packages
sudo yum install git python3 python3-pip -y

# Clone repository
git clone https://github.com/your-username/your-repo.git
cd your-repo

# Install Python dependencies
pip3 install -r requirements.txt
```

### 4. Alternative: Copy Files to AWS

```bash
# Copy files from local machine to AWS
scp -i your-key-file.pem -r ./src ec2-user@your-instance-public-dns:~/lab3/
scp -i your-key-file.pem -r ./paxos_implementation ec2-user@your-instance-public-dns:~/lab3/
```

### 5. Running on AWS

#### Using Screen Sessions

```bash
# Start catalog service
screen -S catalog
python3 src/catalog/catalog.py
# Press Ctrl+A then D to detach

# Start order service replicas
screen -S order0
python3 src/order/order.py 0
# Press Ctrl+A then D to detach

# Repeat for other replicas and frontend
```

#### Running Tests Against AWS

```bash
# Set environment variables
export FRONTEND_HOST=your-instance-public-dns
export FRONTEND_PORT=5555

# Run Test clients
python src/client/testlient.py

# Run clients
python src/client/runclients.py
```

#### Managing Screen Sessions

```bash
# Reattach to a screen session
screen -r session-name

# List screen sessions
screen -ls
```

## Architecture

The system implements a three-tier architecture:

1. **Frontend Layer**: Handles client requests and implements caching
2. **Order Service Layer**: Manages trade orders with replication
3. **Catalog Service Layer**: Maintains stock information

### Fault Tolerance

- Order service replicas provide redundancy
- Optional Paxos implementation ensures consensus
- Cache improves performance and reduces load
