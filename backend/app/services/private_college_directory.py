"""Read the existing private import only after the route has authorized an admin."""
from fastapi import HTTPException
from sqlalchemy import MetaData, Table, func, select
from sqlalchemy.exc import NoSuchTableError


def private_college_page(db, *, q=None, state=None, district=None, page=1, page_size=100):
    connection = db.connection()
    try:
        table = Table('colleges', MetaData(), schema='aishe_staging',
                      autoload_with=connection, resolve_fks=False)
    except NoSuchTableError:
        raise HTTPException(503, 'Private college directory is not configured') from None
    required = {'identifier', 'name', 'state', 'permission_status'}
    if not required.issubset(table.c.keys()):
        raise HTTPException(503, 'Private directory column mapping requires verification')
    filters = []
    if q:
        filters.append(table.c.name.icontains(q, autoescape=True))
    for field, value in (('state', state), ('district', district)):
        if value:
            if field not in table.c:
                return dict(data=[], total=0, page=page, page_size=page_size)
            filters.append(func.lower(table.c[field]) == value.lower())
    # No views, stored functions, privilege changes or writes. Never falls back to a public table.
    fields = [field for field in ('id', 'identifier', 'name', 'state', 'district', 'city',
              'category', 'website', 'provenance', 'last_verified_at', 'permission_status') if field in table.c]
    rows = db.execute(select(*(table.c[field] for field in fields)).where(*filters)
        .order_by(table.c.name, table.c.identifier).offset((page - 1) * page_size).limit(page_size)).mappings().all()
    data = []
    for row in rows:
        item = dict(row)
        item.setdefault('id', item['identifier'])
        data.append(item)
    return dict(data=data, total=db.scalar(select(func.count()).select_from(table).where(*filters)),
                page=page, page_size=page_size)
