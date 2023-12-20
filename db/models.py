import os
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import xml.etree.ElementTree as ET
from sqlalchemy.orm import Session, relationship

import numpy as np

db = SQLAlchemy()

class Student(db.Model):
    __tablename__ = "students"

    # Assume student number is unique
    id = db.Column(db.Integer, primary_key=True)
    fname = db.Column(db.String(80), nullable=False)
    lname = db.Column(db.String(80), nullable=False)

    test_scores = relationship("TestScore", back_populates="student")


class Test(db.Model):
    __tablename__ = "tests"

    # Assumes test ids are unique
    id = db.Column(db.Integer, primary_key=True)
    available_marks = db.Column(db.Integer, nullable=False)

    test_scores = relationship("TestScore", back_populates="test")


class TestScore(db.Model):
    __tablename__ = "test_scores"

    id = db.Column(db.Integer, primary_key=True)

    test_id = db.Column(db.Integer, db.ForeignKey("tests.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)

    # Maybe we need datetime to record the time the test was scanned in? 
    score = db.Column(db.Integer, nullable=False)

    student = relationship("Student", back_populates="test_scores")
    test = relationship("Test", back_populates="test_scores")


def extract_data(root: ET.Element):
    """
    - xml: root element of xml data
    """
    # Iterate through each of the test result objects given
    for elem in root.findall("mcq-test-result"):
        first_name = elem.find("first-name").text
        last_name = elem.find("last-name").text
        if elem.find("student-number") is None:
            raise RuntimeError("No student number available")
        student_number = int(elem.find("student-number").text)
        if elem.find("test-id") is None: 
            raise RuntimeError("No test ID given")
        test_id = int(elem.find("test-id").text)

        summary_marks = elem.find("summary-marks")
        if summary_marks is None: 
            raise RuntimeError("No summary marks available")

        # TODO: potentially handle obtained marks > available, although this 
        # may be desired in the case of bonus marks. 
        if not summary_marks.attrib.get("available"):
            raise RuntimeError("Available marks not set")
        available_marks = int(summary_marks.attrib.get("available"))
        if not summary_marks.attrib.get("obtained"): 
            raise RuntimeError("Obtained marks not set")

        obtained_marks = int(summary_marks.attrib.get("obtained"))

        # Existing entries 
        existing_student = Student.query.get(student_number)
        existing_test = Test.query.get(test_id)
        existing_score = TestScore.query.filter_by(
            test_id=test_id, student_id=student_number
        ).first()

        # Create DB entries 
        if not existing_student:
            student = Student(id=student_number, fname=first_name, lname=last_name)
            db.session.add(student)

        if not existing_test:
            test = Test(id=test_id, available_marks=available_marks)
            db.session.add(test)
        elif existing_test.available_marks < available_marks:
            existing_test.available_marks = available_marks
        
        if not existing_score:
            score = TestScore(
                test_id=test_id, student_id=student_number, score=obtained_marks
            )
            db.session.add(score)
        elif existing_score.score < obtained_marks:
            existing_score.score = obtained_marks
        
    db.session.commit()

def get_test_score_summary(test_id: int): 
    scores = TestScore.query.filter_by(test_id=test_id).all()
    if len(scores) == 0:
        raise RuntimeError(f"No test found with test ID {test_id}")
    
    dataset = np.array([score.score for score in scores])
    return {
        "mean": np.mean(dataset),
        "median": np.median(dataset),
        "stddev" : np.std(dataset),
        "min" : int(np.min(dataset)),
        "max" : int(np.max(dataset)),
        "count" : np.size(dataset),
        "p25": np.percentile(dataset, 25),
        "p50": np.percentile(dataset, 50),
        "p95": np.percentile(dataset, 95),
    }

def init_db(app):
    """
    Initializes & migrates the database.
    """
    # Use sqlite in memory db for testing 
    if os.getenv("RUN_ENV") == "TESTING":
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    else:
        app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql+psycopg2://{}:{}@{}/{}".format(
            os.getenv("DB_USER", "postgres"),
            os.getenv("DB_PASSWORD", "mysecretpassword"),
            os.getenv("DB_HOST", "db"),
            os.getenv("DB", "markr"),
        )
    db.app = app
    db.init_app(app)
    Migrate(app, db)

    with app.app_context():
        db.create_all()
