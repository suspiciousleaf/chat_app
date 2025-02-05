# Chattr: Real-Time Chat Application

## Overview  
Chattr is a real-time chat application designed to facilitate dynamic group or topic-based communication. It features authentication, message persistence, and a performance monitoring framework. The project was developed as a learning tool to explore real-time communication, low-latency programming, concurrency, performance monitoring, testing, profiling, and optimization.

## Features  
- **Real-Time Messaging**: Instant message delivery with low latency.  
- **Dynamic Groups/Topics**: Create and join chat groups or topics on the fly.  
- **Authentication**: Secure user authentication to protect account identities.  
- **Performance Monitoring**: Built-in tools for monitoring application performance.  
- **Load Testing Framework**: Tools to simulate high traffic and test scalability.  

## Project Structure  
The Chattr project is divided into three main components:  
1. **Native GUI Client**: The user interface for interacting with the chat application.  
2. **Backend Server**: Handles the authentication and message handling logic, deployed using Docker for easy setup and scalability.  
3. **Performance Monitoring and Load Testing Framework**: Tools to monitor the application's performance and conduct load testing.  

### Client with load testing in progress
![](demo.gif)

### Example of performance data
 ![Graphs](https://i.imgur.com/JRoV4dQ.png)
 [Source](https://i.imgur.com/JRoV4dQ.png)

## Getting Started  
### Prerequisites  
- Docker  
- Create a virtual environment using `requirements.txt`

### Installation  
1. Clone the repository:  
   ```bash
   git clone https://github.com/suspiciousleaf/chat_app.git
   ```
2. Navigate to the server directory:
   ```bash
   cd server
   ```
3. Comment the correct section of the `docker-compose.yaml` file if running locally or in a container
4. Build a `.env` following the `.env.example` format
5. Either:
   
   a. Start the Docker container:
      ```bash
      docker-compose up --build
      ```
   b. Start Uvicorn:
      ```bash
      uvicorn main_server:app
      ```
6. Start the GUI client, it will perform a health check on the server:
   ```bash
   cd ..
   python run_client.py
   ```
7. Create an account for yourself, for the monitor (using the credentials you specified in the `.env`), and run `load_testing/create_accounts.py` to generate accounts for the virtual users
8. Run `run_load_testing.py` with your chosen constants to initiate a load test. Activity can be viewed via the client, and once it is complete data will be graphed and displayed / saved.
9.  If `USE_cPROFILE = True` in the `.env` file, cProfile will run on the server during the load test. `load_testing/analyze_prof_data.py` can be used to generate flame graphs and analysis from the profile data.

### Performance Analysis and Scalability Study
For detailed insights into the application's performance and scalability, refer to the Performance Analysis Report and Scalability Study. The Performance Analysis Report includes performance data from before and after the performance improvements, including graphs as produced by the load test, plus targets and achievements. 

### Tech Stack

GUI: Tkinter
Server: 
Database: SQLite
Serialization: Protobuf
Authentication: OAuth2 with JWT
Concurrency: asyncio with uvloop
Deployment: Docker
