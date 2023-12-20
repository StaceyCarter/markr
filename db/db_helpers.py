import typing as t
import xml.etree.ElementTree as ET
import numpy as np
from dataclasses import dataclass
from sqlalchemy.orm import Session, relationship
from markr.db.models import Student, Test, TestScore, db

@dataclass
class ScoreData: 
    """"
    Helper struct for extracting and storing data about a particular test score. 
    handles ensuring all relevant data is populated.
    """
    first_name : str 
    last_name : str 
    student_number : int 
    obtained_marks : int 
    available_marks : int 

    def __init__(self, elem: ET.Element):
        self.first_name = elem.find("first-name").text
        self.last_name = elem.find("last-name").text
        if elem.find("student-number") is None:
            raise RuntimeError("No student number available")
        
        self.student_number = int(elem.find("student-number").text)
        if elem.find("test-id") is None: 
            raise RuntimeError("No test ID given")
        self.test_id = int(elem.find("test-id").text)

        summary_marks = elem.find("summary-marks")
        if summary_marks is None: 
            raise RuntimeError("No summary marks available")

        # TODO: potentially handle obtained marks > available, although this 
        # may be desired in the case of bonus marks. 
        if not summary_marks.attrib.get("available"):
            raise RuntimeError("Available marks not set")
        self.available_marks = int(summary_marks.attrib.get("available"))
        if not summary_marks.attrib.get("obtained"): 
            raise RuntimeError("Obtained marks not set")

        self.obtained_marks = int(summary_marks.attrib.get("obtained"))
    
    @property
    def percent_score(self) -> float: 
        return round((self.obtained_marks / self.available_marks) * 100 , 2)


def extract_data(root: ET.Element) -> int:
    """
    Responsible for extracting relevant test data from an XML root.
    If any error occurs in extracting data for one test, then the entire
    request is aborted. 

    Input: 
     - XML root element.

    Output: 
     - Number of test result records that were added or updated in the DB. 
    """
    tally = 0
    for elem in root.findall("mcq-test-result"):
        create_or_update_entries(
            ScoreData(elem)
        )
        tally += 1
    db.session.commit()
    return tally 

def create_or_update_entries(sd: ScoreData):
    """
    Stages updates and/or new entries to be commited to the DB. 

    NOT responsible for committing.
    """
    existing_student = Student.query.get(sd.student_number)
    existing_test = Test.query.get(sd.test_id)
    existing_score = TestScore.query.filter_by(
        test_id=sd.test_id, student_id=sd.student_number
    ).first()
 
    if not existing_student:
        student = Student(id=sd.student_number, fname=sd.first_name, lname=sd.last_name)
        db.session.add(student)

    if not existing_test:
        test = Test(id=sd.test_id, available_marks=sd.available_marks)
        db.session.add(test)
    elif existing_test.available_marks < sd.available_marks:
        existing_test.available_marks = sd.available_marks
    
    if not existing_score:
        score = TestScore(
            test_id=sd.test_id, student_id=sd.student_number, score=sd.obtained_marks, percent_score=sd.percent_score
        )
        db.session.add(score)
    elif existing_score.score < sd.obtained_marks:
        existing_score.score = sd.obtained_marks
        existing_score.percent_score = sd.percent_score


def get_test_score_summary(test_id: int) -> t.Dict[str, t.Union[float, int]]: 
    """
    Collects all test scores from the DB for the given test ID, and returns 
    related aggregate statistics. 

    Input: 
    - test_id for the test of interest 

    Output: 
    - Dictionary with various aggregate statistics pertaining to the given test.
    """
    scores = TestScore.query.filter_by(test_id=test_id).all()
    if len(scores) == 0:
        raise RuntimeError(f"No test found with test ID {test_id}")
    
    dataset = np.array([score.percent_score for score in scores])
    return {
        "mean": round(np.mean(dataset), 2),
        "median": np.median(dataset),
        "stddev" : round(np.std(dataset), 2),
        "min" : int(np.min(dataset)),
        "max" : int(np.max(dataset)),
        "count" : np.size(dataset),
        "p25": np.percentile(dataset, 25),
        "p50": np.percentile(dataset, 50),
        "p95": np.percentile(dataset, 95),
    }