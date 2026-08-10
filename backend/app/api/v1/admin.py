"""Admin-only endpoints."""

from fastapi import APIRouter, Depends

from app.api.deps import require_role
from app.models.user import User, UserRole

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get(
    "/test",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def admin_test(current_user: User = Depends(require_role(UserRole.ADMIN))):
    """Test endpoint — accessible only to ADMIN users.

    This endpoint exists for Phase 1 RBAC verification and can be
    removed once real admin endpoints are implemented.
    """
    return {
        "message": "Admin access granted.",
        "admin_id": current_user.id,
        "admin_email": current_user.email,
    }
