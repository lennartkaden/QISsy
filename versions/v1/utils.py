from typing import Dict, Optional, List
from urllib.parse import urlparse, parse_qs
from datetime import datetime

import bs4
import requests
from bs4 import NavigableString, BeautifulSoup, Comment
from fastapi import HTTPException

from logging_config import logger

from config import get_config_value
from .models import Module, ScoreStatus, Score, ScoreType, TableRow, RowType, GradePointAverageProgressItem

BASE_URL = get_config_value("QIS/BASE_URL")
SERVICE_PATH = get_config_value("QIS/SERVICE_PATH")
SERVICE_BASE_URL = f"{BASE_URL}{SERVICE_PATH}"
USER_DISPLAY_NAME_INDEX = 8


def parse_asi_parameter(response_text: str) -> Optional[str]:
    """Parse the ASI parameter from the HTML response.

    :param response_text: HTML response from the QIS server.
    :return: The ASI parameter if present, otherwise ``None``.
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

def _parse_float(value: str) -> Optional[float]:
    text = value.strip().replace("\xa0", "").replace("&nbsp;", "").replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None

def _parse_int(value: str) -> Optional[int]:
    text = value.strip().replace("\xa0", "").replace("&nbsp;", "")
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _parse_status(status: str) -> Optional[ScoreStatus]:
    """Convert a status string to :class:`ScoreStatus` if possible."""
    status = status.strip().replace("\xa0", "").replace("&nbsp;", "")
    if not status:
        return None
    try:
        return ScoreStatus(status)
    except ValueError:
        return None


def parse_scores(html_text: str) -> Dict[str, List[Module]]:
    table_rows: List[TableRow] = _parse_table_rows(html_text)

    log_table_rows(table_rows)

    scores = {}

    current_category: str = "Unknown"
    current_module: Optional[Module] = None
    current_module_category: str = current_category
    score_found = False

    for row in table_rows[1:]:
        # Check if the row is a category row
        if row.row_type == RowType.CATEGORY:
            current_category = row.title.removeprefix("Kompetenzbereich ")
            continue

        if row.row_type == RowType.MODULE:
            # If the previous module had no scores, remove it from the scores
            if not score_found and current_module and current_module_category in scores:
                scores[current_module_category].remove(current_module)

            current_module = Module(
                id=_parse_int(row.id),
                title=row.title,
                semester=row.semester,
                grade=_parse_float(row.grade),
                status=_parse_status(row.status),
                credits=_parse_int(row.credits),
                issued_on=row.issued_on,
                scores=[]
            )

            current_module_category = current_category
            score_found = False

            if current_category not in scores:
                scores[current_category] = []

            scores[current_category].append(current_module)

        elif row.row_type == RowType.SCORE and current_module:
            # Check if the row is a score row
            score_found = True
            individual_score = Score(
                id=_parse_int(row.id),
                title=row.title,
                type=ScoreType(row.type),
                semester=row.semester,
                grade=_parse_float(row.grade),
                status=_parse_status(row.status),
                issued_on=row.issued_on,
                attempt=_parse_int(row.attempt),
                specific_scorecard_id=None, # TODO: parse this from the HTML
            )
            current_module.scores.append(individual_score)

            if (individual_score.grade is not None and current_module.grade is None
                    and individual_score.status == ScoreStatus.PASSED):
                current_module.grade = individual_score.grade

    return scores


def log_table_rows(table_rows):
    """Log the table rows for debugging with uniform spacing."""
    for row in table_rows:
        try:
            logger.debug(
                f"{row.id:<10} {row.title:<50} {row.type:<10} {row.semester:<15} {row.grade:<5} "
                f"{row.status:<15} {row.credits:<20} {row.issued_on:<15} {row.attempt:<5} "
                f"{row.note:<5} {row.free_attempt:<5}  -  {row.row_type:<10}"
            )
        except Exception as e:
            logger.exception("Error printing row: %s", e)
    return None


def _parse_table_rows(html_text):
    soup = BeautifulSoup(html_text, "html.parser")
    table = soup.find_all("table")[1]
    table_rows: List[TableRow] = []
    # Iterate over all rows in the table
    for row in table.contents:
        try:
            if type(row) is NavigableString:
                continue

            cells = [cell for cell in row.contents if type(cell) not in [NavigableString, Comment]]
            html_classes = set()
            for cell in cells:
                try:
                    for html_class in cell.attrs.get("class", []):
                        html_classes.add(html_class)
                except Exception as e:
                    logger.exception(e)

            if len(cells) >= 11:
                table_row = _read_module_row(cells)
            elif len(cells) == 10:
                table_row = _read_category_row(cells)
            elif len(cells) <= 2:
                score_cells = [score_cell for score_cell in cells[0].contents if
                               type(score_cell) not in [NavigableString, Comment]]
                if len(score_cells) < 10:
                    continue
                else:
                    table_row = _read_score_row(score_cells)
            else:
                continue
            # Append the parsed row to the list
            table_rows.append(table_row)
        except Exception as e:
            logger.exception(e)
    return table_rows


def _read_module_row(cells):
    return TableRow(
        id=cells[0].text.strip(),
        title=cells[1].text.strip(),
        type=cells[2].text.strip(),
        semester=cells[3].text.strip(),
        grade=cells[4].text.strip(),
        status=cells[5].text.strip(),
        credits=cells[6].text.strip(),
        issued_on=cells[7].text.strip(),
        attempt=cells[8].text.strip(),
        note=cells[9].text.strip(),
        free_attempt=cells[10].text.strip(),
        row_type=RowType.MODULE,
    )


def _read_category_row(cells):
    return TableRow(
        id=cells[0].text.strip(),
        title=cells[1].text.strip(),
        type="",
        semester=cells[2].text.strip(),
        grade=cells[3].text.strip(),
        status=cells[4].text.strip(),
        credits=cells[5].text.strip(),
        issued_on=cells[6].text.strip(),
        attempt=cells[7].text.strip(),
        note=cells[8].text.strip(),
        free_attempt=cells[9].text.strip(),
        row_type=RowType.CATEGORY,
    )


def _read_score_row(score_cells):
    return TableRow(
        id=score_cells[0].text.strip(),
        title=score_cells[1].text.strip(),
        type=score_cells[2].text.strip(),
        semester=score_cells[3].text.strip(),
        grade=score_cells[4].text.strip(),
        status=score_cells[5].text.strip(),
        credits=score_cells[6].text.strip(),
        issued_on=score_cells[7].text.strip(),
        attempt=score_cells[8].text.strip(),
        note=score_cells[9].text.strip(),
        free_attempt=score_cells[10].text.strip(),
        row_type=RowType.SCORE,
    )

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


def get_grade_point_average(scorecard: Dict[str, List[Module]]) -> Optional[float]:
    """Calculate the grade point average for a scorecard.

    The GPA is determined by multiplying each score grade with the credits of its
    module and dividing the sum by the total credits.

    :param scorecard: The scorecard to parse.
    :return: The grade point average or ``None`` if it can't be calculated.
    """
    grade_point_average: float = 0.0
    amount_of_credits: int = 0

    # combine every module from the dict into a single list
    all_modules: List[Module] = []
    for modules in scorecard.values():
        all_modules.extend(modules)

    for module in all_modules:
        for score in module.scores:
            if score.grade is not None and module.credits is not None:
                try:
                    grade_point_average += score.grade * module.credits
                    amount_of_credits += module.credits
                except Exception as e:
                    logger.exception(e)

    # divide the sum of the grades by the number of credits
    if amount_of_credits > 0:
        grade_point_average /= amount_of_credits
    else:
        return None

    return round(grade_point_average, 2)


def get_grade_point_average_progress(scorecard: Dict[str, List[Module]]) -> List[GradePointAverageProgressItem]:
    """Return GPA progress over time.

    Generates a list of data points consisting of the module ID, the
    resulting grade point average at that time and the date of the module
    grade. The calculation follows the same weighting logic as
    :func:`get_grade_point_average`.

    :param scorecard: The scorecard to parse.
    :return: List of :class:`GradePointAverageProgressItem` objects ordered
        chronologically.
    """
    entries: List[dict] = []

    for modules in scorecard.values():
        for module in modules:
            for score in module.scores:
                if score.grade is None or module.credits is None:
                    continue
                try:
                    date_obj = datetime.strptime(score.issued_on, "%d.%m.%Y")
                except Exception:
                    logger.exception("Failed to parse date for module %s", module.id)
                    continue
                entries.append({
                    "module_id": module.id,
                    "grade": score.grade,
                    "credits": module.credits,
                    "date": date_obj,
                })

    # sort entries by date ascending
    entries.sort(key=lambda item: item["date"])

    progress: List[GradePointAverageProgressItem] = []
    total_weighted = 0.0
    total_credits = 0

    for entry in entries:
        total_weighted += entry["grade"] * entry["credits"]
        total_credits += entry["credits"]
        if total_credits == 0:
            continue
        gpa = round(total_weighted / total_credits, 2)
        progress.append(
            GradePointAverageProgressItem(
                module_id=entry["module_id"],
                grade_point_average=gpa,
                date=entry["date"].strftime("%d.%m.%Y"),
            )
        )

    return progress


def get_credit_point_sum(scorecard: Dict[str, List[Module]]) -> int:
    """Return the sum of credits for all modules regardless of score grades."""
    credit_sum = 0

    all_modules: List[Module] = []
    for modules in scorecard.values():
        all_modules.extend(modules)

    for module in all_modules:
        if module.credits is None:
            continue
        try:
            credit_sum += module.credits
        except Exception as e:
            logger.exception(e)

    return credit_sum
