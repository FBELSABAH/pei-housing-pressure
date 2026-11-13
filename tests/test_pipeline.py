import sys,unittest,sqlite3,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pipeline as p
class PipelineTests(unittest.TestCase):
 def setUp(self):
  p.run();self.db=sqlite3.connect(p.ROOT/'data/processed/housing.sqlite');self.db.row_factory=sqlite3.Row
 def tearDown(self):self.db.close()
 def test_idempotency(self):self.assertEqual(p.run()['analytical_sha256'],p.run()['analytical_sha256'])
 def test_geography_excludes_ontario(self):self.assertEqual(self.db.execute("SELECT COUNT(*) FROM observations WHERE source_geo LIKE '%Ontario%'").fetchone()[0],0)
 def test_unique_keys(self):
  with self.assertRaises(sqlite3.IntegrityError):self.db.execute('INSERT INTO observations SELECT * FROM observations LIMIT 1')
 def test_calendar_alignment(self):
  r=self.db.execute('SELECT * FROM annual_supply WHERE year=2022').fetchone()
  self.assertEqual(r['population_change'],169731-164203)
 def test_no_starts_substitution(self):
  r=self.db.execute('SELECT * FROM annual_supply WHERE year=2025').fetchone();self.assertGreater(r['starts'],0);self.assertIsNone(r['completions'])
 def test_no_partial_year_scenario(self):self.assertEqual(self.db.execute('SELECT COUNT(*) FROM household_scenarios WHERE year>2022').fetchone()[0],0)
 def test_scenario_math_and_direction(self):
  r=list(self.db.execute('SELECT * FROM household_scenarios WHERE year=2022'))
  self.assertEqual(len(r),3);self.assertAlmostEqual(r[0]['illustrative_pressure_balance'],5528/2-1266);self.assertGreater(r[0]['illustrative_pressure_balance'],r[-1]['illustrative_pressure_balance'])
 def test_rent_change_not_percentage_points(self):
  r=self.db.execute("SELECT * FROM rental_trends WHERE year=2025 AND geo='Charlottetown survey area'").fetchone();self.assertAlmostEqual(r['observed_rent_change_pct'],100*(1354/1239-1))
 def test_missing_published_observation_stays_null(self):
  rows,q=p.normalize()
  for r in rows:
   if r['status'] in ('F','..','x'):self.assertIsNone(r['value'])
 def test_sources_present(self):self.assertEqual(len(json.loads((p.ROOT/'data/raw/manifest.json').read_text())),5)
if __name__=='__main__':unittest.main()
