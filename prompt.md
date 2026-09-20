# Project: PDPA Data Masking Web Application

## ระบบเซ็นเซอร์ข้อมูลลูกค้าเพื่อความปลอดภัยด้วย Regular Expression

พัฒนา Web Application สำหรับ Assignment วิชา Theory of Computation โดยระบบต้องใช้ **Python Regular Expression (`re`) เป็นหลักในการตรวจจับและทำ Data Masking เท่านั้น**

เป้าหมายของระบบคือรับข้อความหรือ Log จากผู้ใช้ ตรวจจับข้อมูลส่วนบุคคลที่อาจหลุดออกมา และทำการเซ็นเซอร์ข้อมูลตามหลัก PDPA ก่อนนำข้อความไปใช้งานต่อ

---

# IMPORTANT: อ่านโค้ดเดิมก่อนเริ่มพัฒนา

ภายใน Project มีโฟลเดอร์ชื่อ:

```text
regex/
```

ในโฟลเดอร์นี้มีโค้ด Regular Expression ที่ฉันเขียนไว้แล้วสำหรับตรวจจับและ Mask ข้อมูลบางประเภท

ก่อนเขียนระบบใหม่:

1. อ่านไฟล์ทั้งหมดใน `regex/`
2. วิเคราะห์ว่า Regex แต่ละตัวทำงานอย่างไร
3. พยายาม reuse หลักการและ Regex เดิมของฉันให้มากที่สุด
4. หาก Regex เดิมมี bug, edge case หรือใช้งานกับ Web Application ไม่สะดวก ให้ปรับแก้
5. อย่า rewrite ใหม่ทั้งหมดโดยไม่มีเหตุผล
6. แยก logic Regex ออกจาก Web route / UI อย่างชัดเจน
7. Web Application ต้อง import และเรียกใช้ module Regex จากโฟลเดอร์นี้
8. ถ้ามีการแก้ Regex ให้รักษาหลักการที่เข้าใจง่ายเพื่อสามารถเอาไปอธิบายตอนพรีเซนต์ได้

ตัวอย่างแนวทาง:

```python
from regex.masker import mask_text

masked_text = mask_text(input_text)
```

ไม่ควรนำ Regex ทั้งหมดไปเขียนกระจายไว้ใน route หรือ frontend

---

# Core Requirement

Input:

ผู้ใช้พิมพ์หรือ paste ข้อความ / Log ลงใน Web Application

Output:

ข้อความที่ถูก Data Masking แล้ว

ระบบต้องรองรับข้อมูลอย่างน้อย 5 ประเภทดังต่อไปนี้

---

# 1. Credit Card Number

รูปแบบ:

```text
XXXX-XXXX-XXXX-XXXX
```

ตัวอย่าง:

```text
1234-5678-9012-3456
```

ต้องได้:

```text
XXXX-XXXX-XXXX-3456
```

เปิดเผยเฉพาะเลข 4 ตัวสุดท้าย

ตัวอย่างหลายค่าใน Log:

```text
Card: 1234-5678-9012-3456
Payment using 4444-5555-6666-7777
```

Output:

```text
Card: XXXX-XXXX-XXXX-3456
Payment using XXXX-XXXX-XXXX-7777
```

---

# 2. Email Address

ต้องซ่อน username ของ Email ยกเว้น:

* ตัวอักษรตัวแรก
* ตัวอักษรตัวสุดท้ายก่อน `@`
* domain ต้องเปิดเผยทั้งหมด

ตัวอย่าง:

```text
somchai.d@company.com
```

Output:

```text
s********d@company.com
```

อีกตัวอย่าง:

```text
card@gmail.com
```

Output:

```text
c**d@gmail.com
```

ต้องรองรับ email ที่ประกอบด้วย:

```text
A-Z
a-z
0-9
.
_
%
+
-
```

ควรจัดการ email username สั้น ๆ เช่น:

```text
a@gmail.com
ab@gmail.com
```

โดยไม่ทำให้โปรแกรม error

---

# 3. Phone Number

รูปแบบ:

```text
XXX-XXX-XXXX
```

เช่น:

```text
093-245-7894
```

Output:

```text
XXX-XXX-7894
```

เปิดเผยเฉพาะเลข 4 ตัวท้าย

---

# 4. Date of Birth

ข้อมูลต้องขึ้นต้นด้วย:

```text
DOB:
```

รูปแบบ:

