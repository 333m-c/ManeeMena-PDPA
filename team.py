"""Roster for the About Us page.

Fill in the three fields for each member. Anything left as an empty string
renders as a blank line on the card, so the page stays presentable while the
team is still being filled in.

    {"nickname": "Chai", "student_id": "67011031", "full_name": "Somchai Jaidee"}

The cards are shown in student-ID order, so a new member can be appended here
rather than slotted into the right position by hand.
"""

MEMBERS = [
    {"nickname": "ฟิล์ม", "student_id": "67010671", "full_name": "ภคพล อวยพร"},
    {"nickname": "การ์ด", "student_id": "67010699", "full_name": "ภัทรวิน ยอดสุขา"},
    {"nickname": "หลง", "student_id": "67010705", "full_name": "ภาคิน โพธิจรรยากุล"},
    {"nickname": "เดียว", "student_id": "67010852", "full_name": "วีรภัทร พิรุฬห์ธรรม"},
    {"nickname": "เตย", "student_id": "67010854", "full_name": "วีรภัทร สว่างจิตต์"},
    {"nickname": "เนเน่", "student_id": "67010858", "full_name": "วีรินทร์ดา เต็มบุญศรัณย์"},
    {"nickname": "ปลื้ม", "student_id": "67010860", "full_name": "วุฒิภัทร วสุภัทรภิญโญ"},
    {"nickname": "อาร์ต", "student_id": "67010917", "full_name": "เศรษฐพงษ์ แก้วนอก"},
    {"nickname": "แคท", "student_id": "67011031", "full_name": "อลิสา วาสิลิกี้ แคทซูลิส"},
    {"nickname": "เจแปน", "student_id": "67011395", "full_name": "กรณ์ กลิ่นทอง"},
]

TEAM = sorted(MEMBERS, key=lambda member: member["student_id"])

FIELDS = (("nickname", "Nickname"), ("student_id", "Student ID"), ("full_name", "Full name"))

# A Thai leading vowel is written before the consonant it belongs to, so an
# avatar showing only the first character would read as a bare vowel mark.
LEADING_VOWELS = "เแโใไ"


def initial(nickname: str) -> str:
    """The short label for a member's avatar."""
    if not nickname:
        return "–"
    return nickname[:2] if nickname[0] in LEADING_VOWELS else nickname[0].upper()
