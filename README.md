# QISsy API Documentation

| :exclamation:  QISsy is still a dev preview! |
|----------------------------------------------|
The functionality of this API is still limited and may not work as expected. Please report any issues you encounter. The scraping process is very trivial and may break at any time due to changes in the QIS system or due to unexpected input.

## Disclaimer

This project is not affiliated with any University or the QIS Product by the HIS eG. It is a private project that
aims to provide a convenient way to access educational records for students of Universities that use the QIS system.
As such, it is not guaranteed to work with all QIS servers and may break at any time due to changes in the QIS system.

Due to the QIS system's lack of an official API, this project relies on web scraping to retrieve data from the QIS
server. This means that the API may break at any time due to changes in the QIS system. This also means that the API
can only rely on the authentication mechanism provided by the QIS system, which is currently a simple username/password
combination. The API is just passing the Users credentials to the QIS server, which is not a secure authentication 
method and should not be used in production environments without further security measures.

## Overview

QISsy is a FastAPI application designed to facilitate the interaction with the QIS server of a University.
It provides a set of endpoints that allow clients to authenticate and access their educational records such as
scorecards and grades in an efficient and user-friendly way.

### Features

- User Authentication
- Optional API key protection for private deployments (HMAC-derived keys with blacklist support)
- Session Validity Checks
- Retrieval of Scorecard Identifiers
- Retrieval of Full Scorecards including detailed grades, grade point average and credit point sum

### Technical Environment

 - FastAPI framework for building APIs with Python 3.9+ based on Pydantic and type hints.
- fastapi-versioning to manage version control within FastAPI endpoints.
- Beautiful Soup for parsing HTML responses.
- Requests library to handle HTTP requests.

## Installation

### Prerequisites

Before you can run QISsy, ensure you have the following installed:
- Python 3.9 or higher
- pip (Python package installer)

### Setup a Virtual Environment (Recommended)

It's a best practice to create a virtual environment for your Python project. This ensures that the dependencies for one
project do not interfere with the dependencies of another project.

```sh
# Navigate to your project directory
cd path/to/your/qissy

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate  # On Linux or macOS
.\venv\Scripts\activate  # On Windows

# Your prompt should change to indicate that you are now operating within the virtual environment
```

### Installation Steps

1. Clone the repository to your local machine.

```sh
git clone https://github.com/lennartkaden/QISsy.git
cd QISsy
```

2. Install required dependencies.

```sh
pip install -r requirements.txt
```

3. Copy the example config to a new file and fill in your QIS server URL.

```sh
cp config_example.json config.json
```

If `config.json` is missing at runtime, QISsy will try to read the values from
environment variables. Set `QIS_BASE_URL` and `QIS_SERVICE_PATH` to the
appropriate values when running without a configuration file.

### Running the APP

To run the QISsy FastAPI app, execute:

```sh
uvicorn main:app --reload
```

After running this command, visit the URL `http://127.0.0.1:8000/v1.0/docs` on your web browser. 
You should see the automatic interactive API documentation provided by FastAPI, which you can use to test the API 
endpoints.

## API Key Protection

QISsy can require an API key on all versioned endpoints (`/v1.0/...`). This is
meant for small private deployments: the operator hands each friend an
individual key. Without a valid key, QISsy rejects the request **before** any
request is sent to the QIS server, so the signin endpoint cannot be abused to
spam the university's QIS.

Keys are stateless: each key is derived from the operator's secret via
HMAC-SHA256 and validated on the fly. Nothing is stored on the server.

### Setup

1. Generate a secret and put it into `config.json`:

   ```sh
   python generate_api_key.py --new-secret
   ```

   ```json
   "API": {
     "SECRET_KEY": "<the generated secret>",
     "KEY_PROTECTION_ENABLED": true,
     "KEY_BLACKLIST": []
   }
   ```

2. Generate a key for each friend and share it with them:

   ```sh
   python generate_api_key.py alice
   # qissy_alice_3f9d2c…
   ```

3. Clients send the key in the `X-API-Key` header on every request.

Apps can check the public `/info` endpoint first: its `api_key_required`
field tells them whether this instance expects an API key, so they can
prompt the user for one before signing in.

Protection is **enabled by default**. To run QISsy without API keys, set
`KEY_PROTECTION_ENABLED` to `false`. If protection is enabled but no
`SECRET_KEY` is configured, QISsy fails closed and rejects all requests
with `503`.

### Revoking access

- **Revoke one key:** add its name to `KEY_BLACKLIST`, e.g. `["alice"]`.
  The change takes effect immediately (the config is re-read per request);
  blacklisted keys receive `403`.
- **Revoke all keys:** replace `SECRET_KEY` with a new secret. All previously
  issued keys become invalid instantly and receive `401`.

Environment variable fallbacks (used when `config.json` is missing or lacks
the key): `API_SECRET_KEY`, `API_KEY_PROTECTION_ENABLED`,
`API_KEY_BLACKLIST` (comma separated, e.g. `alice,bob`).

## Usage

This API comes with a set of versioned endpoints that serve different functionalities. The current version is `v1.0`.

### Endpoints summary:

- GET `/info` - Provides information about the running QISsy instance,
  including `api_key_required`, which tells clients whether the versioned
  endpoints expect an `X-API-Key` header.
- GET `/robots.txt` - Disallows all web crawlers.

- POST `/v1.0/signin` - Authenticates the user using provided credentials.
- GET `/v1.0/check_session` - Checks whether an existing session is valid.
- GET `/v1.0/scorecard_ids` - Retrieves the identifiers of available scorecards for the user.
- GET `/v1.0/scorecard` - Fetches a particular scorecard using its identifier.

  The response contains the current grade point average, the total credit
  sum and a timeline of how the grade point average evolved over time.

All `/v1.0/...` endpoints require the `X-API-Key` header when API key
protection is enabled (the default). `/info` and `/robots.txt` are always
public.

Each endpoint requires specific input parameters and returns respective responses which are documented in detail using 
Pydantic models and can be viewed on the Swagger/OpenAPI documentation available at `http://127.0.0.1:8000/v1.0/redoc`
once the server is running.

## Development

The source code is structured as follows:

- `main.py` - Contains the FastAPI application instantiation and setup.
- `versions/v1/` - Contains all the versioned API routes, utility functions, and Pydantic models for data validation.

To contribute to the project, follow these steps:

1. Create a fork of the repository.
2. Clone the fork to your local machine.
3. Create a new branch for your feature.
4. Make your changes and commit them.
5. Push your changes to your fork.
6. Create a pull request.
7. Wait for the pull request to be reviewed and merged.

Please maintain the code quality standards of the project and adhere to PEP8 style guidelines.

## License

Distributed under the MIT License. See `LICENSE` for more information.