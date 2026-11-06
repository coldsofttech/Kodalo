"""The doctor route: what the About screen shows about the installation."""

from fastapi import APIRouter

from kodalo.api.deps import (
    data_dir,
)
from kodalo.api.routers.common import (
    COMMON,
)
from kodalo.api.schemas import (
    DoctorCheck,
    DoctorResponse,
)
from kodalo.core.doctor import passed, run_checks

router = APIRouter()


@router.get("/doctor", summary="Diagnose the installation", responses=COMMON)
def doctor() -> DoctorResponse:
    """Run the same checks as `kodalo doctor`: versions, libraries, data folder and database."""
    checks = run_checks(data_dir())
    return DoctorResponse(healthy=passed(checks), checks=[DoctorCheck.from_core(c) for c in checks])
