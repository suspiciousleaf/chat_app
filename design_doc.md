# Chat Application Performance Improvement Design Document

## 1. Introduction
This document outlines the strategy for improving the performance of a chat application server, focusing on three key areas. The server is written using FastAPI, with a SQLite database. The overall goal is to maximise the number of active users and message volume that the server can handle, while keeping latency sufficiently low to enable a good user experience. Latency percentile targets: 
- 90th: 200ms
- 95th: 500ms
- 99th: 1000ms

## 2. Understanding current performance
### Load testing
Load testing is performed by instantiating virtual users which mimic real user behaviour. Virtual users are hosted on a remote machine so they do not interfere with server performance. Accounts are selected from a pool of premade accounts. Credentials are used to acquire a bearer token for authentication, connect to the websocket, and then begin performing actions. These include sending random messages to one of the users' subscribed channels (94%), joining a new channel (3%), or leaving a channel (3%). Users wait 6 seconds between each action. After a set number of actions have been completed, the account disconnects. A specified delay is used between each account joining. This is based on general assumptions of user behaviour patterns.
This leads to a ramp up of activity with simultaneous authentication load, a plateau of sustained high activity, and then a tailing off of load following the same pattern as the ramp up, but without the additional authentication load.

A monitor pings the server once per second to request performance metrics, and measure the latency. This data includes: 
- Latency, calculated from the time the ping request is sent, to the time the response is received. It uses the same pathway and priority as messages sent between users, so it is representative of the user messaging experience
- CPU load
- Memory usage
- Message volume processed since last ping
- Duration for covers that volume (in case of high server load causing pings to cover a significantly longer or shorter period, so message volume can be calculated as per second)
- Adjusted message volume, calculated using the above duration, and using an EMA for some light smoothing
- Active accounts

### Parameters
Current load testing parameters have been chosen to push the server slightly beyond its limits, to expose which areas can be improved for the biggest performance gains and provide reliable, repeatable, metrics to assess changes. The parameters used for the graphs are:
- Users: 250
- Actions: 40
- Delay between connections: 0.25s
- Delay before action: 6s
- Delay between actions: 6s

### Analysis

Lantecies achieved:
- 90th: 362ms
- 95th: 857ms
- 99th: 2132ms
  
