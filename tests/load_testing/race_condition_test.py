import os
import sys
import asyncio
import time
import httpx
from collections import Counter

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def detect_base_url():
    env_url = os.getenv("BASE_URL")
    if env_url:
        return env_url
    for url in ["http://localhost", "http://localhost:8000", "http://localhost:8080"]:
        try:
            with httpx.Client(timeout=1.0) as client:
                r = client.get(f"{url}/health")
                if r.status_code == 200:
                    return url
        except Exception:
            continue
    return "http://localhost"

BASE_URL = detect_base_url()
TOTAL_USERS = 500
TARGET_SECTION = "sec-001"
SLOTS = 30

async def register_student(client: httpx.AsyncClient, user_idx: int):
    student_id = f"std-{user_idx:04d}"
    payload = {
        "section_id": TARGET_SECTION,
        "semester_id": "sem-2024-1",
        "prerequisite_course_code": "NONE",
        "section_time_mask": 7,
        "credits": 3,
        "student_id": student_id
    }
    headers = {
        "X-Student-Id": student_id,
        "X-Idempotency-Key": f"race-{student_id}-{TARGET_SECTION}"
    }
    
    try:
        resp = await client.post(
            f"{BASE_URL}/api/v1/registrations",
            json=payload,
            headers=headers,
            timeout=10.0
        )
        return resp.status_code, resp.text
    except Exception as e:
        return 500, str(e)

async def main():
    print("=" * 70)
    print("🚀 BẮT ĐẦU KIỂM THỬ TRANH CHẤP ĐỒNG THỜI (RACE CONDITION LOAD TEST)")
    print(f"👉 Target Endpoint: {BASE_URL}")
    print(f"👉 Mục tiêu: {TOTAL_USERS} sinh viên đồng thời tranh {SLOTS} slot của lớp {TARGET_SECTION}")
    print("=" * 70)

    start_time = time.time()
    
    # Mở connection pool lớn để bắn dồn dập
    limits = httpx.Limits(max_keepalive_connections=200, max_connections=500)
    async with httpx.AsyncClient(limits=limits) as client:
        # Bắn đồng thời 500 coroutines
        tasks = [register_student(client, i) for i in range(1, TOTAL_USERS + 1)]
        results = await asyncio.gather(*tasks)

    elapsed = time.time() - start_time
    
    status_counts = Counter([res[0] for res in results])
    success_count = status_counts.get(200, 0) + status_counts.get(202, 0)
    conflict_count = status_counts.get(409, 0)
    error_count = sum(count for code, count in status_counts.items() if code not in [200, 202, 409])

    print("\n📊 KẾT QUẢ KIỂM THỬ CHI TIẾT:")
    print(f"- Tổng số requests gửi đi:       {TOTAL_USERS}")
    print(f"- Thời gian thực thi:            {elapsed:.2f} giây")
    print(f"- Tốc độ xử lý (Throughput):     {TOTAL_USERS / elapsed:.1f} req/s")
    print(f"- Thành công giữ slot (200/202):  {success_count} (Kỳ vọng: {SLOTS})")
    print(f"- Bị từ chối hết chỗ (409):       {conflict_count} (Kỳ vọng: {TOTAL_USERS - SLOTS})")
    print(f"- Lỗi khác (5xx/Network/429):    {error_count}")

    if error_count > 0:
        error_samples = [res for res in results if res[0] not in [200, 202, 409]][:3]
        print(f"  Chi tiết lỗi mẫu: {error_samples}")

    print("\n🎯 ĐÁNH GIÁ TÍNH TOÀN VẸN (INTEGRITY CHECK):")
    if success_count == SLOTS and conflict_count == (TOTAL_USERS - SLOTS):
        print("✅ [PASSED] TUYỆT ĐỐI KHÔNG BÁN VƯỢT SĨ SỐ (ZERO OVERSELLING)!")
        print(f"   Đúng {SLOTS} slot được cấp phát thành công, {TOTAL_USERS - SLOTS} sinh viên nhận thông báo hết chỗ.")
    elif success_count <= SLOTS:
        print(f"✅ [PASSED] Không có bán vượt sĩ số ({success_count}/{SLOTS} slots được cấp).")
    else:
        print(f"❌ [FAILED] PHÁT HIỆN OVERSELLING: Đã cấp {success_count} chỗ cho lớp {SLOTS} slot!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
