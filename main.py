from typing import Dict

import bs4
import requests
from bs4 import NavigableString
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel

app = FastAPI()

BASE_URL = "https://qis.verwaltung.uni-hannover.de"
SERVICE_BASE_URL = f"{BASE_URL}/qisserver/servlet/de.his.servlet.RequestDispatcherServlet"
SIGNIN_URL = f"{SERVICE_BASE_URL}?state=user&type=1&category=auth.login&startpage=portal.vm&breadCrumbSource=portal"

# Constants for magic numbers/strings
USER_DISPLAY_NAME_INDEX = 8


class UserCredentials(BaseModel):
    """
    Model for the user's credentials.
    """
    username: str
    password: str


class UserSignInDetails(BaseModel):
    """
    Model for the user's sign in details.
    """
    message: str
    user_display_name: str
    session_cookie: str


@app.post("/signin", response_model=UserSignInDetails,
          responses={200: {"description": "Successfully signed in", "model": UserSignInDetails},
                     401: {"description": "Invalid credentials"}, 500: {"description": "Internal server error"},
                     503: {"description": "Service temporarily unavailable"}})
async def signin(user_credentials: UserCredentials):
    """
    Reads the user's credentials, forwards them to the qis server und returns the session cookie for the user.
    :return: Session cookie
    """
    qis_session = requests.Session()
    # The "asdf" and "fdsa" keys are the names of the input fields for the username and password.
    # The QIS server uses the framework "Struts", which requires the input fields to be named like this.
    qis_request_body = {"asdf": user_credentials.username, "fdsa": user_credentials.password, "submit": "Login"}

    # 2. Error handling for network issues.
    try:
        # 1. Added a timeout for the request.
        response = qis_session.post(SIGNIN_URL, data=qis_request_body, timeout=10)
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable") from e

    # Check the response's HTTP status code.
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Unexpected response from QIS server")

    session_cookies_dict = qis_session.cookies.get_dict()

    # Check if the user's credentials are valid by checking if the password input field is still present.
    if "Passwort" in response.text:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Check if the key "JSESSIONID" is in the session cookies dictionary.
    if "JSESSIONID" not in session_cookies_dict:
        raise HTTPException(status_code=500, detail="Internal server error")

    # get the user's display name from the HTML response.
    user_display_name = parse_user_display_name(response.text)

    # Return the session cookie and the user's display name.
    return {"message": "Successfully signed in", "user_display_name": user_display_name,
            "session_cookie": session_cookies_dict["JSESSIONID"]}


# 8. Separate function for parsing user display name from the HTML response.
def parse_user_display_name(html_text: str) -> str:
    """
    Parses the user's display name from the HTML response.
    :param html_text: HTML response from the QIS server.
    :return: User's display name.
    """
    soup = bs4.BeautifulSoup(html_text, "html.parser")
    div_login_status = soup.find("div", {"class": "divloginstatus"})

    # Check if the div is not None and has the expected structure.
    if div_login_status and len(div_login_status.contents) > USER_DISPLAY_NAME_INDEX and type(
            div_login_status.contents[USER_DISPLAY_NAME_INDEX]) is NavigableString:
        user_display_name = div_login_status.contents[USER_DISPLAY_NAME_INDEX].strip()
        return " ".join(user_display_name.split())
    return ""


class SessionCheckInput(BaseModel):
    """
    Model to accept the session cookie.
    """
    session_cookie: str


class SessionStatus(BaseModel):
    """
    Model to represent the validity of a session.
    """
    is_valid: bool
    message: str


@app.get("/check_session", response_model=SessionStatus,
         responses={200: {"description": "Session status returned", "model": SessionStatus},
                    400: {"description": "Bad request, possibly due to missing or invalid parameters"},
                    503: {"description": "Service temporarily unavailable"}})
async def check_session_validity(session_cookie: str = Header(...)):  # Der Session-Key wird vom Header genommen
    """
    Checks if a session cookie is still valid.
    :param session_cookie: The data containing the JSESSIONID cookie.
    :return: A model indicating if the session is valid or not.
    """
    # Creating a new session to use the provided session cookie
    qis_session = requests.Session()
    qis_session.cookies.set("JSESSIONID", session_cookie)

    try:
        # Requesting the login page
        response = qis_session.get(f"{SERVICE_BASE_URL}?state=user&type=0&application=lsf", timeout=10)
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable") from e

    # If the 'Passwort' field is present, the session is invalid. Otherwise, it's still valid.
    if "Passwort" in response.text:
        return {"is_valid": False, "message": "Session is invalid"}
    else:
        return {"is_valid": True, "message": "Session is valid"}
