"""The chat URL table: which URL + method runs which route function, and the errors each one can return. No logic here."""

from fastapi import APIRouter
from fastapi.sse import EventSourceResponse

from app.chat.a_schemas.chat_response import ChatResponse
from app.chat.a_schemas.conversation_summary import ConversationSummary
from app.chat.a_schemas.message_out import MessageOut
from app.chat.f_routes.get_conversation_messages import get_conversation_messages
from app.chat.f_routes.get_conversations import get_conversations
from app.chat.f_routes.post_chat import post_chat
from app.chat.f_routes.post_chat_stream import post_chat_stream
from app.core.e_errors.error_docs import error_docs

EVERY_CALL = ("invalid_api_key", "scope_forbidden", "invalid_request", "internal_error")
ASKING = ("collection_forbidden", "collection_not_found", "conversation_not_found")
STREAM_EVENTS = (
    "A stream of Server-Sent Events, in this order:\n\n"
    "1. **meta** {conversation_id, request_id}\n"
    "2. **token** {text}, many: append each to the screen\n"
    "3. **done** {answer, found, citations}: replace the shown text with answer (it can differ from the tokens)\n\n"
    "or, if it fails after it started, **error** {code, message}: llm_busy, llm_unavailable or internal_error."
)

router = APIRouter(tags=["chat"])
router.add_api_route(
    "/v1/chat", post_chat, methods=["POST"], summary="Ask a question", response_model=ChatResponse,
    responses=error_docs(*EVERY_CALL, *ASKING, "llm_busy", "llm_unavailable"),
)
router.add_api_route(
    "/v1/chat/stream", post_chat_stream, methods=["POST"], summary="Ask a question, answer streamed",
    response_class=EventSourceResponse, responses={200: {"description": STREAM_EVENTS}} | error_docs(*EVERY_CALL, *ASKING),
)
router.add_api_route(
    "/v1/conversations", get_conversations, methods=["GET"], summary="List the user's conversations",
    response_model=list[ConversationSummary], responses=error_docs(*EVERY_CALL),
)
router.add_api_route(
    "/v1/conversations/{conversation_id}/messages", get_conversation_messages, methods=["GET"],
    summary="Read one conversation", response_model=list[MessageOut],
    responses=error_docs(*EVERY_CALL, "conversation_not_found"),
)
