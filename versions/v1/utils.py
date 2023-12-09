"""
This Python script defines various helper functions for the parent API router to interact with a QIS
server and parse its responses.

Key functionalities include:

- **ASI Parameter Parsing:** The parse_asi_parameter function extracts the ASI parameter from the HTML response.

- **Parse User Display Name:** This function extracts the user's display name from the HTML response.

- **Session Validity:** This function checks if the current user session is still valid on the QIS server.

- **Parse Scorecard IDs:** This function extracts the scorecard IDs from the HTML response from the QIS server.

- **Parse Base Score and Individual Score Rows:** These functions parse the details of the grades contained in a
  scorecard from the HTML response of a scorecard page and format them into the structured model
  (BaseScore or IndividualScore).

- **Parse Scorecard:** This function extracts an entire scorecard from an HTML response from the QIS server.
  It uses parse_base_score_row and parse_individual_score_row functions to parse the scorecard information.

- **Session Validation:** This function checks if the incoming session cookie is still valid on the QIS system. This is
  used before making any requests that require an authenticated session.

- **Grade Point Average Calculation:** This function parses the grades from the scorecard and calculates the grade
  point average.

Most functions in this script operate by sending HTTP requests to the QIS server or parsing the HTML responses from the
server using BeautifulSoup. Error handling is implemented to handle potential exceptions, providing meaningful
responses to the user.

**Environment:** Python 3.10 with packages: requests, beautifulsoup4, fastapi

**Classes, Methods, and Functions:**

- Function `parse_asi_parameter`: Parses the ASI parameter from the HTML response
- Function `parse_user_display_name`: Parses the user's display name from the HTML response
- Function `_session_is_valid`: Checks if the current user session is still valid
- Function `parse_scorecard_ids`: Parses the scorecard IDs from the HTML response
- Function `parse_base_score_row`: Parse single row of scores into BaseScore model
- Function `parse_individual_score_row`: Parse single row of scores into IndividualScore model
- Function `parse_scorecard`: Parses the whole scorecard from the HTML response
- Function `validate_session_or_raise`: Validate current session or raise http exception
- Function `get_grade_point_average`: Calculates the grade point average from a scorecard.
"""


import contextlib
from typing import Dict, Optional, List
from urllib.parse import urlparse, parse_qs

import bs4
import requests
from bs4 import NavigableString
from fastapi import HTTPException

from config import get_config_value
from .models import BaseScore, ScoreStatus, IndividualScore, ScoreType

BASE_URL = get_config_value("QIS/BASE_URL")
SERVICE_PATH = get_config_value("QIS/SERVICE_PATH")
SERVICE_BASE_URL = f"{BASE_URL}{SERVICE_PATH}"
USER_DISPLAY_NAME_INDEX = 8


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

        # Get the parent node of the 'a' tag
        parent_node = a_tag.parent

        # check if the "nodeID" parameter is present
        if "nodeID" in query_params:
            scorecard_ids[parent_node.text.strip()] = query_params["nodeID"][0]

    return scorecard_ids


def parse_base_score_row(cells) -> BaseScore:
    """
    Parses the base score from the HTML response.
    :param cells: Cells of the row.
    :return: Base score.
    """
    score_id: int = int(cells[0].text.strip())
    title: str = cells[1].text.strip()
    semester: str = cells[3].text.strip()
    grade: Optional[float] = None

    raw_score_status: str = cells[5].text.strip()
    if not raw_score_status:
        raw_score_status = "angemeldet"

    status: ScoreStatus = ScoreStatus(raw_score_status)
    score_credits: int or None = int(cells[6].text.strip()) if cells[6].text.strip() else None
    issued_on: str = cells[7].text.strip()

    return BaseScore(id=score_id, title=title, semester=semester, grade=grade, status=status, credits=score_credits,
                     issued_on=issued_on, individual_scores=[])


def parse_individual_score_row(cells) -> IndividualScore:
    """
    Parses the individual score from the HTML response.
    :param cells: Cells of the row.
    :return: Individual score.
    """

    score_id: int = int(cells[0].text.strip())
    title: str = cells[1].text.strip()
    score_type: ScoreType = ScoreType(cells[2].text.strip())
    semester: str = cells[3].text.strip()

    specific_scorecard_id: Optional[str] = None

    if cells[4].text.strip():
        grade: Optional[float] = float(cells[4].text.strip().replace(",", "."))

        with contextlib.suppress(Exception):
            specific_scorecard_url = cells[4].contents[1].attrs['href']

            # Split the url into its components
            parsed_url = urlparse(specific_scorecard_url)

            # extract the parameters from the url
            query_params = parse_qs(parsed_url.query)

            specific_scorecard_id: Optional[str] = query_params["nodeID"][0]

    else:
        grade: Optional[float] = None

    status: ScoreStatus = ScoreStatus(cells[5].text.strip())
    issued_on: str = cells[7].text.strip()

    if cells[8].text.strip():
        attempt: Optional[int] = int(cells[8].text.strip())
    else:
        attempt: Optional[int] = None

    return IndividualScore(id=score_id, title=title, type=score_type, semester=semester, grade=grade, status=status,
        issued_on=issued_on, attempt=attempt, specific_scorecard_id=specific_scorecard_id)


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
    skip_next_row = False

    # iterate over the rows
    for row in rows:
        # get the cells of the row
        cells = row.findAll("td")

        if skip_next_row:
            skip_next_row = False
            continue

        # check if the row has the expected structure
        if len(cells) != 11:
            # if the row has not 11 cells, it is not a score row, but a title row. This row is followed by another row,
            # which should be skipped
            skip_next_row = True
            continue

        if not cells[6].text.strip() and cells[7].text.strip():
            continue

        # get the score's type
        if not cells[2].text.strip():
            latest_base_score = parse_base_score_row(cells)
            scores.append(latest_base_score)
        elif latest_base_score is not None:
            if len(row.contents) < 4:
                continue
            latest_base_score.individual_scores.append(parse_individual_score_row(cells))

    for score in scores:
        # if exactly one individual score has a grade, set the grade of the base score to that grade
        amount_of_grades = 0
        for individual_score in score.individual_scores:
            if individual_score.grade is not None:
                amount_of_grades += 1
                score.grade = individual_score.grade

        if amount_of_grades != 1:
            score.grade = None

    return scores


async def validate_session_or_raise(session_cookie):
    """
    Checks if the session cookie is still valid.
    Raises an exception if it isn't
    :param session_cookie: the session cookie to validate
    :raises HTTPException with status code 401 if the cookie is invalid
    :raises HTTPException with status code 503 if another error occurred
    """
    try:
        session_is_valid = _session_is_valid(session_cookie)
        if not session_is_valid:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable") from e


def get_grade_point_average(scorecard: List[BaseScore]) -> float or None:
    """
    parse the grades from the scorecard by iterating over the individual scores,
    multiplying the grade with the credits from the base score and summing them up
    :param scorecard: the scorecard to parse
    :return: the grade point average
    """
    great_point_average: float = 0.0
    amount_of_credits: int = 0

    for score in scorecard:
        for individual_score in score.individual_scores:
            if individual_score.grade is not None:
                great_point_average += individual_score.grade * score.credits
                amount_of_credits += score.credits

    # divide the sum of the grades by the number of credits
    if amount_of_credits > 0:
        great_point_average /= amount_of_credits
    else:
        return None

    return round(great_point_average, 2)
