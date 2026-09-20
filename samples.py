"""Fictional, bundled examples. User input is never written here."""

SAMPLES = [
    {
        "id": "customer", "title": "Customer activity", "tag": "ALL 5 RULES",
        "description": "A customer log with Thai address data, payment details and a date of birth.",
        "text": "[2026-09-20 14:32:01] Customer Login\n\nName: Somchai Jaidee\nEmail: somchai.jaidee@example.com\nPhone: 093-245-7894\nDOB:25/12/2549\nCredit Card: 1234-5678-9012-3456\nAddress: 689 ซอยลาดกระบัง 19 ถนนลาดกระบัง แขวงลาดกระบัง เขตลาดกระบัง กรุงเทพฯ\n\nPayment completed successfully.",
    },
    {
        "id": "payments", "title": "Payment service", "tag": "MULTIPLE MATCHES",
        "description": "Seven matches across a service log. Try disabling email masking and scan again.",
        "text": "[INFO] Payment batch started\nCard: 1234-5678-9012-3456\nEmail: card@example.com\nPhone: 093-245-7894\nEmail: support+demo@example.org\nPhone: 081-123-4567\nDOB: 01/01/2500\nAddress: 99/12 ถนนสุขุมวิท เขตวัฒนา กรุงเทพฯ\n[INFO] Payment batch completed",
    },
    {
        "id": "boundaries", "title": "Explore the boundaries", "tag": "EDGE CASES",
        "description": "Short usernames, an emoji, unformatted numbers and dates without a DOB label.",
        "text": "🧪 Regex boundary test\nEmail: a@example.com\nEmail: ab@example.com\nEmail: user_name123@test.com\nUnformatted card: 1234567890123456\nUnformatted phone: 0811234567\nUnlabelled date: 25/12/2549\nDOB: 25/12/2549\nAddress: 12/3 หมู่ 4 ถนนตัวอย่าง\nHTML is text: <strong>Hello</strong>",
    },
]
