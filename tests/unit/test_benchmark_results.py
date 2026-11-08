import unittest

class ResultTests(unittest.TestCase):
    def test_accepted_does_not_replace_confirmed(self):
        from scripts.benchmark import validate_counts
        self.assertFalse(validate_counts({"confirmed":59,"enrolled":60,"slots":0,"owners":60,"pending":0},60,"redis_queue"))
        self.assertFalse(validate_counts({"confirmed":60,"enrolled":60,"slots":0,"owners":60,"pending":1},60,"redis_queue"))
        self.assertTrue(validate_counts({"confirmed":60,"enrolled":60,"slots":0,"owners":60,"pending":0},60,"redis_queue"))
        self.assertTrue(validate_counts({"confirmed":60,"enrolled":60},60,"postgres"))

    def test_stats_units(self):
        from scripts.container_metrics import bytes_value
        self.assertEqual(bytes_value("1.5MiB"),1572864)
        self.assertEqual(bytes_value("2MB"),2000000)

    def test_report_median_excludes_warmup(self):
        import tempfile, json
        from pathlib import Path
        from unittest.mock import patch
        from scripts import benchmark
        with tempfile.TemporaryDirectory() as root:
            folder=Path(root)
            for name,value in [("postgres-1",10),("postgres-2",30),("postgres-3",20),("warmup-postgres",999)]:
                (folder/(name+"-summary.json")).write_text(json.dumps({"metrics":{
                    "http_req_duration{phase:register}":{"values":{"avg":value,"p(95)":value}}}}))
                (folder/(name+"-verification.json")).write_text(json.dumps({"confirmed":60,"valid":True}))
            with patch.object(benchmark,"RESULTS",folder):
                benchmark.report()
            text=(folder/"comparison.md").read_text()
            self.assertIn("Median postgres",text)
            self.assertIn("20",text)
