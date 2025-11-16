from machine import ADC, Pin
import time

# === 配置区域 ===
adc = ADC(Pin(3))         # ⚠️ 这里填写你用于测电池的 ADC GPIO
adc.atten(ADC.ATTN_11DB)  # 推荐：读取范围提升到 0~3.3V
adc.width(ADC.WIDTH_12BIT)
print(adc.read_u16())

# VREF = 3.3                # ADC满量程电压
# DIV_RATIO = 2.0           # 分压比 2倍
# FULL = 4.20               # 满电压
# EMPTY = 3.30              # 0% 电压
# SAMPLES = 16              # 均值滤波
# HYST = 0.3                # 滞回（0.3 档）
# 
# _last_level = 0           # 上一次电量档位
# 
# 
# # === 读取电压（带均值滤波） ===
# def read_voltage():
#     total = 0
#     for _ in range(SAMPLES):
#         total += adc.read_u16()
#         time.sleep_us(200)
#     raw = total / SAMPLES
#     adc_v = raw * VREF / 65535
#     real_v = adc_v * DIV_RATIO
#     return real_v
# 
# 
# # === 电压换算成 0～9 档，并带滞回 ===
# def get_battery_level():
#     global _last_level
# 
#     v = read_voltage()
# 
#     # 限制范围
#     if v >= FULL:
#         level = 9
#     elif v <= EMPTY:
#         level = 0
#     else:
#         percent = (v - EMPTY) / (FULL - EMPTY) * 100
#         level = int(percent / 10)  # 转换为 0~9 档
# 
#     # === 滞回（防跳变） ===
#     if abs(level - _last_level) >= HYST:
#         _last_level = level
# 
#     return _last_level
# 
# 
# # === 主循环 ===
# while True:
#     lv = get_battery_level()
#     print("Battery Level:", lv)
#     time.sleep(1)
