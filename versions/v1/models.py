"""
This Python script defines Pydantic models that are used in the parent API to validate data, serialize and deserialize
Python primitives to JSON, and generate OpenAPI schema.

The following models are defined:

- `ErrorResponse`: Represents error messages that are returned on HTTP errors.
- `UserCredentials`: Represents the user's credentials (username and password).
- `UserSignInDetails`: Represents the response returned when a user signs in, including a welcome message, user's
  display name, session cookie, and an ASI parameter.
- `SessionStatus`: Represents the current session's status, indicating its validity and a message.
- `ScorecardIDs`: Represents a mapping of identifiers for available scorecards and a message confirming successful
  retrieval of these identifiers.
- `ScoreType` and `ScoreStatus`: Enum classes representing various types and statuses of student scores respectively.
- `IndividualScore` and `BaseScore`: Represent individual scores and base scores in a student's scorecard respectively,
  with detailed attributes such as id, title, type, semester, grade, status, issued date, number of attempts, and the
  ID of the specific scorecard if applicable.
- `Scorecard`: Represents a student's scorecard as a list of BaseScores and includes the overall grade point average
  and a message confirming successful retrieval of the scorecard.

Each model is represented by a class that inherits from pydantic's `BaseModel` or `str` for Enum. The schema and example
values for the fields are defined by the `Field` function from pydantic, used in the attribute annotations. The data
types for these fields include built-in Python data types and custom Enum classes.
"""
from enum import Enum
from typing import Dict, Optional, List

from pydantic import BaseModel, Field


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


class SessionStatus(BaseModel):
    """
    Model to represent the validity of a session.
    """
    is_valid: bool
    message: str


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


class ScoreType(str, Enum):
    """
    Enum to represent the type of score.
    """
    PL = "PL"
    SL = "SL"


class ScoreStatus(str, Enum):
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
    id: int = Field(..., example=110, description="The number of the score")
    title: str = Field(..., example="Grundlagen der Informatik", description="The name of the score")
    type: ScoreType = Field(..., example="Prüfungsleitung", description="The type of the score")
    semester: str = Field(..., example="WS 2017/18", description="The semester of the score")
    grade: Optional[float] = Field(None, example=1.3, description="The grade of the score")
    status: ScoreStatus = Field(..., example="bestanden", description="The state of the score")
    issued_on: str = Field(..., example="01.02.2018", description="The date of the score")
    attempt: Optional[int] = Field(None, example=1, description="The number of tries")
    specific_scorecard_id: Optional[str] = Field(None, example="auswahlBaum|abschluss:abschl=82|studiengang:"
                                                               "stg=001,pversion=2017,kzfa=H|kontoOnTop:labnrzu=0000001"
                                                               "|konto:labnrzu=0000001|konto:labnrzu=0000001|pruefung"
                                                               ":labnr=0000001",
                                                 description="The ID of the specific scorecard")


class BaseScore(BaseModel):
    """
    Model to represent a score.
    """
    id: int = Field(..., example=100, description="The number of the score")
    title: str = Field(..., example="Grundlagen der Informatik", description="The name of the score")
    semester: str = Field(..., example="WS 2017/18", description="The semester of the score")
    grade: Optional[float] = Field(None, example=1.3, description="The grade of the score if a individual score"
                                                                  " contains a grade. If multiple individual scores are"
                                                                  " present, this field is None.")
    status: ScoreStatus = Field(..., example="bestanden", description="The state of the score")
    credits: int = Field(..., example=10, description="The credits of the score")
    issued_on: str = Field(..., example="01.02.2018", description="The date of the score")
    individual_scores: List[IndividualScore] = Field(..., example=[{
        "id": 110,
        "title": "Grundlagen der Informatik",
        "type": "PL",
        "semester": "WS 2017/18",
        "grade": 1.3,
        "status": "bestanden",
        "issued_on": "01.02.2018",
        "attempt": 1,
        "specific_scorecard_id": "auswahlBaum|abschluss:abschl=82|studiengang:stg=001,pversion=2017,kzfa=H|kontoOnTop:"
                                 "labnrzu=0000001|konto:labnrzu=0000001|konto:labnrzu=0000001|pruefung:labnr=0000001"
    }, {
        "id": 1109,
        "title": "Grundlagen der Informatik",
        "type": "SL",
        "semester": "WS 2017/18",
        "grade": None,
        "status": "bestanden",
        "issued_on": "01.02.2018",
        "attempt": 1,
        "specific_scorecard_id": None
    }], description="A list of individual scores")


class Scorecard(BaseModel):
    """
    Model to represent a scorecard.
    """
    scores: list[BaseScore]
    grade_point_average: Optional[float] = Field(None, example=1.3, description="The grade point average")
    message: str = Field(..., example="Successfully retrieved scorecard",
                         description="A message indicating if the request was successful or not")
