import typing as t
from unittest import TestCase
from markr.app import app
from markr.db.models import TestScore, Student, Test, db
from dataclasses import dataclass 
from sqlalchemy.orm import joinedload
from flask import abort
import pytest
from werkzeug.exceptions import HTTPException

@dataclass
class MockData: 
    fname: str = "Jane"
    lname: str = "Austen"
    student_number: int = 99999
    test_id: int = 1234
    available_marks: int = 10
    obtained_marks: int = 5

def gen_test_result_xml(mock_data: MockData) -> str:
    xml = f"""<mcq-test-result scanned-on="2017-12-04T12:12:10+11:00">
            <first-name>{mock_data.fname}</first-name>
            <last-name>{mock_data.lname}</last-name>
            <student-number>{mock_data.student_number}</student-number>
            <test-id>{mock_data.test_id}</test-id>
            <summary-marks available="{mock_data.available_marks}" obtained="{mock_data.obtained_marks}" />
        </mcq-test-result>"""
    return xml


def gen_input(mocks: t.List[MockData]) -> str:
    """
    Helper for generating XML test score data.

    Input: 
        - mocks: list of MockData objects describing the xml to be created.

    Output: 
    Mock data formatted as xml input /import endpoint is expecting.
    """
    ret = ["<mcq-test-results>"]

    for mock_data in mocks:
        ret.append(gen_test_result_xml(mock_data))

    ret.append("</mcq-test-results>")

    return "".join(ret)

incomplete_data_test_cases = {
    "no_summary_marks" : """<mcq-test-result scanned-on="2017-01-01T00:00:00Z">
                <first-name>Jane</first-name>
                <last-name>Student</last-name>
                <student-number>99999999</student-number>
                <test-id>78763</test-id>
                <answer question="1" marks-available="1" marks-awarded="1">A</answer>
                <answer question="2" marks-available="1" marks-awarded="0">B</answer>
                <answer question="4" marks-available="1" marks-awarded="1">A</answer>
            </mcq-test-result>""",
    "available_marks_missing" :  """<mcq-test-result scanned-on="2017-01-01T00:00:00Z">
                <first-name>Jane</first-name>
                <last-name>Student</last-name>
                <student-number>99999999</student-number>
                <test-id>78763</test-id>
                <summary-marks obtained="2" />
                <answer question="1" marks-available="1" marks-awarded="1">A</answer>
                <answer question="2" marks-available="1" marks-awarded="0">B</answer>
                <answer question="4" marks-available="1" marks-awarded="1">A</answer>
            </mcq-test-result>""",
    "obtained_marks_missing" :  """<mcq-test-result scanned-on="2017-01-01T00:00:00Z">
                <first-name>Jane</first-name>
                <last-name>Student</last-name>
                <student-number>99999999</student-number>
                <test-id>78763</test-id>
                <summary-marks available="10" />
                <answer question="1" marks-available="1" marks-awarded="1">A</answer>
                <answer question="2" marks-available="1" marks-awarded="0">B</answer>
                <answer question="4" marks-available="1" marks-awarded="1">A</answer>
            </mcq-test-result>""",
    "student_number_missing" :  """<mcq-test-result scanned-on="2017-01-01T00:00:00Z">
                <first-name>Jane</first-name>
                <last-name>Student</last-name>
                <test-id>78763</test-id>
                <summary-marks available="10" obtained="2" />
                <answer question="1" marks-available="1" marks-awarded="1">A</answer>
                <answer question="2" marks-available="1" marks-awarded="0">B</answer>
                <answer question="4" marks-available="1" marks-awarded="1">A</answer>
            </mcq-test-result>""",
    "test_id_missing" :  """<mcq-test-result scanned-on="2017-01-01T00:00:00Z">
                <first-name>Jane</first-name>
                <last-name>Student</last-name>
                <student-number>99999999</student-number>
                <summary-marks available="10" obtained="2" />
                <answer question="1" marks-available="1" marks-awarded="1">A</answer>
                <answer question="2" marks-available="1" marks-awarded="0">B</answer>
                <answer question="4" marks-available="1" marks-awarded="1">A</answer>
            </mcq-test-result>""",
}


