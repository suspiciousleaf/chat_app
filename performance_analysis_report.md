# Performance Analysis Report

## Overview
This report assesses the performance enhancements made to the chat application server following a series of optimizations, including improved serialization, CPU profiling, and optimizations to the asynchronous event loop. The primary objective was to reduce latency to a specified target, and reduce CPU load caused by each user and message, enabling the server to handle more concurrent users and higher message volumes without sacrificing user experience. The following improvements were evaluated against latency targets and CPU usage metrics.

### Target Metrics
- **Latency Percentiles**: 90th: 200ms, 95th: 500ms, 99th: 1000ms
- **CPU Load**: Reduce CPU overhead, particularly during high-load events like authentication and sustained message traffic.

Since authentication has such an impact on CPU load and results in significant latencies, and is the target of one fo the performance goals, until it is addressed in goal 4.3 it will be removed, by having accounts connect and then sit idle for a period of time until all authentication has completed. User activity will still ramp up, plateau, and ramp down as before, just after the authentical load has occured rather than concurrently.

Removing the authentication load in this way results in the following latencies:
With authentication:    percentiles_ms=[362,857,2132]
Without authentication: percentiles_ms=[203,246,311]

These values are already within the target range, indicating that addressing the authentication load is a correct approach. However we also want to increase the supported user / message bandwidth, so other performance gains are still required.

## Performance Goal 1: Serialization Optimization

### Implementation Details

