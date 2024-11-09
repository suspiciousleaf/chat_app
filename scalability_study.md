# Scalability Study for Chat Application

## Introduction
This study explores strategies for scaling a real-time chat application to support 10x to 100x its current user base. The architectural design considerations here aim to address exponential growth in message volume, database load, and CPU utilization as the number of users grows. Key strategies include modularizing services, offloading intensive tasks, and balancing load efficiently across server instances.

## Scalability Challenges

1. **Message Volume Explosion**: Each user message must be sent to all other users in a channel, leading to exponential message growth as user count increases. 
2. **Database Bottlenecks**: Real-time database writes for user actions and message history can saturate disk I/O and CPU.
3. **Authentication Load**: Resource-intensive authentication processes impact server response times and limit scalability.
4. **Load Balancing**: Efficiently distributing users and message traffic across server instances to avoid bottlenecks and ensure smooth scaling.

## Proposed Architectural Changes

### 1. Authentication as a Microservice
   - **Current Challenge**: Authentication requires CPU-intensive password hashing, consuming resources on the main server.
   - **Solution**: Move authentication to a standalone microservice dedicated to validating users and issuing JWT tokens. The main server will only handle token validation, which is lightweight.
   - **Benefits**:
     - Reduces CPU load on the chat server, improving response times.
     - Allows independent scaling of the authentication microservice.
     - Potential for elastic scaling with cloud services (e.g., AWS EC2 auto-scaling).
   - **Implementation**:
     - Login endpoint can go directly to the authentication microservice, and use the received JWT to authorize the session to the main server.

### 2. Database Writes via Redis Queue System
   - **Current Challenge**: High-volume, synchronous database writes for message history and channel subscriptions lead to slowdowns.
   - **Solution**: Implement a **Redis-based queue system** to manage asynchronous database writes, decoupling them from user-facing processes.
   - **Benefits**:
     - Allows for controlled, efficient writing through dedicated worker services.
     - Supports scaling by adding more workers as the user base grows.
     - At present SQLite is used to minimize latency, but for scaling and to allow better asynchronous performance changing to Postgres may be a better solution.
   - **Implementation**:
     - Messages and subscriptions are queued in Redis.
     - A background worker service reads from the queue and commits actions to the database in batches, improving write efficiency and reducing main server impact.

### 3. Horizontal Scaling with Load Balancer
   - **Current Challenge**: Single-server architecture is unsustainable for high traffic, causing increased latency and potential failures.
   - **Solution**: Deploy multiple server instances behind a load balancer, distributing user connections and requests across available resources.
   - **Benefits**:
     - Allows linear scaling by adding more instances as needed.
     - Mitigates risk of single-point failures and improves resilience.
   - **Implementation**:
     - Use a load balancer such as AWS ELB or NGINX.
     - Each server instance handles a subset of user connections, reducing load per instance.
   
### 4. Redis Pub/Sub for Message Broadcasting
   - **Current Challenge**: High-volume message broadcasting across all connected users results in significant server load.
   - **Solution**: Use a **Redis Pub/Sub** system for inter-server message propagation.
   - **Benefits**:
     - Allows servers to only be exposed to messages on channels that users they are servicing are subscribed to.
   - **Implementation**:
     - When a message is sent in a channel and received by a server instance, it is published to Redis.
     - All relevant server instances subscribe to the necessary Redis channels, receiving messages and broadcasting them to local users as needed.


## Scalability Testing Strategy

To validate the effectiveness of these changes, thorough testing will be conducted:

1. **Load Testing**: Simulate increased user traffic (10x to 100x) and observe key metrics, including:
   - **Latency**: 90th, 95th, and 99th percentile response times.
   - **CPU Usage**: Across all microservices and database. Load averages are an important metric for longer duration load tests.
   - **Message Throughput**: Number of messages processed and broadcast per second.

2. **Stress Testing**: Push the application beyond expected loads to understand its limits and pinpoint potential failure modes.

3. **Monitoring and Observability**:
   - Implement real-time monitoring for server health, Redis queue lengths, message broadcast latency, and load balancing efficiency.
   - Use tools like Prometheus and Grafana to visualize and alert on performance metrics.

## Actionable Summary

The following architectural adjustments will enhance scalability and support a growing user base:

1. **Authentication Microservice**: Reduces CPU load on the main server by offloading user validation.
2. **Redis Queue for Database Writes**: Improves database efficiency by queuing writes.
3. **Load Balancer and Horizontal Scaling**: Distributes load across multiple instances.
4. **Redis Pub/Sub for Broadcasting**: Synchronizes messages across instances without redundant effort.

This is essentially a complete rebuild of the app from the ground up. Given the focus on performance and scale, it would likely be worthwhile to switch to a more performant language like Go for this implementation.
