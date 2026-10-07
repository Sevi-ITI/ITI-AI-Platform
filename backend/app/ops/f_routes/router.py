"""The ops URL table. No logic here."""

from fastapi import APIRouter

from app.ops.f_routes.get_health import get_health

router = APIRouter(tags=["ops"])
router.add_api_route("/health", get_health, methods=["GET"])