class TestImport(TestCase):
    def tearDown(self) -> None:
        # Ensure DB is cleared after each test
        with app.app_context():
            Student.query.delete()
            Test.query.delete()
            TestScore.query.delete()
            db.session.commit()

    def test_import__success(self):
        """
        Test that /import adds data correctly to the db.
        """
        mock_input = MockData() 
        with app.test_client() as client: 
            resp = client.post("/import", data=gen_input([MockData()]), content_type='text/xml+markr')
       
        with app.app_context():
            score = TestScore.query.options(joinedload(TestScore.student), joinedload(TestScore.test)).first()

        self.assertEqual(score.score, mock_input.obtained_marks)
        self.assertEqual(score.student.id, mock_input.student_number)
        self.assertEqual(score.test.id, mock_input.test_id)
        self.assertEqual(score.test.available_marks, mock_input.available_marks)
    
    def test_import__excess_fields(self):
        """
        Test that /import can handle extra information and fields in the input xml. 
        Only relevant information should be added to the db.
        """
        mock_data = MockData()
        xml = f"""
        <mcq-test-results>
            <mcq-test-result scanned-on="2017-01-01T00:00:00Z">
                <first-name>{mock_data.fname}</first-name>
                <more-random-stuff>noise</more-random-stuff>
                <last-name>Student</last-name>
                <student-number>99999999</student-number>
                <test-id>78763</test-id>
                <summary-marks available="10" obtained="2" />
                <answer question="1" marks-available="1" marks-awarded="1">A</answer>
                <answer question="2" marks-available="1" marks-awarded="0">B</answer>
                <answer question="4" marks-available="1" marks-awarded="1">A</answer>
            </mcq-test-result>
            <random-stuff></random-stuff>
        </mcq-test-results>
        """
        with app.test_client() as client: 
            resp = client.post("/import", data=xml, content_type='text/xml+markr')
       
        with app.app_context():
            score = TestScore.query.options(joinedload(TestScore.student), joinedload(TestScore.test)).first()
            self.assertEqual(len(TestScore.query.all()), 1)

        self.assertEqual(score.student.fname, mock_data.fname)

    def test_import__pick_student_highest_score(self):
        """
        If a test score is sent multiple times for the same student, then pick the highest result.
        """
        # Test highest score is picked within a single request:
        mock_data = [MockData(obtained_marks=2), MockData(obtained_marks=9),  MockData(obtained_marks=8)]
        with app.test_client() as client: 
            resp = client.post("/import", data=gen_input(mock_data), content_type='text/xml+markr')
        
        with app.app_context():
            score = TestScore.query.options(joinedload(TestScore.student), joinedload(TestScore.test)).first()
            # Only one score should be present
            self.assertEqual(len(TestScore.query.all()), 1)
        
        self.assertEqual(score.score, 9, "Highest mark should have been picked")

        # Test higher score is picked when subsequent requests are sent:
        # First request is lower, so score should remain the same
        with app.test_client() as client: 
            resp = client.post("/import", data=gen_input([MockData(obtained_marks=2)]), content_type='text/xml+markr') 
        
        with app.app_context():
            score = TestScore.query.options(joinedload(TestScore.student), joinedload(TestScore.test)).first()
        self.assertEqual(score.score, 9, "Highest mark should have been picked")

        # Second request: score must be updated:
        with app.test_client() as client: 
            resp = client.post("/import", data=gen_input([MockData(obtained_marks=11)]), content_type='text/xml+markr') 
        
        with app.app_context():
            score = TestScore.query.options(joinedload(TestScore.student), joinedload(TestScore.test)).first()
        self.assertEqual(score.score, 11, "Highest mark should have been picked")
    
    def test_import__pick_test_highest_available_marks(self):
        """
        If there is discrepancy in the available marks for a particular test, then set the 
        available marks to the highest number. 
        """
        mock_data = [MockData(available_marks=2), MockData(available_marks=9),  MockData(available_marks=8)]
        with app.test_client() as client: 
            resp = client.post("/import", data=gen_input(mock_data), content_type='text/xml+markr')
        
        with app.app_context():
            score = TestScore.query.options(joinedload(TestScore.student), joinedload(TestScore.test)).first()
            # Only one score should be present
            self.assertEqual(len(TestScore.query.all()), 1)
        
        self.assertEqual(score.test.available_marks, 9, "Highest available marks should have been picked")

        # Test higher score is picked when subsequent requests are sent:
        # First request is lower, so score should remain the same
        with app.test_client() as client: 
            resp = client.post("/import", data=gen_input([MockData(available_marks=2)]), content_type='text/xml+markr') 
        
        with app.app_context():
            score = TestScore.query.options(joinedload(TestScore.student), joinedload(TestScore.test)).first()
        self.assertEqual(score.test.available_marks, 9, "Highest mark should have been picked")

        # Second request: score must be updated:
        with app.test_client() as client: 
            resp = client.post("/import", data=gen_input([MockData(available_marks=11)]), content_type='text/xml+markr') 
        
        with app.app_context():
            score = TestScore.query.options(joinedload(TestScore.student), joinedload(TestScore.test)).first()
        self.assertEqual(score.test.available_marks, 11, "Highest mark should have been picked")
    
    def test_import__incomplete_data(self):
        """
        If any of the test results have incomplete data, then the whole document
        should be rejected.
        """
        # Results with no summary marks should be rejected
       
        for test_case, incomplete_test_result in incomplete_data_test_cases.items():
            incomplete_input = f"""
                <mcq-test-results>
                    {gen_test_result_xml(MockData(student_number=1234))}
                    {incomplete_test_result}
                    {gen_test_result_xml(MockData(student_number=9876))}
                    <random-stuff></random-stuff>
                </mcq-test-results>
                """

            with app.test_client() as client: 
                resp = client.post("/import", data=incomplete_input, content_type='text/xml+markr')
            self.assertEqual(resp.status_code, 400)

            # All entries should have been considered invalid, nothing should be added to the db.
            with app.app_context():
                scores = TestScore.query.all()
            self.assertEqual(len(scores), 0, f"Failed incomplete test case: {test_case}")
        

    def test_import__wrong_xml(self):
        """
        If xml is sent to /import that doesn't match the expected format, it should be rejected. 
        """
        xml = f"""
        <a-different-doc>
            <random-stuff>Irrelevant information</random-stuff>
        </a-different-doc>
        """
        with app.test_client() as client: 
            resp = client.post("/import", data=xml, content_type='text/xml+markr')
        
        self.assertEqual(resp.status_code, 400)
    
    def test_import__malformed_xml(self):
        """
        If data is sent to /import that is malformed, the request should be rejected.
        """
        with app.test_client() as client: 
            resp = client.post("/import", data="malformed content", content_type='text/xml+markr')
        
        self.assertEqual(resp.status_code, 400)
    
    def test_import__json(self):
        """
        If json is sent to /import, it is rejected.
        """
        with app.test_client() as client: 
            resp = client.post("/import", data="{}", content_type='application/json')
        
        self.assertEqual(resp.status_code, 400)
    

        
        







