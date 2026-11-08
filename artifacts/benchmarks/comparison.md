| Run | avg ms | p95 ms | completion p95 ms | Confirmed | Unexpected | Verified |
|---|---:|---:|---:|---:|---:|---|
| postgres-1 | 6822.252828031669 | 11146.363674549999 | 4672 | 60 | 0 | True |
| postgres-2 | 7845.715747668028 | 12587.699506899997 | 5095.4 | 60 | 0 | True |
| postgres-3 | 7125.301940138986 | 11546.14175575 | 4207.9 | 60 | 0 | True |
| redis_queue-1 | 748.6695812003314 | 4441.994902699997 | 3072.25 | 60 | 0 | True |
| redis_queue-2 | 596.452928855666 | 3344.9385412499983 | 2459.1 | 60 | 0 | True |
| redis_queue-3 | 704.8543642346673 | 4059.808571499997 | 2700.6 | 60 | 0 | True |
| smoke-redis_queue | 98.69688860000001 | 104.48932579999999 | 1145.55 | 10 | 0 | True |
| sustained-300 | None | None | None | 60 | 0 | True |
| sustained-3000 | None | None | None | 60 | 32482 | True |
| sustained-initial-limit | None | None | None | 60 | 74559 | True |
| warmup-postgres | 444.9969950000001 | 562.16107885 | 563.9499999999999 | 10 | 0 | True |
| warmup-redis_queue | 48.1039115 | 51.35290055 | 1061 | 10 | 0 | True |

Median postgres: avg 7125.302 ms; p95 11546.142 ms.

Median redis_queue: avg 704.854 ms; p95 4059.809 ms.
