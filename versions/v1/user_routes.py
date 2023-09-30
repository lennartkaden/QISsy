import requests
from fastapi import APIRouter
from fastapi import HTTPException, Header

from .models import ErrorResponse, UserCredentials, UserSignInDetails, SessionStatus, ScorecardIDs, Scorecard
from .utils import SERVICE_BASE_URL, parse_asi_parameter, parse_user_display_name, _session_is_valid, \
    parse_scorecard_ids, parse_scorecard, validate_session_or_raise

router = APIRouter()

SIGNIN_URL = f"{SERVICE_BASE_URL}?state=user&type=1&category=auth.login&startpage=portal.vm&breadCrumbSource=portal"
STUDY_POS_URL = (f"{SERVICE_BASE_URL}?state=change&type=1&moduleParameter=studyPOSMenu&nextdir=change&next=menu.vm"
                 f"&subdir=applications&xml=menu&purge=y&navigationPosition=functions%2CstudyPOSMenu&breadcrumb"
                 f"=studyPOSMenu&topitem=functions")
DEFAULT_REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/116.0.0.0 Safari/537.36"}


# Constants for magic numbers/strings
@router.post("/signin", response_model=UserSignInDetails,
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


@router.get("/check_session", response_model=SessionStatus,
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


# noinspection DuplicatedCode
@router.get("/scorecard_ids", response_model=ScorecardIDs,
            responses={200: {"description": "Scorecard IDs returned", "model": ScorecardIDs},
                       400: {"description": "Bad request, possibly due to missing or invalid parameters",
                             "model": ErrorResponse},
                       401: {"description": "Invalid credentials", "model": ErrorResponse},
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
    await validate_session_or_raise(session_cookie)

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
    return ScorecardIDs(scorecard_ids=scorecard_ids, message="Successfully retrieved scorecard IDs")


# noinspection DuplicatedCode
@router.get("/scorecard", response_model=Scorecard,
            responses={200: {"description": "Scorecard returned", "model": Scorecard},
                       400: {"description": "Bad request, possibly due to missing or invalid parameters",
                             "model": ErrorResponse},
                       401: {"description": "Invalid credentials", "model": ErrorResponse},
                       500: {"description": "Internal server error", "model": ErrorResponse},
                       503: {"description": "Service temporarily unavailable", "model": ErrorResponse}})
async def get_scorecard(scorecard_id: str,
                        session_cookie: str = Header(..., description="The data containing the JSESSIONID cookie.",
                                                     example="ETHEWEBNTZRH45iEGFORTNB839FHCB93.uhvqis1"),
                        asi: str = Header(..., description="The ASI parameter.",
                                          example="tnEJEgEd8dAPRC.kaurx")) -> Scorecard:
    """
    Gets the scorecard for the user.
    """
    # Check if the session is still valid
    await validate_session_or_raise(session_cookie)

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
    return Scorecard(scores=scorecard, message="Successfully retrieved scorecard")