```text
DOB:25/12/2549
```

Output:

```text
DOB:XX/XX/25XX
```

หลักการ:

* ปิดวัน
* ปิดเดือน
* เปิดเผย 2 หลักแรกของปี พ.ศ.
* ปิด 2 หลักหลัง

ต้องรองรับกรณีมี space เช่น:

```text
DOB: 25/12/2549
```

และพยายามคง formatting เดิมเอาไว้

---

# 5. Address

ข้อมูลขึ้นต้นด้วย:

```text
Address:
```

ตัวอย่าง:

```text
Address: 689 ซอยลาดกระบัง 19 ถนนลาดกระบัง แขวงลาดกระบัง เขตลาดกระบัง กรุงเทพฯ
```

Output:

```text
Address: XXX ซอยลาดกระบัง 19 ถนนลาดกระบัง แขวงลาดกระบัง เขตลาดกระบัง กรุงเทพฯ
```

Mask เฉพาะเลขที่บ้านตัวแรกหลังคำว่า:

```text
Address:
```

ข้อมูลส่วนอื่นของที่อยู่ต้องเหมือนเดิม

ต้องรองรับ:

```text
Address: 45 ถนน...
Address: 99/12 ถนนสุขุมวิท...
Address: 12/3 หมู่ 4...
```

ตัวอย่าง:

```text
Address: 99/12 ถนนสุขุมวิท แขวง...
```

Output:

```text
Address: XXX ถนนสุขุมวิท แขวง...
```

---

# Main Page Design

ออกแบบเป็น Modern Security Dashboard

Theme:

* Dark / Navy
* Security / Cybersecurity style
* Accent สีเขียว, cyan หรือ blue
* responsive
* ใช้งานได้ทั้ง Desktop และ Mobile

หน้าเว็บไม่ควรเป็นเพียง textarea 2 ช่องธรรมดา

โครงสร้างแนะนำ:

```text
Navbar
 ├─ Logo
 ├─ Data Masker
 ├─ Regex Playground
 ├─ Examples
 ├─ About PDPA
 └─ GitHub

Hero / Header
 └─ PDPA Sensitive Data Masking

Main Workspace
 ├─ Input Log
 ├─ Scan / Mask Button
 ├─ Output
 └─ Scan Statistics

Detection Panel
 ├─ Credit Card
 ├─ Email
 ├─ Phone
 ├─ DOB
 └─ Address
```

---

# Feature 1: Live Data Masking

ให้ผู้ใช้ paste Log ลงใน textarea

มีปุ่ม:

```text
Scan & Mask
```

เมื่อกดแล้ว Backend จะใช้ Python `re` ตรวจสอบและทำ Mask

Output แสดงด้านขวา

Desktop:

```text
Input Log       |       Masked Log
```

Mobile:

```text
Input Log
Masked Log
```

---

# Feature 2: Highlight Sensitive Data

ก่อน Mask ให้ระบบสามารถแสดงว่าตรวจพบ Sensitive Data ตำแหน่งไหน

เช่น:

```text
Customer Email: somchai@gmail.com
Phone: 093-245-7894
```

ให้ Highlight:

* Email
* Phone
* Credit Card
* DOB
* Address

แต่ละประเภทสามารถมีสีหรือ Badge ต่างกัน

เช่น:

```text
EMAIL
PHONE
CREDIT CARD
DOB
ADDRESS
```

Feature นี้ใช้สำหรับ visualization เท่านั้น

Detection และ Matching ต้องมาจาก Python Regex เดิม

---

# Feature 3: Detection Statistics

หลัง Scan ให้แสดง Summary:

```text
Sensitive Data Found: 7

Credit Card : 1
Email       : 2
Phone       : 2
DOB         : 1
Address     : 1
```

แสดงเป็น Card / Badge

เพื่อให้ตอน Demo เห็นชัดว่า Regex ตรวจอะไรได้บ้าง

---

# Feature 4: Before / After Comparison

สร้าง Compare Mode

ตัวอย่าง:

```text
BEFORE
Customer card 1234-5678-9012-3456

AFTER
Customer card XXXX-XXXX-XXXX-3456
```

Highlight เฉพาะส่วนที่ถูกแก้

---

# Feature 5: Regex Explanation

เพิ่มหน้า:

```text
/regex-playground
```

แสดง Regular Expression ของแต่ละประเภท

ตัวอย่าง:

