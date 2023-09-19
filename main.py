from enum import Enum
from typing import Dict, List, Optional
from urllib.parse import urlparse, parse_qs

import bs4
import requests
from bs4 import NavigableString
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, Field

app = FastAPI()

BASE_URL = "https://qis.verwaltung.uni-hannover.de"
SERVICE_BASE_URL = f"{BASE_URL}/qisserver/servlet/de.his.servlet.RequestDispatcherServlet"
SIGNIN_URL = f"{SERVICE_BASE_URL}?state=user&type=1&category=auth.login&startpage=portal.vm&breadCrumbSource=portal"
STUDY_POS_URL = (f"{SERVICE_BASE_URL}?state=change&type=1&moduleParameter=studyPOSMenu&nextdir=change&next=menu.vm"
                 f"&subdir=applications&xml=menu&purge=y&navigationPosition=functions%2CstudyPOSMenu&breadcrumb"
                 f"=studyPOSMenu&topitem=functions")
DEFAULT_REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/116.0.0.0 Safari/537.36"}

# Constants for magic numbers/strings
USER_DISPLAY_NAME_INDEX = 8


class ErrorResponse(BaseModel):
    detail: str


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
    asi: str


def parse_asi_parameter(response_text: str) -> str or None:
    """
    Parses the ASI parameter from the HTML response.
    :param response_text: HTML response from the QIS server.
    :return: ASI parameter or None if it could not be parsed.
    """
    soup = bs4.BeautifulSoup(response_text, "html.parser")

    # get the button for the scorecard page to get the ASI parameter
    if button := soup.find("a", text="Notenspiegel / Studienverlauf"):
        return button.attrs['href'].split("asi=")[1]
    return None


@app.post("/signin", response_model=UserSignInDetails,
          responses={200: {"description": "Successfully signed in", "model": UserSignInDetails},
                     401: {"description": "Invalid credentials", "model": ErrorResponse},
                     500: {"description": "Internal server error", "model": ErrorResponse},
                     503: {"description": "Service temporarily unavailable", "model": ErrorResponse}})
async def signin(user_credentials: UserCredentials):
    """
    Reads the user's credentials, forwards them to the qis server und returns the session cookie for the user.
    :return: Session cookie
    """
    qis_session = requests.Session()
    # The "asdf" and "fdsa" keys are the names of the input fields for the username and password.
    # The QIS server uses the framework "Struts", which requires the input fields to be named like this.
    qis_request_body = {"asdf": user_credentials.username, "fdsa": user_credentials.password, "submit": "Login"}

    # Error handling for network issues.
    try:
        # Added a timeout for the request.
        response = qis_session.post(SIGNIN_URL, data=qis_request_body, headers=DEFAULT_REQUEST_HEADERS, timeout=10)
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable") from e

    # Check the response's HTTP status code.
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Unexpected response from QIS server")

    # Check if the user's credentials are valid by checking if the password input field is still present.
    if "Passwort" in response.text:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    session_cookies_dict = qis_session.cookies.get_dict()

    # Check if the key "JSESSIONID" is in the session cookies dictionary.
    if "JSESSIONID" not in session_cookies_dict:
        raise HTTPException(status_code=500, detail="Internal server error")

    # Requesting the study POS page with the obtained session cookie to gain the ASI parameter.
    try:
        response = qis_session.get(STUDY_POS_URL, headers=DEFAULT_REQUEST_HEADERS, timeout=10)
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable") from e

    # Check if the response's HTTP status code is 200.
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Unexpected response from QIS server")

    # Parse the ASI parameter from the HTML response.
    asi_parameter = parse_asi_parameter(response.text)

    # Check if the ASI parameter is valid.
    if asi_parameter is None:
        raise HTTPException(status_code=500, detail="Internal server error")

    # get the user's display name from the HTML response.
    user_display_name = parse_user_display_name(response.text)

    # Return the session cookie and the user's display name.
    return {"message": "Successfully signed in", "user_display_name": user_display_name,
            "session_cookie": session_cookies_dict["JSESSIONID"], "asi": asi_parameter}


