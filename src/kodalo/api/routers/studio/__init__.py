"""Studio routes: the repository a post is made from, then its ideas, copy and design."""

from fastapi import APIRouter

from kodalo.api.routers.studio import copy, design, ideas, repositories, source

router = APIRouter(tags=["v1"])
router.include_router(source.router)
router.include_router(repositories.router)
router.include_router(ideas.router)
router.include_router(copy.router)
router.include_router(design.router)
