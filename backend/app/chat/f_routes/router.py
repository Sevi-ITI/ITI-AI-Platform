"""The chat URL table: which URL + method runs which route function. No logic here."""

from fastapi import APIRouter
from fastapi.sse import EventSourceResponse

from app.chat.a_schemas.chat_response import ChatResponse
from app.chat.a_schemas.conversation_summary import ConversationSummary
from app.chat.a_schemas.message_out import MessageOut
from app.chat.f_routes.get_conversation_messages import get_conversation_messages
from app.chat.f_routes.get_conversations import get_conversations
from app.chat.f_routes.post_chat import post_chat
from app.chat.f_routes.post_chat_stream import post_chat_stream
from app.core.e_errors.error_responses import ERROR_RESPONSES

router = APIRouter(tags=["chat"], responses=ERROR_RESPONSES)
router.add_api_route("/v1/chat", post_chat, methods=["POST"], response_model=ChatResponse)
router.add_api_route("/v1/chat/stream", post_chat_stream, methods=["POST"], response_class=EventSourceResponse)
router.add_api_route("/v1/conversations", get_conversations, methods=["GET"], response_model=list[ConversationSummary])
router.add_api_route(
    "/v1/conversations/{conversation_id}/messages",
    get_conversation_messages,
    methods=["GET"],
    response_model=list[MessageOut],
)
