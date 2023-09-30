import contextlib
from typing import Dict, Optional, List
from urllib.parse import urlparse, parse_qs

import bs4
import requests
from bs4 import NavigableString
from fastapi import HTTPException

from .models import BaseScore, ScoreStatus, IndividualScore, ScoreType

BASE_URL = "https://qis.verwaltung.uni-hannover.de"
SERVICE_BASE_URL = f"{BASE_URL}/qisserver/servlet/de.his.servlet.RequestDispatcherServlet"
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
    status: ScoreStatus = ScoreStatus(cells[5].text.strip())
    score_credits: int = int(cells[6].text.strip())
    issued_on: str = cells[7].text.strip()

    return BaseScore(id=score_id, title=title, semester=semester, status=status, credits=score_credits,
        issued_on=issued_on, individual_scores=[], )


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
