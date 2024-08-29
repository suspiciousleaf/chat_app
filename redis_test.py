import time
import asyncio
import redis
import sqlite3
from pprint import pprint

t0 = time.perf_counter()

# Redis setup
r = redis.Redis(host="127.0.0.1", port=6379, decode_responses=True)


# Async Redis functions
async def redis_set(i):
    await asyncio.to_thread(r.set, str(i), str(i))


async def redis_get(i):
    return await asyncio.to_thread(r.get, str(i))


async def redis_delete(i):
    await asyncio.to_thread(r.delete, str(i))


async def run_redis_test(test_range, batch_size=1000):
    print("\nRedis test (async)\n")
    redis_times = {"set": [], "get": [], "delete": []}

    await redis_set(1)

    # Set operations
    for i in range(0, test_range, batch_size):
        batch = range(i, min(i + batch_size, test_range))
        for j in batch:
            t0_per_op = time.perf_counter_ns()
            await redis_set(j)
            t1_per_op = time.perf_counter_ns()
            redis_times["set"].append((t1_per_op - t0_per_op) / 1000)  # Microseconds

    print(
        f"Set operations completed with average time per operation: {sum(redis_times['set'])/len(redis_times['set']):.4f} µs"
    )

    # Get operations
    for i in range(0, test_range, batch_size):
        batch = range(i, min(i + batch_size, test_range))
        for j in batch:
            t0_per_op = time.perf_counter_ns()
            await redis_get(j)
            t1_per_op = time.perf_counter_ns()
            redis_times["get"].append((t1_per_op - t0_per_op) / 1000)  # Microseconds

    print(
        f"Get operations completed with average time per operation: {sum(redis_times['get'])/len(redis_times['get']):.4f} µs"
    )

    # Delete operations
    for i in range(0, test_range, batch_size):
        batch = range(i, min(i + batch_size, test_range))
        for j in batch:
            t0_per_op = time.perf_counter_ns()
            await redis_delete(j)
            t1_per_op = time.perf_counter_ns()
            redis_times["delete"].append((t1_per_op - t0_per_op) / 1000)  # Microseconds

    print(
        f"Delete operations completed with average time per operation: {sum(redis_times['delete'])/len(redis_times['delete']):.4f} µs"
    )

    # Print detailed times
    print(f"\nDetailed times (in µs):")
    for item in redis_times:
        redis_times[item].sort(reverse=True)
        print(f"{item}: \n{redis_times[item][:20]}...\n{redis_times[item][-20:]}")


# In-memory test
def run_in_memory_test(test_range):
    print("\nIn memory test\n")
    mem_store = {}
    mem_store_times = {"assign": [], "retrieve": [], "delete": []}
    t0 = time.perf_counter()
    for i in range(test_range):
        t0_per_op = time.perf_counter_ns()
        mem_store[i] = i
        t1_per_op = time.perf_counter_ns()
        mem_store_times["assign"].append((t1_per_op - t0_per_op) / 1000)
    t1 = time.perf_counter()
    print(f"Uploads completed in {(t1-t0)*1000:,.3f} ms")
    for i in range(test_range):
        t0_per_op = time.perf_counter_ns()
        x = mem_store[i]
        t1_per_op = time.perf_counter_ns()
        mem_store_times["retrieve"].append((t1_per_op - t0_per_op) / 1000)
    t2 = time.perf_counter()
    print(f"Retrieves completed in {(t2-t1)*1000:,.3f} ms")
    for i in range(test_range):
        t0_per_op = time.perf_counter_ns()
        mem_store.pop(i)
        t1_per_op = time.perf_counter_ns()
        mem_store_times["delete"].append((t1_per_op - t0_per_op) / 1000)
    t3 = time.perf_counter()
    print(f"Deletes completed in {(t3-t2)*1000:,.3f} ms")
    print(f"Detailed times (in µs):")
    for item in mem_store_times:
        mem_store_times[item].sort(reverse=True)
        print(
            f"{item}: \n{mem_store_times[item][:20]}...\n{mem_store_times[item][-20:]}"
        )


# SQLite test
def run_sqlite_test(test_range, database):
    print(f'\nSQLite test ("{database}")\n')
    sqlite_memory_times_us = []
    conn = sqlite3.connect(database)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, value INTEGER)")

    t0 = time.perf_counter()
    c.executemany(
        "INSERT INTO test (id, value) VALUES (?, ?)",
        [(i, i) for i in range(test_range)],
    )
    conn.commit()
    t1 = time.perf_counter()
    print(f"Uploads completed in {(t1-t0)*1000:.3f} ms")

    for i in range(test_range):
        t0_per_op = time.perf_counter_ns()
        c.execute("SELECT value FROM test WHERE id=?", (i,))
        x = c.fetchone()
        t1_per_op = time.perf_counter_ns()
        sqlite_memory_times_us.append((t1_per_op - t0_per_op) / 1000)
    t2 = time.perf_counter()
    print(f"Retrieves completed in {(t2-t1)*1000:.3f} ms")
    print(
        f"Times per operation in µs: \n{sqlite_memory_times_us[:20]}...\n{sqlite_memory_times_us[-20:]}"
    )

    c.executemany("DELETE FROM test WHERE id=?", [(i,) for i in range(test_range)])
    conn.commit()
    t3 = time.perf_counter()
    print(f"Deletes completed in {(t3-t2)*1000:.3f} ms")

    conn.close()


# Main execution
async def main():
    test_range = 10000
    print(f"Iterations: {test_range:,}")

    redis_batch_size = 100

    # await run_redis_test(test_range, redis_batch_size)
    run_in_memory_test(test_range)
    run_sqlite_test(test_range, ":memory:")
    run_sqlite_test(test_range, "perf_test_db")


if __name__ == "__main__":
    asyncio.run(main())

# TODO Measure redis operations in tranches to see if they are all slow, or if only a small nubmer are slowing everything down. Maybe make a graph
# TODO Measure speed of each operation and write all 100,000 to a csv, then graph them"""
