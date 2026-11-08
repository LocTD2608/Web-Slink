-- Minh họa nguyên tử, KHÔNG phải toàn bộ logic của ứng dụng.
-- Code lab còn kiểm tra lịch, tín chỉ, tiên quyết và ticket.
if redis.call("SISMEMBER", KEYS[2], ARGV[1]) == 1 then return -1 end
local slots = tonumber(redis.call("GET", KEYS[1]) or "0")
if slots <= 0 then return 0 end
redis.call("DECR", KEYS[1])
redis.call("SADD", KEYS[2], ARGV[1])
return 1
