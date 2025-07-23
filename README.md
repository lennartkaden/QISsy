# QISsy API Documentation

[![Deployment to testserver](https://github.com/lennartkaden/QISsy/actions/workflows/deploy.yml/badge.svg?branch=master)](https://github.com/lennartkaden/QISsy/actions/workflows/deploy.yml)

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

## Usage

This API comes with a set of versioned endpoints that serve different functionalities. The current version is `v1.0`.

### Endpoints summary:

- GET `/info` - Provides information about the running QISsy instance.

- POST `/v1.0/signin` - Authenticates the user using provided credentials.
- GET `/v1.0/check_session` - Checks whether an existing session is valid.
- GET `/v1.0/scorecard_ids` - Retrieves the identifiers of available scorecards for the user.
- GET `/v1.0/scorecard` - Fetches a particular scorecard using its identifier.

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