# Separate function for parsing user display name from the HTML response.
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
        user_display_name = str(div_login_status.contents[USER_DISPLAY_NAME_INDEX]).strip()
        return " ".join(user_display_name.split())
    return ""


class SessionStatus(BaseModel):
    """
    Model to represent the validity of a session.
    """
    is_valid: bool
    message: str


@app.get("/check_session", response_model=SessionStatus,
         responses={200: {"description": "Session status returned", "model": SessionStatus},
                    400: {"description": "Bad request, possibly due to missing or invalid parameters",
                          "model": ErrorResponse},
                    503: {"description": "Service temporarily unavailable", "model": ErrorResponse}})
async def check_session_validity(session_cookie: str = Header(...)):  # The session cookie is passed as a header.
    """
    Checks if a session cookie is still valid.
    :param session_cookie: The data containing the JSESSIONID cookie.
    :return: A model indicating if the session is valid or not.
    """
    try:
        # Requesting the login page
        is_valid = _session_is_valid(session_cookie)
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable") from e

    # If the 'Passwort' field is present, the session is invalid. Otherwise, it's still valid.
    if not is_valid:
        return {"is_valid": False, "message": "Session is invalid"}
    else:
        return {"is_valid": True, "message": "Session is valid"}


def _session_is_valid(session_cookie: str) -> bool:
    """
    Checks if a session cookie is still valid.
    :param session_cookie: The data containing the JSESSIONID cookie.
    :return: True if the session is valid, False otherwise.
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
    return "Passwort" not in response.text


class ScorecardIDs(BaseModel):
    """
    Modell zur Darstellung der Scorecard-IDs.
    """
    scorecard_ids: Dict[str, str] = Field(..., example={
        "Informatik  (PO-Version 2017)": "auswahlBaum|abschluss:abschl=82|studiengang:stg=079,pversion=2017,kzfa=H",
        "Informatik  (PO-Version 2004)": "auswahlBaum|abschluss:abschl=82|studiengang:stg=079,pversion=2004,kzfa=H"},
                                          description="A dictionary containing the scorecard IDs")
    message: str = Field(..., example="Successfully retrieved scorecard IDs",
                         description="A message indicating if the request was successful or not")


def parse_scorecard_ids(html_text: str) -> Dict[str, str]:
    """
    Parses the scorecard IDs from the HTML response.
    :param html_text: HTML response from the QIS server.
    :return: Scorecard IDs.
    """
    soup = bs4.BeautifulSoup(html_text, "html.parser")
    scorecard_ids = {}

    for a_tag in soup.find_all("a", {"title": lambda x: x and x.startswith("Leistungen")}):
        # Split the url into its components
        parsed_url = urlparse(a_tag.attrs["href"])

        # extract the parameters from the url
        query_params = parse_qs(parsed_url.query)

        # Get the parent node of the a tag
        parent_node = a_tag.parent

        # check if the "nodeID" parameter is present
        if "nodeID" in query_params:
            scorecard_ids[parent_node.text.strip()] = query_params["nodeID"][0]

    return scorecard_ids


@app.get("/scorecard_ids", response_model=ScorecardIDs,
         responses={200: {"description": "Scorecard IDs returned", "model": ScorecardIDs},
                    400: {"description": "Bad request, possibly due to missing or invalid parameters",
                          "model": ErrorResponse}, 401: {"description": "Invalid credentials", "model": ErrorResponse},
                    500: {"description": "Internal server error", "model": ErrorResponse},
                    503: {"description": "Service temporarily unavailable", "model": ErrorResponse}})
async def get_scorecard_ids(session_cookie: str = Header(..., description="The data containing the JSESSIONID cookie.",
                                                         example="ETHEWEBNTZRH45iEGFORTNB839FHCB93.uhvqis1"),
                            asi: str = Header(..., description="The ASI parameter.",
                                              example="tnEJEgEd8dAPRC.kaurx")) -> ScorecardIDs:
    """
    Gets the scorecard IDs for the user.
    """
    # Check if the session is still valid
    try:
        session_is_valid = _session_is_valid(session_cookie)
        if not session_is_valid:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable") from e

    # Creating a new session to use the provided session cookie
    qis_session = requests.Session()
    qis_session.cookies.set("JSESSIONID", session_cookie)

    try:
        # Requesting the scorecard page
        response = qis_session.get(f"{SERVICE_BASE_URL}?state=notenspiegelStudent&"
                                   f"struct=auswahlBaum&navigation=Y&next=tree.vm&"
                                   f"nextdir=qispos/notenspiegel/student&nodeID=auswahlBaum%7Cabschluss:abschl%3D82"
                                   f"&expand=0&lastState=notenspiegelStudent"
                                   f"&asi={asi}", timeout=10)
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable") from e

    # Check if the response's HTTP status code is 200.
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Unexpected response from QIS server")

    # Parse the scorecard IDs from the HTML response.
    scorecard_ids = parse_scorecard_ids(response.text)

    # Check if the scorecard IDs are valid.
    if len(scorecard_ids) == 0:
        raise HTTPException(status_code=500, detail="Internal server error")

    # Return the scorecard IDs.
    return {"scorecard_ids": scorecard_ids, "message": "Successfully retrieved scorecard IDs"}


class ScoreType(str, Enum):
    """
    Enum to represent the type of score.
    """
    PL = "PL"
    SL = "SL"


class ScoreState(str, Enum):
    """
    Enum to represent the state of a score.
    """
    PASSED = "bestanden"
    FAILED = "nicht bestanden"
    REGISTERED = "angemeldet"


class IndividualScore(BaseModel):
    """
    Model to represent a score.
    """
    number: int = Field(..., example=110, description="The number of the score")
    name: str = Field(..., example="Grundlagen der Informatik", description="The name of the score")
    score_type: ScoreType = Field(..., example="Prüfungsleitung", description="The type of the score")
    semester: str = Field(..., example="WS 2017/18", description="The semester of the score")
    grade: Optional[float] = Field(None, example=1.3, description="The grade of the score")
    state: ScoreState = Field(..., example="bestanden", description="The state of the score")
    date: str = Field(..., example="01.02.2018", description="The date of the score")
    try_number: Optional[int] = Field(None, example=1, description="The number of tries")


class BaseScore(BaseModel):
    """
    Model to represent a score.
    """
    number: int = Field(..., example=100, description="The number of the score")
    name: str = Field(..., example="Grundlagen der Informatik", description="The name of the score")
    semester: str = Field(..., example="WS 2017/18", description="The semester of the score")
    state: ScoreState = Field(..., example="bestanden", description="The state of the score")
    score_credits: int = Field(..., example=10, description="The credits of the score")
    date: str = Field(..., example="01.02.2018", description="The date of the score")
    individual_scores: List[IndividualScore] = Field(..., example=[{
        "number": 110,
        "name": "Grundlagen der Informatik",
        "score_type": "Prüfungsleitung",
        "semester": "WS 2017/18",
        "grade": 1.3,
        "state": "bestanden",
        "date": "01.02.2018",
        "try_number": 1
    }, {
        "number": 1109,
        "name": "Grundlagen der Informatik",
        "score_type": "Studienleistung",
        "semester": "WS 2017/18",
        "grade": None,
        "state": "bestanden",
        "date": "01.02.2018",
        "try_number": 1
    }], description="A list of individual scores")


class Scorecard(BaseModel):
    """
    Model to represent a scorecard.
    """
    scores: list[BaseScore]
    message: str = Field(..., example="Successfully retrieved scorecard",
                         description="A message indicating if the request was successful or not")


def parse_base_score_row(cells) -> BaseScore:
    """
    Parses the base score from the HTML response.
    :param cells: Cells of the row.
    :return: Base score.
    """
    number: int = int(cells[0].text.strip())
    name: str = cells[1].text.strip()
    semester: str = cells[3].text.strip()
    state: ScoreState = ScoreState(cells[5].text.strip())
    score_credits: int = int(cells[6].text.strip())
    date: str = cells[7].text.strip()

    return BaseScore(
        number=number,
        name=name,
        semester=semester,
        state=state,
        score_credits=score_credits,
        date=date,
        individual_scores=[],
    )


def parse_individual_score_row(cells) -> IndividualScore:
    """
    Parses the individual score from the HTML response.
    :param cells: Cells of the row.
    :return: Individual score.
    """

    number: int = int(cells[0].text.strip())
    name: str = cells[1].text.strip()
    score_type: ScoreType = ScoreType(cells[2].text.strip())
    semester: str = cells[3].text.strip()

    if cells[4].text.strip():
        grade: Optional[float] = float(cells[4].text.strip().replace(",", "."))
    else:
        grade: Optional[float] = None

    state: ScoreState = ScoreState(cells[5].text.strip())
    date: str = cells[7].text.strip()

    if cells[8].text.strip():
        try_number: Optional[int] = int(cells[8].text.strip())
    else:
        try_number: Optional[int] = None

    return IndividualScore(
        number=number,
        name=name,
        score_type=score_type,
        semester=semester,
        grade=grade,
        state=state,
        date=date,
        try_number=try_number,
    )


def parse_scorecard(html_text: str) -> List[BaseScore] or None:
    """
    Parses the scorecard from the HTML response.
    :param html_text: HTML response from the QIS server.
    :return: Scorecard.
    """
    soup = bs4.BeautifulSoup(html_text, "html.parser")

    # find the table with the scores
    table = soup.findAll("table")[1]

    # get the rows of the table
    rows = table.findAll("tr")

    # remove the first row, because it contains the table headers
    rows.pop(0)

    # create a list to store the scores
    scores = []

    latest_base_score = None

    # iterate over the rows
    for row in rows:
        # get the cells of the row
        cells = row.findAll("td")

        # check if the row has the expected structure
        if len(cells) != 11:
            continue

        if not cells[6].text.strip():
            continue

        # get the score's type
        if not cells[2].text.strip():
            latest_base_score = parse_base_score_row(cells)
            scores.append(latest_base_score)
        elif latest_base_score is not None:
            if len(row.contents) < 4:
                continue
            latest_base_score.individual_scores.append(parse_individual_score_row(cells))

    return scores

@app.get("/scorecard", response_model=Scorecard,
         responses={200: {"description": "Scorecard returned", "model": Scorecard},
                    400: {"description": "Bad request, possibly due to missing or invalid parameters",
                          "model": ErrorResponse},
                    401: {"description": "Invalid credentials", "model": ErrorResponse},
                    500: {"description": "Internal server error", "model": ErrorResponse},
                    503: {"description": "Service temporarily unavailable", "model": ErrorResponse}})
async def get_scorecard(scorecard_id: str,
                        session_cookie: str = Header(...,
                                                     description="The data containing the JSESSIONID cookie.",
                                                     example="ETHEWEBNTZRH45iEGFORTNB839FHCB93.uhvqis1"),
                        asi: str = Header(...,
                                          description="The ASI parameter.",
                                          example="tnEJEgEd8dAPRC.kaurx")
                        ) -> ScorecardIDs:
    """
    Gets the scorecard for the user.
    """
    # Check if the session is still valid
    try:
        session_is_valid = _session_is_valid(session_cookie)
        if not session_is_valid:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable") from e

    # Creating a new session to use the provided session cookie
    qis_session = requests.Session()
    qis_session.cookies.set("JSESSIONID", session_cookie)

    url = (f"{SERVICE_BASE_URL}?state=notenspiegelStudent&menu_open=n&next=list.vm&nextdir=qispos/notenspiegel/student"
           f"&createInfos=Y&struct=auswahlBaum&nodeID={scorecard_id}&expand=0&asi={asi}")

    try:
        # Requesting the scorecard page
        response = qis_session.get(url, timeout=10)
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable") from e

    # Check if the response's HTTP status code is 200.
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Unexpected response from QIS server")

    # Parse the scorecard from the HTML response.
    scorecard = parse_scorecard(response.text)

    # Check if the scorecard is valid.
    if scorecard is None:
        raise HTTPException(status_code=500, detail="Internal server error")

    # Return the scorecard.
    return {"scores": scorecard, "message": "Successfully retrieved scorecard"}
