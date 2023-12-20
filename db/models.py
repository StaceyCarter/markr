import os
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.orm import relationship

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

    # Assume test ids are unique
    id = db.Column(db.Integer, primary_key=True)
    available_marks = db.Column(db.Integer, nullable=False)

    test_scores = relationship("TestScore", back_populates="test")


class TestScore(db.Model):
    __tablename__ = "test_scores"

    id = db.Column(db.Integer, primary_key=True)

    # index test_id since our aggregate endpoint relies on this
    test_id = db.Column(db.Integer, db.ForeignKey("tests.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)

    score = db.Column(db.Integer, nullable=False) # Assume half marks are not given
    percent_score = db.Column(db.Float, nullable=False)
    # TODO: potentially record the time the test score was scanned

    student = relationship("Student", back_populates="test_scores")
    test = relationship("Test", back_populates="test_scores")


def init_db(app):
    """
    Initialize & migrates the database.
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