```text
Credit Card
Pattern:
(\d{4})-(\d{4})-(\d{4})-(\d{4})

Purpose:
แบ่ง Credit Card เป็น 4 กลุ่ม
จากนั้นเก็บ Group 4 ไว้และ Mask Group 1-3
```

ต้องอธิบาย Regex เป็นส่วน ๆ

เช่น:

```text
\d
{4}
(...)
(?=...)
(?<=...)
^
$
[]
+
*
?
```

เฉพาะ syntax ที่ Project นี้ใช้จริง

หน้า Regex Playground สำคัญมาก เพราะ Assignment เน้นเรื่อง Regular Expression

---

# Feature 6: Toggle Masking Rules

ให้ผู้ใช้สามารถเลือกได้ว่าจะ Mask ข้อมูลอะไร

ตัวอย่าง:

```text
[x] Credit Card
[x] Email
[x] Phone
[x] Date of Birth
[x] Address
```

ถ้าปิด Email:

Email จะไม่ถูก Mask

Backend ต้องรับ configuration แล้วเลือกเรียก Regex ตาม Rule ที่เปิดอยู่

---

# Feature 7: Sample Logs

มีปุ่ม:

```text
Load Sample Log
```

สร้างตัวอย่างเช่น:

```text
[2026-09-20 14:32:01] Customer Login

Name: Somchai Jaidee
Email: somchai.jaidee@gmail.com
Phone: 093-245-7894
DOB:25/12/2549
Credit Card: 1234-5678-9012-3456
Address: 689 ซอยลาดกระบัง 19 ถนนลาดกระบัง แขวงลาดกระบัง เขตลาดกระบัง กรุงเทพฯ

Payment completed successfully.
```

จากนั้นผู้ใช้กด:

```text
Scan & Mask
```

ได้:

```text
[2026-09-20 14:32:01] Customer Login

Name: Somchai Jaidee
Email: s*************e@gmail.com
Phone: XXX-XXX-7894
DOB:XX/XX/25XX
Credit Card: XXXX-XXXX-XXXX-3456
Address: XXX ซอยลาดกระบัง 19 ถนนลาดกระบัง แขวงลาดกระบัง เขตลาดกระบัง กรุงเทพฯ

Payment completed successfully.
```

---

# Feature 8: Risk Score

สามารถเพิ่ม Scan Result แบบ:

```text
Privacy Risk

LOW
MEDIUM
HIGH
CRITICAL
```

คำนวณง่าย ๆ จากจำนวน Sensitive Data ที่พบ

เช่น:

```text
0       = Safe
1-2     = Low
3-5     = Medium
6-10    = High
>10     = Critical
```

ต้องระบุใน UI ชัดเจนว่าเป็น:

```text
Demo Privacy Risk Score
```

ไม่ใช่ PDPA Compliance Score จริง

---

# Feature 9: Log Inspector

เมื่อ Regex ตรวจพบข้อมูล ให้แสดงรายการ:

```text
Detected Sensitive Information

Email
somchai@gmail.com
Line 4

Phone
093-245-7894
Line 5

Credit Card
1234-5678-9012-3456
Line 7
```

ในหน้า Inspector ควร Mask preview ด้วยเพื่อไม่แสดงข้อมูลเต็มโดยไม่จำเป็น

---

# Feature 10: Copy & Download

เพิ่ม:

```text
Copy Masked Text
Download Masked Log
Clear
```

ไฟล์ Download เช่น:

```text
masked_log.txt
```

ไม่จำเป็นต้องเก็บ Log ลง Database

---

# Feature 11: Privacy First Mode

เพิ่มข้อความ:

```text
Your data is processed temporarily and is not stored.
```

และออกแบบระบบให้:

* ไม่ save input ลง DB
* ไม่ log raw sensitive data ลง console
* ไม่ส่งข้อมูลไป third-party service
* ประมวลผลแล้วคืนผลทันที

เหมาะกับ Concept ของ PDPA

---

# Feature 12: Real-time Character / Line Counter

ใต้ Input:

```text
Characters: 1,204
Lines: 24
```

และ Output:

```text
Sensitive Data Found: 7
Masked Characters: 43
```

---

# Feature 13: Explain Detection

เมื่อคลิกผล Detection เช่น Email

แสดง:

```text
Why was this detected?
```

แล้วแสดง:

```text
Matched Pattern:
[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}

Matched Text:
somchai@gmail.com
```

