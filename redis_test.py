import time
import asyncio
import redis
import sqlite3

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


# Async Redis test
async def run_redis_test(test_range, batch_size=1000):
    print("\nRedis test (async)\n")

    t1 = time.perf_counter()
    for i in range(0, test_range, batch_size):
        batch = range(i, min(i + batch_size, test_range))
        await asyncio.gather(*[redis_set(j) for j in batch])
    t2 = time.perf_counter()
    print(f"Uploads completed in {t2-t1:.4f}s")

    for i in range(0, test_range, batch_size):
        batch = range(i, min(i + batch_size, test_range))
        await asyncio.gather(*[redis_get(j) for j in batch])
    t3 = time.perf_counter()
    print(f"Retrieves completed in {t3-t2:.4f}s")

    for i in range(0, test_range, batch_size):
        batch = range(i, min(i + batch_size, test_range))
        await asyncio.gather(*[redis_delete(j) for j in batch])
    t4 = time.perf_counter()
    print(f"Deletes completed in {t4-t3:.4f}s")


# In-memory test
def run_in_memory_test(test_range):
    print("\nIn memory test\n")
    mem_store = {}
    t0 = time.perf_counter()
    for i in range(test_range):
        mem_store[i] = i
    t1 = time.perf_counter()
    print(f"Uploads completed in {t1-t0:.4f}s")
    for i in range(test_range):
        x = mem_store[i]
    t2 = time.perf_counter()
    print(f"Retrieves completed in {t2-t1:.4f}s")
    for i in range(test_range):
        mem_store.pop(i)
    t3 = time.perf_counter()
    print(f"Deletes completed in {t3-t2:.4f}s")


# SQLite in-memory test
def run_sqlite_test(test_range, database=":memory:"):
    print(f"\nSQLite test ({database})\n")
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
    print(f"Uploads completed in {t1-t0:.4f}s")

    t2 = time.perf_counter()
    for i in range(test_range):
        c.execute("SELECT value FROM test WHERE id=?", (i,))
        x = c.fetchone()
    t3 = time.perf_counter()
    print(f"Retrieves completed in {t3-t2:.4f}s")

    c.executemany("DELETE FROM test WHERE id=?", [(i,) for i in range(test_range)])
    conn.commit()
    t4 = time.perf_counter()
    print(f"Deletes completed in {t4-t3:.4f}s")

    conn.close()


# Main execution
async def main():
    test_range = 100000
    print(f"Iterations: {test_range:,}")

    redis_batch_size = 100

    # await run_redis_test(test_range, redis_batch_size)
    run_in_memory_test(test_range)
    run_sqlite_test(test_range, ":memory:")
    run_sqlite_test(test_range, "perf_test_db")


if __name__ == "__main__":
    asyncio.run(main())
