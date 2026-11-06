from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.dependencies import get_current_user
from app.services.connector_service import SlackReadConnector, ConnectorUnavailable, ConnectorRateLimited


router = APIRouter(prefix="/connectors", tags=["Read-only connectors"])


@router.get("/slack/history")
def slack_history(channel_id: str = Query(pattern=r"^[CG][A-Z0-9]{8,31}$"),
                  limit: int = Query(15, ge=1, le=15),
                  cursor: str = Query("", max_length=512, pattern=r"^[A-Za-z0-9+/=_-]*$"),
                  user=Depends(get_current_user)):
    try:
        return SlackReadConnector(user.customer_id).read_page(channel_id, limit, cursor)
    except PermissionError:
        raise HTTPException(403, "Channel not authorized") from None
    except ConnectorRateLimited as error:
        raise HTTPException(429, "Connector rate limited", headers={"Retry-After": str(error.retry_after)}) from None
    except ConnectorUnavailable:
        raise HTTPException(503, "Tenant Slack connector unavailable") from None
