"""About routes: the installation check shown on the About screen."""

from fastapi import APIRouter

from kodalo.api.routers.about import doctor

router = APIRouter()
router.include_router(doctor.router)
