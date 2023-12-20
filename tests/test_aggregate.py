import os 
import json
from unittest import TestCase
from markr.db.models import TestScore, Student, Test, db
from markr.app import app

class TestImport(TestCase):
    def setUp(self) -> None:
        app.config["TESTING"] = True

        # Add sample data to db 
        current_directory = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_directory, 'sample_data.xml')
        with open(file_path, 'r') as file:
            file_content = file.read()
        with app.test_client() as client: 
            import_resp = client.post("/import", data=file_content, content_type='text/xml+markr')

    def tearDown(self) -> None:
        # Ensure DB is cleared after each test
        with app.app_context():
            Student.query.delete()
            Test.query.delete()
            TestScore.query.delete()
            db.session.commit()

    def test_aggregate(self):
        """
        Ensure aggregations are performed correctly on the sample data.
        """
        with app.test_client() as client: 
            agg_resp = client.get("/results/9863/aggregate")
        json_resp = json.loads(agg_resp.text)

        self.assertEqual(json_resp['median'], 50.0)
        self.assertEqual(json_resp['min'], 30.0)
        self.assertEqual(json_resp['max'], 75.0)
        self.assertEqual(round(json_resp['mean'], 2), 50.8)
        self.assertEqual(round(json_resp['stddev'], 2), 9.92)
        self.assertEqual(json_resp['p25'], 45.0)
        self.assertEqual(json_resp['p50'], 50.0)
        self.assertEqual(json_resp['p95'], 70.0)
        self.assertEqual(json_resp['count'], 81)

    def test_aggregate__bad_test_id(self):
        """
        Ensure a malformed test ID is rejected. 
        """
        with app.test_client() as client: 
            resp = client.get("/results/adsfkj/aggregate")
        
        self.assertEqual(resp.status_code, 400)
    
    def test_aggregate__nonexistent_test_id(self):
        """
        Ensure a non-existent test-id is properly handled
        """
        with app.test_client() as client: 
            resp = client.get("/results/111111/aggregate")
        
        self.assertEqual(resp.status_code, 400)
        
        

