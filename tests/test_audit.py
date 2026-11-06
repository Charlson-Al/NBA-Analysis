import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from audit import CSV_PATH, DOCX_PATH, inspect, parse_number

class AuditTests(unittest.TestCase):
    def test_source_reconciliation(self):
        result=inspect()
        self.assertEqual(result['teams'],30)
        self.assertEqual(result['columns'],61)
        self.assertTrue(result['pass_numeric_reconciliation'],result['mismatches'][:3])
        self.assertTrue(result['blocked_for_game_day'])

    def test_display_parser(self):
        self.assertEqual(parse_number('17.5% forced'),17.5)
        self.assertEqual(parse_number('27.3% allowed'),27.3)

    def test_tamper_detected(self):
        with CSV_PATH.open(newline='',encoding='utf-8-sig') as f:
            reader=csv.DictReader(f)
            rows=list(reader)
            cols=reader.fieldnames
        rows[0]['adjusted_off_rating']='999.9'
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'modified.csv'
            with path.open('w',newline='',encoding='utf-8') as f:
                writer=csv.DictWriter(f,fieldnames=cols)
                writer.writeheader();writer.writerows(rows)
            result=inspect(path,DOCX_PATH)
        self.assertFalse(result['pass_numeric_reconciliation'])
        self.assertTrue(any(m['team']=='ATL' and m['field']=='adjusted_off_rating' for m in result['mismatches']))

if __name__=='__main__':
    unittest.main()
