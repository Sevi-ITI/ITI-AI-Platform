"""ConsoleRole: what a console account may do.
super_admin = everything. supervisor = see every page, use the chatbot, upload NEW documents only.
Not called "admin", so it is never confused with the "admin" scope of API keys."""

from typing import Literal

ConsoleRole = Literal["super_admin", "supervisor"]