พร้อมคำอธิบายแต่ละส่วน

Feature นี้เหมาะมากสำหรับใช้พรีเซนต์ Regular Expression

---

# Suggested Backend Structure

ถ้า Project เดิมไม่ได้กำหนด Framework ให้ใช้ Flask

โครงสร้างประมาณ:

```text
project/
│
├── app.py
│
├── regex/
│   ├── __init__.py
│   ├── credit_card.py
│   ├── email.py
│   ├── phone.py
│   ├── dob.py
│   ├── address.py
│   └── masker.py
│
├── templates/
│   ├── index.html
│   ├── regex.html
│   └── about.html
│
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
│
├── tests/
│   └── test_regex.py
│
├── requirements.txt
└── README.md
```

แต่ก่อนสร้างหรือย้ายไฟล์ ต้องตรวจสอบ Structure ปัจจุบันก่อน

อย่าทำลาย Project เดิมโดยไม่จำเป็น

---

# Regex Module Design

สร้าง API กลาง เช่น:

```python
def mask_credit_card(text):
    ...

def mask_email(text):
    ...

def mask_phone(text):
    ...

def mask_dob(text):
    ...

def mask_address(text):
    ...

def mask_text(text, enabled_rules=None):
    ...
```

ตัวอย่าง:

```python
result = mask_text(
    input_text,
    enabled_rules=[
        "credit_card",
        "email",
        "phone",
        "dob",
        "address"
    ]
)
```

ควรสามารถ return metadata ได้ด้วย:

```python
{
    "masked_text": "...",
    "total_detected": 5,
    "counts": {
        "credit_card": 1,
        "email": 1,
        "phone": 1,
        "dob": 1,
        "address": 1
    }
}
```

หากเหมาะสมสามารถเพิ่ม:

```python
"detections": [...]
```

สำหรับหน้า Inspector

---

# API

สร้าง endpoint เช่น:

```text
POST /api/mask
```

Request:

```json
{
    "text": "Customer email is card@gmail.com",
    "rules": {
        "credit_card": true,
        "email": true,
        "phone": true,
        "dob": true,
        "address": true
    }
}
```

Response:

```json
{
    "success": true,
    "masked_text": "Customer email is c**d@gmail.com",
    "total_detected": 1,
    "counts": {
        "credit_card": 0,
        "email": 1,
        "phone": 0,
        "dob": 0,
        "address": 0
    }
}
```

---

# Important Regex Rule

โจทย์ Assignment ระบุว่า:

```text
เรียกใช้ Regex (Python re เท่านั้น)
```

ดังนั้น Sensitive Data Detection และ Data Masking ทั้งหมดต้องใช้:

```python
import re
```

ห้ามเปลี่ยนไปใช้ library เช่น:

```text
email-validator
phonenumbers
presidio
spaCy
NER
AI / LLM detection
```

สามารถใช้ JavaScript สำหรับ UI ได้

แต่การตัดสินใจว่า Text ใดเป็น Sensitive Data ต้องเกิดจาก Python Regex

---

# Edge Cases ที่ต้อง Test

Credit Card:

```text
1234-5678-9012-3456
0000-1111-2222-3333
```

ไม่ควรจับ:

```text
123-456
1234567890123456
```

ถ้า Requirement กำหนดเฉพาะ format ที่มี `-`

---

Email:

```text
card@gmail.com
somchai.jaidee@company.co.th
user_name123@test.com
a@gmail.com
ab@gmail.com
```

---

Phone:

```text
093-245-7894
081-123-4567
```

ไม่ควรจับ:

```text
0811234567
```

หาก Requirement ต้องการเฉพาะ `XXX-XXX-XXXX`

---

DOB:

```text
DOB:25/12/2549
DOB: 25/12/2549
DOB:01/01/2500
```

---

Address:

```text
Address: 689 ถนนลาดกระบัง แขวงลาดกระบัง เขตลาดกระบัง กรุงเทพฯ
Address: 99/12 ถนนสุขุมวิท เขตวัฒนา กรุงเทพฯ
Address: 12/3 หมู่ 4 ถนน...
```

ต้อง Mask เฉพาะบ้านเลขที่

---

# Unit Tests

สร้าง Test ให้ Regex ทุกประเภท

เช่น:

```python
def test_credit_card():
    input_text = "Card: 1234-5678-9012-3456"
    expected = "Card: XXXX-XXXX-XXXX-3456"
    assert mask_credit_card(input_text) == expected
```

