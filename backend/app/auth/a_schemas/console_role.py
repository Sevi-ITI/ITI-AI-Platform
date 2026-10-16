"""ConsoleRole: what a console account may do.
super_admin = everything. supervisor = see every page, use the chatbot, upload NEW documents only.
tester = only the Chat page: ask about the collections a super admin gave them, see only their own chats.
Not called "admin", so it is never confused with the "admin" scope of API keys."""

from typing import Literal

ConsoleRole = Literal["super_admin", "supervisor", "tester"]

