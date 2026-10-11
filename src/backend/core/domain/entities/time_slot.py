from dataclasses import dataclass

@dataclass(frozen=True)
class TimeSlot:
    """
    Biểu diễn một khung thời gian học trong tuần.
    - schedule_day: 2 (Thứ Hai), 3 (Thứ Ba), ..., 7 (Thứ Bảy), 8 (Chủ Nhật).
    - start_period: Tiết bắt đầu (1 đến 12).
    - end_period: Tiết kết thúc (1 đến 12).
    - Mã hóa thành 84-bit bitmap: 7 ngày * 12 tiết/ngày.
    """
    schedule_day: int
    start_period: int
    end_period: int

    def compute_mask(self) -> int:
        if not (2 <= self.schedule_day <= 8):
            raise ValueError(f"schedule_day must be between 2 and 8, got {self.schedule_day}")
        if not (1 <= self.start_period <= self.end_period <= 12):
            raise ValueError(f"Invalid periods: {self.start_period} to {self.end_period}")

        day_offset = (self.schedule_day - 2) * 12
        mask = 0
        for period in range(self.start_period, self.end_period + 1):
            bit_index = day_offset + (period - 1)
            mask |= (1 << bit_index)
        return mask
