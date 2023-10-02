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
