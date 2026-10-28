from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db
from app.robots import check_robots_txt
from app.schemas import SourceCreate, SourceResponse, SourceUpdate


router = APIRouter(
    prefix="/sources",
    tags=["Sources"]
)


# --------------------------------------------------
# POST /sources
# Create a new source
# --------------------------------------------------

@router.post(
    "",
    response_model=SourceResponse,
    status_code=201
)
def create_source(
    source_data: SourceCreate,
    db: Session = Depends(get_db)
):
    base_url = str(source_data.base_url)

    # Check duplicate URL
    existing_source = crud.get_source_by_url(
        db,
        base_url
    )

    if existing_source:
        raise HTTPException(
            status_code=409,
            detail="A source with this URL already exists."
        )

    # Check robots.txt
    robots_allowed, robots_status = check_robots_txt(
        base_url
    )

    # Create source
    try:
        source = crud.create_source(
            db=db,
            source_data=source_data,
            robots_allowed=robots_allowed,
            robots_status=robots_status
        )

        return source

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="A source with this URL already exists."
        )


# --------------------------------------------------
# GET /sources
# List sources
# --------------------------------------------------

@router.get(
    "",
    response_model=list[SourceResponse]
)
def get_sources(
    active_only: bool = Query(
        default=False,
        description="Return only active sources"
    ),
    db: Session = Depends(get_db)
):
    return crud.get_sources(
        db,
        active_only=active_only
    )


# --------------------------------------------------
# GET /sources/{source_id}
# Get one source
# --------------------------------------------------

@router.get(
    "/{source_id}",
    response_model=SourceResponse
)
def get_source(
    source_id: int,
    db: Session = Depends(get_db)
):
    source = crud.get_source(
        db,
        source_id
    )

    if not source:
        raise HTTPException(
            status_code=404,
            detail="Source not found."
        )

    return source


# --------------------------------------------------
# PUT /sources/{source_id}
# Update source
# --------------------------------------------------
@router.put(
    "/{source_id}",
    response_model=SourceResponse
)
def update_source(
    source_id: int,
    source_data: SourceUpdate,
    db: Session = Depends(get_db)
):
    source = crud.get_source(
        db,
        source_id
    )

    if not source:
        raise HTTPException(
            status_code=404,
            detail="Source not found."
        )

    # ---------------------------------------------
    # If the source is being activated, verify
    # robots.txt before allowing it.
    # ---------------------------------------------
    if source_data.is_active is True:

        robots_allowed, robots_status = check_robots_txt(
            source.base_url
        )

        # Store the latest robots.txt result
        source.robots_txt_allowed = robots_allowed
        source.robots_txt_status = robots_status

        # Do not allow activation if crawling
        # is disallowed.
        if not robots_allowed:
            source.is_active = False

            db.commit()
            db.refresh(source)

            raise HTTPException(
                status_code=403,
                detail=(
                    "Source cannot be activated because "
                    f"robots.txt status is '{robots_status}'."
                )
            )

    # ---------------------------------------------
    # Apply the requested update
    # ---------------------------------------------
    source = crud.update_source(
        db,
        source,
        source_data
    )

    return source


# --------------------------------------------------
# PUT /sources/{source_id}/pause
# Pause source
# --------------------------------------------------

@router.put(
    "/{source_id}/pause",
    response_model=SourceResponse
)
def pause_source(
    source_id: int,
    db: Session = Depends(get_db)
):
    source = crud.get_source(
        db,
        source_id
    )

    if not source:
        raise HTTPException(
            status_code=404,
            detail="Source not found."
        )

    return crud.pause_source(
        db,
        source
    )


# --------------------------------------------------
# PUT /sources/{source_id}/resume
# Resume source
# --------------------------------------------------

@router.put(
    "/{source_id}/resume",
    response_model=SourceResponse
)
def resume_source(
    source_id: int,
    db: Session = Depends(get_db)
):
    source = crud.get_source(
        db,
        source_id
    )

    if not source:
        raise HTTPException(
            status_code=404,
            detail="Source not found."
        )

    # Check the current robots.txt policy
    robots_allowed, robots_status = check_robots_txt(
        source.base_url
    )

    # Always store the latest result
    source.robots_txt_allowed = robots_allowed
    source.robots_txt_status = robots_status

    # Do not resume if crawling is not allowed
    if not robots_allowed:
        source.is_active = False

        db.commit()
        db.refresh(source)

        raise HTTPException(
            status_code=403,
            detail=( 
                "Source cannot be resumed because "
                f"robots.txt status is '{robots_status}'."
            )
        )

    source.is_active = True

    db.commit()
    db.refresh(source)

    return source


# --------------------------------------------------
# PATCH /sources/{source_id}/crawl
# Update last crawled timestamp
# --------------------------------------------------

@router.patch(
    "/{source_id}/crawl",
    response_model=SourceResponse
)
def update_crawl_time(
    source_id: int,
    db: Session = Depends(get_db)
):
    source = crud.get_source(
        db,
        source_id
    )

    if not source:
        raise HTTPException(
            status_code=404,
            detail="Source not found."
        )

    return crud.update_last_crawled(
        db,
        source
    )


# --------------------------------------------------
# DELETE /sources/{source_id}
# Delete source
# --------------------------------------------------

@router.delete(
    "/{source_id}",
    status_code=204
)
def delete_source(
    source_id: int,
    db: Session = Depends(get_db)
):
    source = crud.get_source(
        db,
        source_id
    )

    if not source:
        raise HTTPException(
            status_code=404,
            detail="Source not found."
        )

    crud.delete_source(
        db,
        source
    )

    return None