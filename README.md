# Antigravity / Gemini Daily Quota LINE Bot

ระบบแจ้งเตือนโควตาการใช้งาน Antigravity / Gemini (Google AI Pro) เข้า LINE อัตโนมัติทุกวันเวลา **05:47 น. (Asia/Bangkok)** ผ่าน GitHub Actions (ทำงานบน Cloud แม้ปิดเครื่อง Mac)

## รูปแบบข้อความที่ส่งเข้า LINE

```text
☀️ Gemini · <account email>
• ลิมิต 5 ชั่วโมง: <used>% (รีเซ็ต <ว. d MMM HH:mm>)
• ลิมิตรายสัปดาห์: <used>% (รีเซ็ต <ว. d MMM HH:mm>)
<สถานะ>
```

โดย `<สถานะ>` จะคำนวณตามเงื่อนไข:
- **เหลือเวลา `<= 72 ชม.` ก่อนรีเซ็ตรายสัปดาห์ และใช้ไป `< 50%`:**
  `⚠️ ลิมิตรายสัปดาห์ ใช้ไป <used>% เหลือ <x วัน y ชม.> ก่อนรีเซ็ต — ใช้ให้คุ้ม`
- **ใช้ลิมิตรายสัปดาห์ไป `>= 90%`:**
  `🔴 ลิมิตรายสัปดาห์ ใช้ไป <used>% ใกล้เต็ม`
- **กรณีอื่นๆ:**
  `✅ ปกติ`
- **กรณีดึงข้อมูลไม่ได้:**
  `❗ Gemini · <email>`
  `ดึงข้อมูลการใช้งานไม่ได้วันนี้ (<reason>)`

---

## วิธีซิงก์ตัวเลขโควตาจากแถบสถานะ Antigravity IDE บนเครื่อง Mac ขึ้น GitHub

เนื่องจากแถบสถานะของ **Antigravity IDE** ดึงข้อมูลโควตาจากกระบวนการ `language_server` ที่รันอยู่ในเครื่อง Mac ขณะเปิดใช้งาน IDE (ไม่ได้เปิด Public API ให้ภายนอกเรียกโดยตรง) คุณสามารถซิงก์สถานะโควตาล่าสุดจากเครื่อง Mac ขึ้นเก็บไว้ใน Repo นี้ (`quota_state.json`) เพื่อให้ GitHub Actions ส่งสรุปตอน 05:47 น. (แม้ตอน 05:47 น. เครื่อง Mac จะปิดอยู่) ได้ดังนี้:

### 1. โคลน Repo ลงบนเครื่อง Mac
```bash
git clone https://github.com/tonmai7272/antigravity-quota-line-bot.git
cd antigravity-quota-line-bot
```

### 2. รันสคริปต์ดึงค่าจาก Antigravity IDE อัตโนมัติ
ขณะที่เปิดแอป Antigravity IDE อยู่ ให้รัน:
```bash
python3 sync_from_mac_ide.py --push
```
*(คุณสามารถตั้ง `crontab` บนเครื่อง Mac ให้รันคำสั่งนี้ทุกๆ 1 ชั่วโมงตอนที่เปิดเครื่องทำงานอยู่ เช่น `0 * * * * cd /path/to/antigravity-quota-line-bot && python3 sync_from_mac_ide.py --push` เพื่อให้ข้อมูลใน GitHub เป็นค่าล่าสุดเสมอ ก่อนที่คุณจะปิดเครื่องนอน)*

### 3. หรือระบุค่าโควตาด้วยตัวเอง / จากสคริปต์อื่น
```bash
python3 sync_from_mac_ide.py \
  --email "your-email@gmail.com" \
  --five-hour-used 20 \
  --five-hour-reset "2026-11-19T12:00:00+07:00" \
  --weekly-used 35 \
  --weekly-reset "2026-11-21T18:00:00+07:00" \
  --push
```