รวมถึง edge cases

เป้าหมายคือใช้ Test ยืนยันว่าเมื่อเอา Regex เดิมจาก `regex/` มาปรับแล้ว Behavior ยังถูกต้อง

---

# README

สร้าง README ที่อธิบาย:

```text
1. Project Overview
2. Assignment Requirement
3. Features
4. Technology Stack
5. Project Structure
6. Installation
7. How to Run
8. Regular Expressions Used
9. Example Input / Output
10. Privacy Design
11. Team Members / Responsibilities
12. GitHub / Demo URL
```

ส่วน Regular Expression ต้องอธิบายอย่างละเอียดเพื่อใช้เป็นข้อมูลตอน Presentation

---

# GitHub Link

หน้า Web Application ต้องมี GitHub button ชัดเจน เช่น:

```text
View Source Code
```

Navbar หรือ Footer ก็ได้

สร้าง config / placeholder สำหรับ GitHub URL เพื่อแก้ง่าย

---

# Presentation Friendly

ระบบต้องออกแบบให้สามารถ Demo ในคลิปไม่เกิน 10 นาทีได้ง่าย

Flow แนะนำ:

```text
1. อธิบายปัญหา Personal Data Leak
2. แสดง Input Log
3. Scan Sensitive Data
4. แสดง Regex Detection
5. อธิบาย Regex แต่ละตัว
6. Mask Data
7. Compare Before / After
8. Toggle Rules
9. เปิด Regex Playground
10. สรุป PDPA และ Privacy Design
```

ดังนั้น UI ต้องคลิก Demo ได้ง่ายและไม่ซับซ้อนเกินไป

---

# Additional Requirements

* รองรับภาษาไทย UTF-8
* responsive
* Error handling
* Empty input validation
* ไม่ reload หน้าโดยไม่จำเป็น
* UI มี loading state ตอน Scan
* Copy button ต้องทำงานจริง
* Download ต้องทำงานจริง
* Source Code button ต้องทำงาน
* Regex Explanation ต้องอ้างอิง Regex ที่ระบบใช้จริง ไม่ใช่ข้อความ hardcode ที่ไม่ตรงกับ code
* หลีกเลี่ยง code duplication
* เขียน comment ในส่วน Regex ที่ซับซ้อน
* ชื่อ function และ variable อ่านง่าย

---

# Development Workflow

ก่อนแก้ code:

1. Inspect Project Structure
2. Inspect ทุกไฟล์ใน `regex/`
3. สรุป Regex ที่มีอยู่
4. ระบุ bug / limitation ของ Regex เดิม
5. ปรับ Regex เท่าที่จำเป็น
6. สร้าง reusable Regex masking module
7. เชื่อมเข้ากับ Backend
8. สร้าง API
9. สร้าง Frontend
10. เพิ่ม Statistics / Inspector / Playground
11. เขียน Tests
12. Run Tests
13. ทดสอบ Web Application
14. อัปเดต README

ห้ามข้ามขั้นตอนการอ่าน `regex/`

---

# Definition of Done

Project ถือว่าเสร็จเมื่อ:

* Credit Card masking ถูกต้อง
* Email masking ถูกต้อง
* Phone masking ถูกต้อง
* DOB masking ถูกต้อง
* Address masking ถูกต้อง
* ใช้ Python `re`
* Regex ถูกแยกเป็น module
* Web เรียกใช้ Regex module จริง
* Input/Output ใช้งานได้จริง
* Toggle Rules ใช้งานได้
* Detection Statistics ใช้งานได้
* Sample Log ใช้งานได้
* Regex Explanation มี
* Copy ใช้งานได้
* Download ใช้งานได้
* GitHub Link มี
* Responsive
* Tests ผ่าน
* README อัปเดต
* ไม่มี raw sensitive information ถูกเก็บลง Database หรือ application log โดยไม่จำเป็น

หลังจากพัฒนาเสร็จ ให้สรุป:

1. ไฟล์ที่แก้
2. ไฟล์ที่เพิ่ม
3. Regex เดิมตัวไหนถูก reuse
4. Regex ตัวไหนถูกแก้ และเพราะอะไร
5. Feature ที่ทำเสร็จ
6. Test ที่ทำ
7. วิธี Run Project
8. สิ่งที่ยังเหลือหรือควรปรับปรุง
