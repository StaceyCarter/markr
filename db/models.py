import os
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

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

    score = db.Column(db.Integer, nullable=False)


def init_db(app):
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
