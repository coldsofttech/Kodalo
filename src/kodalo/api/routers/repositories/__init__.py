"""Repository routes: the GitHub repositories and local folders that posts are made from."""

from fastapi import APIRouter

from kodalo.api.routers.repositories import crud, images

router = APIRouter(tags=["v1"])
router.include_router(crud.router)
router.include_router(images.router)
