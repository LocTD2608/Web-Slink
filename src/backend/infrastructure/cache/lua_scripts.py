# Lua scripts for Redis atomic operations

RESERVE_SLOT_LUA = """
-- KEYS[1]: section:{section_id}:slots
-- KEYS[2]: section:{section_id}:enrolled
-- KEYS[3]: student:{student_id}:completed_courses
-- KEYS[4]: student:{student_id}:credits
-- KEYS[5]: student:{student_id}:registered_mask

-- ARGV[1]: student_id
-- ARGV[2]: prerequisite_course_code (or 'NONE')
-- ARGV[3]: section_time_mask (number)
-- ARGV[4]: section_credits (number)

local student_id = ARGV[1]
local prereq_code = ARGV[2]
local section_time_mask = tonumber(ARGV[3])
local section_credits = tonumber(ARGV[4])

-- 1. Kiểm tra sinh viên đã đăng ký lớp này chưa
if redis.call('SISMEMBER', KEYS[2], student_id) == 1 then
    return -1 -- ALREADY_ENROLLED
end

-- 2. Kiểm tra slot lớp học phần
local current_slots = tonumber(redis.call('GET', KEYS[1]) or 0)
if current_slots <= 0 then
    return -2 -- SECTION_FULL
end

-- 3. Kiểm tra môn tiên quyết (nếu có yêu cầu)
if prereq_code ~= "" and prereq_code ~= "NONE" then
    if redis.call('SISMEMBER', KEYS[3], prereq_code) == 0 then
        return -3 -- PREREQUISITE_NOT_MET
    end
end

-- 4. Kiểm tra trần tín chỉ
local current_credits = tonumber(redis.call('HGET', KEYS[4], 'current') or 0)
local max_credits = tonumber(redis.call('HGET', KEYS[4], 'max') or 24)
if (current_credits + section_credits) > max_credits then
    return -4 -- CREDIT_LIMIT_EXCEEDED
end

-- 5. Kiểm tra trùng lịch học qua Bitmask (84-bit)
local student_mask = tonumber(redis.call('GET', KEYS[5]) or 0)
-- Phép toán bitwise AND trong Lua 5.3+ hoặc mô phỏng số
-- Trong Redis Lua (Lua 5.1/bit library), dùng bit.band
local conflict = 0
if bit and bit.band then
    conflict = bit.band(student_mask, section_time_mask)
else
    -- Fallback nếu bit lib không sẵn có: kiểm tra logic số học
    local sm = student_mask
    local tm = section_time_mask
    while sm > 0 and tm > 0 do
        if (sm % 2 == 1) and (tm % 2 == 1) then
            conflict = 1
            break
        end
        sm = math.floor(sm / 2)
        tm = math.floor(tm / 2)
    end
end

if conflict > 0 then
    return -5 -- SCHEDULE_CONFLICT
end

-- 6. THÀNH CÔNG: Trừ slot và cập nhật dữ liệu sinh viên
redis.call('DECR', KEYS[1])
redis.call('SADD', KEYS[2], student_id)
redis.call('HINCRBY', KEYS[4], 'current', section_credits)

-- Cập nhật mask mới (bitwise OR)
local new_mask = 0
if bit and bit.bor then
    new_mask = bit.bor(student_mask, section_time_mask)
else
    new_mask = student_mask + section_time_mask - conflict
end
redis.call('SET', KEYS[5], tostring(new_mask))

return 1 -- SUCCESS
"""

ROLLBACK_SLOT_LUA = """
-- KEYS[1]: section:{section_id}:slots
-- KEYS[2]: section:{section_id}:enrolled
-- KEYS[3]: student:{student_id}:credits
-- KEYS[4]: student:{student_id}:registered_mask

-- ARGV[1]: student_id
-- ARGV[2]: section_time_mask (number)
-- ARGV[3]: section_credits (number)

local student_id = ARGV[1]
local section_time_mask = tonumber(ARGV[2])
local section_credits = tonumber(ARGV[3])

-- 1. Hoàn trả slot
redis.call('INCR', KEYS[1])

-- 2. Xóa sinh viên khỏi tập hợp giữ slot
redis.call('SREM', KEYS[2], student_id)

-- 3. Trừ lại số tín chỉ
local current_credits = tonumber(redis.call('HGET', KEYS[3], 'current') or 0)
if current_credits >= section_credits then
    redis.call('HINCRBY', KEYS[3], 'current', -section_credits)
end

-- 4. Trừ lại mặt nạ thời gian
local student_mask = tonumber(redis.call('GET', KEYS[4]) or 0)
if bit and bit.band and bit.bnot then
    local new_mask = bit.band(student_mask, bit.bnot(section_time_mask))
    redis.call('SET', KEYS[4], tostring(new_mask))
end

return 1
"""
