# Proposed Architecture Improvements

This document outlines suggestions for a future restructuring of QISsy. The aim is to make the code base easier to maintain as more API versions and functionality are added.

## 1. Clear application root

Create an `app/` directory that contains all application code. Only configuration files, documentation and tests remain in the project root.

```
QISsy/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── routes.py
│   │   │   ├── models.py
│   │   │   └── utils.py
│   │   └── v2/   # future versions
│   ├── core/
│   │   ├── config.py
│   │   └── logging.py
│   ├── services/
│   │   └── ...    # business logic separated from the routes
│   └── main.py
├── tests/
└── ...
```

This structure separates the FastAPI layers (routes/models), shared services and infrastructure code (logging, configuration). It also allows additional versions to be introduced in parallel under `app/api`.

## 2. API versioning

Continue using `VersionedFastAPI`, but place the versioned routers inside `app/api/<version>/`. Each version should provide a `router` object that is included by `main.py`.

```
from fastapi_versioning import VersionedFastAPI
from app.api.v1.routes import router as v1_router

base_app = FastAPI()
base_app.include_router(v1_router)
app = VersionedFastAPI(base_app, prefix_format="/v{major}.{minor}")
```

When a breaking change is required, a new folder (e.g. `v2`) can be created and the old code kept intact.

## 3. Configuration handling

Move configuration helpers into `app/core/config.py`. Use environment variables or a `.env` file in combination with Pydantic settings for better validation and easier defaults.

## 4. Service layer

Encapsulate scraping and data processing logic in `app/services/` modules. The API routes then become thin wrappers that call these services. This improves testability and keeps the routers small.

## 5. Tests

Keep all tests under `tests/` but mirror the directory layout of the `app/` folder if it grows. Each version should have its own tests, e.g. `tests/api/v1/test_routes.py`.

Implementing these steps would simplify further development and help to maintain multiple API versions without cluttering the root directory.