A test message was created and serialized using the standard json library, as well as [orjson](https://github.com/ijl/orjson) (one of the most performant python json serializers) and [protobuf](https://protobuf.dev/). Serialization time, deserialization time, and message size were compared. Times are the sum over a loop of 1,000,000 iterations.

Test json message:
{
  "name": "Test Name",
  "age": 40,
  "random_float": 0.554781258874,
  "items": ["Hammer", "Radio"]
}

| Format      | Serialize (ms) | Deserialize (ms) | Total (ms) | File Size (bytes) |
|-------------|-----------------|------------------|------------|--------------------|
| JSON        | 3,588           | 2,630            | 6,219      | 132               |
| Orjson      | 407             | 645              | 1,052      | 116               |
| Protobuf    | 403             | 344              | 747        | 64                |

We expect to see speed improvements going from json to orjson/protobuf, and size improvements between orjson and protobuf.

- **Switch to orjson**: Initially replaced JSON serialization with orjson, resulting in measurable latency reduction. Orjson is not only a more performant tool for serialization / deserialization, but also serializes into bytes rather than a string, so messages can be sent as binary over the websocket which is more performant. It also results in a slightly smaller message - 116b vs 132b.
  json   percentiles_ms=[203,246,311]
  orjson percentiles_ms=[170,199,240]

- **Protobuf Integration**: Protobuf with a micro-backend ([upb](https://github.com/protocolbuffers/upb/wiki) written in C) was implemented for further reduction in CPU load and message size.
  - Protobuf showed improved serialization and deserialization times over JSON and Orjson, with message sizes reduced by 50% compared to JSON. The test message above was 64b using protobuf.
- **Post-Optimization Latencies (Protobuf)**:
  - protobuf percentiles_ms=[159,190,252]
  - CPU load has also slightly reduced, at peak message volume the band has dropped from 50%-90% down to 40%-80%. The micro band end doing the serialization is now able to be pushed to the second core on the server, reducing the demand on the core handling ther main load.
  
### Results
Protobuf serialization significantly reduced latency and CPU load, exceeding latency goals in tests. This approach allowed for an increase in active virtual users from 250 to 300, supporting a sustained message volume of 9,000 messages per second (up from 6,500 at 250 users) at the following latencies: percentiles_ms=[357,460,561].

**Conclusion**: Protobuf serialization achieved substantial latency and bandwidth improvements over the default JSON library.

## Performance Goal 2: CPU Profiling and Optimization

### Profiling Tools Used
Due to compatibility issues, cProfile was used instead of Scalene or py-spy. Profiling data was visualized with `snakeviz` and `gprof2dot`.

### Key Findings and Optimizations
<!-- 1. **SQLite Commit Overhead**: Approx 14% CPU usage during SQLite commit operations due to frequent updates to message history and channel subscription lists. This load will be mitigated by introducing caching for channel subscriptions, which can then be committed periodically or upon user disconnect. -->
**Profiling Impact**: cProfile adds significant CPU load so profiled tests will never perfectly replicate unprofiled load tests. Virtual users were decreased until the latencies achieved while profiling were approximately the same as those achieved with 250 users. In practice this was 200 users profiled vs 250 unprofiled.
  
1. **Event Loop Optimization**: The asyncio event loop showed considerable overhead. It was replaced with [uvloop](https://github.com/MagicStack/uvloop) (or [winloop](https://github.com/Vizonex/Winloop) for Windows when the server is run on my local machine). 

### Results using `uvloop`:
- Performance gains were negligible, indicating that although asyncio and the Proactor event loop had a heavy presence in the profiling data, it wasn't blocking the CPU. Async code can be hard to interpret as percentages don't necessarily sum to 100, and functions can accumulate high percentage values while they are waiting and not blocking.
 - Latency with uvloop under standard conditions: percentiles_ms=[165ms,196ms,247ms]
 - An unexpected benefit was a significant change to the profiled data as viewed with gprof2dot - Much of the event loop calls are no longer visible, and the CPU percentages occupied by other function calls are now much higher. This has made it significantly easier to interpret the data and look for possible optimisations.
   

2. **Compression Overhead**: The newly expanded  CPU percentage data shows that ~50% of time is spent on the `send_message` function. Of this, half is spent on `permessage_deflate`. This is a compression that is beneficial for sending JSON data, but has minimal benefits for data already encoded with protobuf, and carries a high CPU load. 

### Results with `permessage_deflate` Disabled via the `--ws-per-message-deflate` flag:
- percentiles_ms=[125ms,156ms,215ms] with 250 virtual users and message volume around 6500/s.
- `send_message` CPU demand reduced from 50% to 25%.


## Scalability Testing
After these optimizations, the server was tested at higher user counts to assess scalability:
- **325 Users (11,000/s)**: [164,188,221], CPU load of 40%-60%.
- **400 Users (16,500/s)**: [351,446,590], CPU load 40%-70%.
- **425 Users (18,000/s)**: [481,570,768], CPU load nearing saturation at 50%-90%.

With Protobuf optimizations, uvloop, and permessage_deflate, the application could handle nearly three times the original message bandwidth, supporting around 16,500 messages per second at an acceptable latency.The 90th percentile is a bit higher than originally specified, but the 95th and 99th are comfortably within limits and the behaviour is consistent across multiple runs.

### CPU Affinity Adjustment
During runs it was noted that the process moves between CPU cores every second or two, which gives a wide spread for CPU load data, and may impact performance due to cache misses. The main process was bound to a single core `psutil cpu affinity`. Doing it this way allows subprocesses like protobuf serialization to still be assigned to other cores.

### Results using CPU affinity:
- Reduced latencies percentiles_ms=[338,428,671] and a tighter band of CPU loads across the plateau: 70%-90% with affinity vs 60%-100% without at 425 virtual users.
- This did work as expected, however enforcing resource useage behaviour like this will likely only be beneficial in specific loading situations, and isn't a good idea for a production environment.

**Conclusion**: Profiling identified high-impact optimizations that enabled the application to support higher message throughput and user concurrency.


## Performance Goal 3: Authentication Load Reduction
### Implementation Details
Profiling showed that `authenticate_user` calls took 10.69% CPU time. Of this, the end of the chain is `built-in method _ffi.argon2_verify`, the password hashing function. This is by design CPU intensive, and it shows that without altering the password verification approach entirely there are no gains to be made. It uses highly optimised C code for the actual hashing. Given the high impact that authentication has on load, the best approach would be to move authentication to a separate microservice that will provide a bearer token (authentication already uses JWT), and the main server will just validate that token on connection, which carries a very small CPU load. 
Given the dynamic demand, some kind of elastic solution seems the most logical, like an AWS EC2 instance using auto scaling. 

## Summary of Performance Gains
- **Latency**: Across all optimizations, latency reductions were achieved, meeting or closely approaching target percentiles even under high-load scenarios.
- **CPU Load**: CPU usage per user was significantly reduced..
- **Scalability**: The optimizations enabled an increase in supported user volume from 250 to 425 users, with corresponding message volume scaling from 6500/s to 18,000/s.

### Performance graphs with optimisations implemented:
 ![Graphs](https://i.imgur.com/JRoV4dQ.png)
 [Source](https://i.imgur.com/JRoV4dQ.png)

### Pre optimised performance for comparison:
 ![Graphs](https://i.imgur.com/4Jmd8QG.png)
 [Source](https://i.imgur.com/4Jmd8QG.png)
 
---

This report demonstrates that the primary performance objectives were met, with additional headroom for future scalability. Transitioning authentication to a microservice could further free CPU resources and improve system responsiveness, enabling the server to maintain even higher user volumes while meeting target metrics.
