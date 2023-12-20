import os
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import xml.etree.ElementTree as ET
from sqlalchemy.orm import Session

db = SQLAlchemy()

class Student(db.Model):
    __tablename__ = "students"

    # Assume student number is unique
    id = db.Column(db.Integer, primary_key=True)
    fname = db.Column(db.String(80), nullable=False)
    lname = db.Column(db.String(80), nullable=False)


class Test(db.Model):
    __tablename__ = "tests"

    # Assumes test ids are unique
    id = db.Column(db.Integer, primary_key=True)
    available_marks = db.Column(db.Integer, nullable=False)


class TestScore(db.Model):
    __tablename__ = "test_scores"

    id = db.Column(db.Integer, primary_key=True)

    test_id = db.Column(db.Integer, db.ForeignKey("tests.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)

    # Maybe we need datetime to record the time the test was scanned in? 
    score = db.Column(db.Integer, nullable=False)


def extract_data(root: ET.Element):
    """
    - xml: root element of xml data
    """
    # Iterate through each of the test result objects given
    for elem in root.findall("mcq-test-result"):
        first_name = elem.find("first-name").text
        last_name = elem.find("last-name").text
        student_number = int(elem.find("student-number").text)
        test_id = int(elem.find("test-id").text)

        summary_marks = elem.find("summary-marks")
        available_marks = int(summary_marks.attrib.get("available"))
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
        
        if not existing_score:
            score = TestScore(
                test_id=test_id, student_id=student_number, score=obtained_marks
            )
            db.session.add(score)
        
    db.session.commit()


def init_db(app):
    """
    Initializes & migrates database.
    """
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
