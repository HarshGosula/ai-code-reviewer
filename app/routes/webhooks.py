from fastapi import APIRouter

router = APIRouter()

@router.get("/test")
async def test_webhook():
    """Test endpoint to verify webhook route is working"""
    return {
        "message": "Webhook endpoint is working",
        "supported_events": ["pull_request", "issue_comment"],
    }