Current latencies are approximately double the desired values. 

 ![Graphs](https://i.imgur.com/fMh0V5v.png)
 [Source](https://i.imgur.com/fMh0V5v.png)

The graphs show some key details. The first graph shows that latency correlates with CPU load, rising slightly above 50% load, with some data points spiking significantly above 70% load. Message volume also correlates with CPU load. Message volume plateaus around 6500 per second, which can be sustained at approx 50% CPU load.  

The second graph shows that CPU usage starts at around 70% as soon as accounts start authenticating, indicating (as expected) a high CPU load caused by the auth process. This load increases as the test goes on and message volume picks up, peaking around 100% as peak user account numbers are reached. Once the authentication has been completed, peak message volume is sustained with 50-85% CPU load. As users complete their actions and start disconnecting, CPU load decrease correlates perfectly with reducing message volume as there is no additional auth load. 
Takeaways:
- Targeting the CPU load caused by authentication, if it can be done without compromising on security, is worth investigating.
- Message volume alone places a high demand on the server. Targeting reducions in this load should yield significant improvements to latency.
- The wide variation in CPU loads while sustaining user activity without auth might indicate some CPU intensive actions being performed that can be identified and minimized via a profiling technique, such as using a flame graph.
  
Graph three again illustrates the correlation between message volume and CPU load, as well as the exponential increase in message volume with regards to active users. The CPU load band at the top of the graph is the load during the first part of the test, including the auth load, and the lower band that tracks with message volume is from the end of the test, showing the load imposed by message volume only. Auth appears to impose approx +70% CPU load, reducing slightly as total load increases. This likely correlates with increased auth time. 

Graph four shows that the peak message volume of ~6500/s can be sustained around the limit of acceptable latency. However latency blows up at slightly lower volumes, which will be caused by the auth load combined with high message volume. This indicates that any reduction in CPU load from either message volume or auth with improve these latency spikes and get closer to the desired metrics.


## 3. Current Performance Issues
- High CPU usage and increased latency when message volume increases. Inefficient message serialization suspected to be a large part of this due to the use of the default json library. Other json libraries perform [significantly better](https://jcristharif.com/msgspec/benchmarks.html). In addition, other options like [protocol buffers](https://protobuf.dev/overview/), offer rapid serialization and reduced message size (thereby also reducing bandwidth requirements), which can improve performance even more and allow cross-language compatibility for future proofing.
- Heavy load from authentication processes.
- Other possible hidden CPU intensive tasks occuring during normal user activity.

## 4. Performance Improvement Goals

### 4.1 Message Serialization Optimization
**Objective**: Reduce serialization overhead and improve message processing speed.

**Proposed Solution**: Implement protobuf serialization, to reduce load, reduce message size, and allow messages to be sent as bytes rather than strings over websocket

**Action Items**:
- Replace current JSON serialization with protobuf
- Rewrite code to send data as bytes over websocket
- Benchmark performance before and after implementation

**Expected Outcome**: Reduced CPU usage and lower latency in message processing, allowing higher message bandwidth.

### 4.2 CPU Usage Analysis and Optimization
**Objective**: Identify and address CPU bottlenecks in the application. This could be from inefficient database use, logic operations with a high big O time cost, blocking I/O operations, places where caching could be introduced, and so on.

**Proposed Solution**: Utilize flame graphs for detailed CPU usage analysis, and target the biggest offenders.

**Action Items**:
- Set up profiling tools to generate flame graphs
- Analyze flame graphs to identify high-CPU operations
- Develop optimization strategies for identified bottlenecks
- Implement and test optimizations
- Re-profile to verify improvements

**Expected Outcome**: Comprehensive understanding of CPU usage patterns and targeted optimizations.

### 4.3 Authentication Load Reduction
**Objective**: Decrease authentication overhead.

**Proposed Solution**: 
Optimize authentication processes

**Action Items**:
- Analyze current authentication process for optimization opportunities
- Design and implement more efficient authentication method

**Expected Outcome**: Reduced server load from authentication.

## 5. Timeline / Order of Events
The protobuf integration is the lowest hanging fruit with the easiest implementation and no impact on other parts of the code, so it will be done first.
Next up the CPU load profiling so that the full app can be analyzed, and the auth load measured alongside the suspected bottlenecks. Bottlenecks can then be reduced.
Lastly tackling the auth load issue. This could potentially result in a significant refactor and change of flow, so I want to address the first two actions before undertaking this.

## 6. Success Metrics
Aim to achieve latency metrics as specified above:
- 90th: 200ms
- 95th: 500ms
- 99th: 1000ms

If these are achieved, sustain higher account activity while maintaining acceptable latency levels.

## 7. Risks and Mitigations
- Risk: New bottlenecks emerging after optimizations
- Mitigation: Continuous monitoring and iterative improvement
- Risk: Protobuf implementation will break compatibility with old client versions
- Mitigation: Client update will need to be implemented and rolled out at the same time as the server update
- Risk: Protobuf will make serialized messages unreadable
- Mitigation: Careful logging and incremental implementation to avoid errors should avoid most issues

## Performance goal 1: Serialization

Implemented orjson isntead of json with messages sent as bytes of websocket - latency percentiles changes:
without auth: 
json   percentiles_ms=[203,246,311]
orjson percentiles_ms=[170,199,240]
with auth:
json   percentiles_ms=[362,857,2132]
orjson percentiles_ms=[309,492,1828]

In serialization / deserialization tests, using a simple message with a string, int, float, and list (repeat string) over 10,000,000 loops. Using the upb micro-protobuf backend written in C for improved performance over the standard C++ version. Results:

Protobuf serialize:   403 ms
Protobuf deserialize: 344 ms
Protobuf total:       747 ms
Protobuf file size:   64 b

Orjson serialize:     407 ms
Orjson deserialize:   645 ms
Orjson total:         1,052 ms
Orjson file size:     116 b

Json serialize:       3,588 ms
Json deserialize:     2,630 ms
Json total:           6,219 ms
Json file size:       132 b

Protobuf is the fastest, but orjson was surprisingly close. Orjson is slightly faster at serializing data, but significantly slower at deserializing. Orjson shows a small reduction in filesize vs json, but protobuf achieves a 50% reduction in filesize which will contribute meaningfully to reducing required bandwidth.

Implemented cProfile to test server when running locally. Identified issue with protobuf implementation serializing messages for every send, rather than every message. Corrected and ran load testing under the same conditions:

without auth:
protobuf percentiles_ms=[159,190,252]

with auth:
protobuf percentiles_ms=[280,427,1667]

This has already exceeded the specified performance targets of [200,500,1000] when the auth load is removed, and isn't far off with it included. 
Virtual users were increased to 300 in the no auth test, which results in message volume increasing from ~6500/s to ~9000/s, and is sustained with the following latencies:
protobuf percentiles_ms=[357,460,561]

Additional observations:
While CPU load on the core handling the async thread remains high, the load on the second core increased from ~3% to ~20%. The protobuf serialization is done in C on a separate thread, which appears to be pushed to the second core. Moving this load to the other core, and the reduced message size, enables this higher sustained load and provides a significant performance boost.

This completes performance goal 1, serialization is done most efficiently using Protobuf, and a significant improvement in message volume and latency has been achieved.

## Performance goal 2: Profiling
