"""Roster for the About Us page.

Fill in the fields for each member. Anything left as an empty string renders
as a blank line on the card, so the page stays presentable while the team is
still being filled in.

    {"nickname": "ไชย", "english": "Chai", "student_id": "67011031",
     "full_name": "สมชาย ใจดี"}

``english`` is the romanised nickname. Only its first letter is shown, in the
avatar; the card itself shows the Thai nickname.

The cards are shown in student-ID order, so a new member can be appended here
rather than slotted into the right position by hand.
"""

MEMBERS = [
    {"nickname": "ฟิล์ม", "english": "Film", "student_id": "67010671", "full_name": "ภคพล อวยพร"},
    {"nickname": "การ์ด", "english": "Guard", "student_id": "67010699", "full_name": "ภัทรวิน ยอดสุขา"},
    {"nickname": "หลง", "english": "Long", "student_id": "67010705", "full_name": "ภาคิน โพธิจรรยากุล"},
    {"nickname": "เดียว", "english": "Deaw", "student_id": "67010852", "full_name": "วีรภัทร พิรุฬห์ธรรม"},
    {"nickname": "เตย", "english": "Toey", "student_id": "67010854", "full_name": "วีรภัทร สว่างจิตต์"},
    {"nickname": "เนเน่", "english": "Nene", "student_id": "67010858", "full_name": "วีรินทร์ดา เต็มบุญศรัณย์"},
    {"nickname": "ปลื้ม", "english": "Pleum", "student_id": "67010860", "full_name": "วุฒิภัทร วสุภัทรภิญโญ"},
    {"nickname": "อาร์ต", "english": "Art", "student_id": "67010917", "full_name": "เศรษฐพงษ์ แก้วนอก"},
    {"nickname": "แคท", "english": "Cat", "student_id": "67011031", "full_name": "อลิสา วาสิลิกี้ แคทซูลิส"},
    {"nickname": "เจแปน", "english": "Japan", "student_id": "67011395", "full_name": "กรณ์ กลิ่นทอง"},
]

TEAM = sorted(MEMBERS, key=lambda member: member["student_id"])

FIELDS = (("nickname", "Nickname"), ("student_id", "Student ID"), ("full_name", "Full name"))


def initial(english: str) -> str:
    """The avatar letter: the first letter of the romanised nickname."""
    return english[:1].upper() if english else "–"
