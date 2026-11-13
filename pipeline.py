"""Official-data pipeline. No API credentials, inferred values, or silent source fallbacks."""
from pathlib import Path
import argparse,csv,datetime,hashlib,io,json,os,sqlite3,time,urllib.request,zipfile
ROOT=Path(__file__).resolve().parent
TABLES={'17100009':'Population estimates, quarterly','34100126':'Housing starts, completions and under construction, all areas, annual','34100133':'Average rents, urban areas 10,000+','34100131':'Vacancy, row/apartment 3+ units, agglomerations 50,000+','34100132':'Vacancy, row/apartment 3+ units, agglomerations 10,000–49,999'}
GEOS={'Prince Edward Island':'PEI','Charlottetown, Prince Edward Island':'Charlottetown survey area','Summerside, Prince Edward Island':'Summerside survey area'}

def dump(path,data):
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2)+'\n')
def sha(b):return hashlib.sha256(b).hexdigest()
def download():
 manifest=[]
 for table,title in TABLES.items():
  url=f'https://www150.statcan.gc.ca/n1/tbl/csv/{table}-eng.zip'
  b=urllib.request.urlopen(url,timeout=120).read();z=zipfile.ZipFile(io.BytesIO(b));raw=z.read(table+'.csv')
  p=ROOT/'data/raw'/f'{table}.csv';p.write_bytes(raw)
  manifest.append(dict(table=table,title=title,url=url,page=f'https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid={table}01',retrieved_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),csv_sha256=sha(raw),zip_sha256=sha(b),bytes=len(raw)))
 dump(ROOT/'data/raw/manifest.json',manifest)
def metric_for(t,r):
 if t=='17100009':return 'population'
 if t=='34100126' and r['Type of unit']=='Total units':return {'Housing starts':'starts','Housing completions':'completions'}.get(r['Housing estimates'])
 if t=='34100133' and r['Type of structure']=='Row and apartment structures of three units and over' and r['Type of unit']=='Two bedroom units':return 'rent_2br'
 if t in ('34100131','34100132'):return 'vacancy_pct'

def normalize():
 out=[];rejected=[];counts={};unavailable=[]
 for t in TABLES:
  n=0
  with (ROOT/'data/raw'/f'{t}.csv').open(encoding='utf-8-sig',newline='') as f:
   for r in csv.DictReader(f):
    if r['GEO'] not in GEOS or r['REF_DATE']<'2017':continue
    m=metric_for(t,r)
    if not m:continue
    if m in ('starts','completions','population') and r['GEO']!='Prince Edward Island':continue
    if m in ('rent_2br','vacancy_pct') and r['GEO']=='Prince Edward Island':continue
    if t=='34100131' and r['GEO']!='Charlottetown, Prince Edward Island':continue
    if t=='34100132' and r['GEO']!='Summerside, Prince Edward Island':continue
    if r['SCALAR_FACTOR']!='units':raise ValueError('Unexpected scaling')
    value=None
    if r['VALUE'] and r['STATUS'] not in ('F','x','..'):
     value=float(r['VALUE'])
     if value<0 or (m=='vacancy_pct' and value>100):raise ValueError('Out-of-range published observation')
    else:unavailable.append(dict(table=t,period=r['REF_DATE'],geo=r['GEO'],metric=m,status=r['STATUS']))
    out.append(dict(series=r['VECTOR'],period=r['REF_DATE'],geo=GEOS[r['GEO']],source_geo=r['GEO'],dguide=r['DGUID'],metric=m,value=value,unit=r['UOM'],status=r['STATUS'],source=t));n+=1
  counts[t]=n
 keys=[(r['series'],r['period']) for r in out]
 if len(set(keys))!=len(keys):raise ValueError('Duplicate vector/period; refresh aborted')
 required={'population','starts','completions','rent_2br','vacancy_pct'}
 if {r['metric'] for r in out}!=required:raise ValueError('Source schema or geography changed')
 return sorted(out,key=lambda r:(r['series'],r['period'])),dict(selected_records=len(out),source_counts=counts,duplicate_keys=0,unavailable_observations=unavailable,rejected_records=rejected,coverage={m:max(r['period'] for r in out if r['metric']==m and r['value'] is not None) for m in required})

def export_csv(path,rows,fields=None):
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields or list(rows[0]));w.writeheader();w.writerows(rows)
def run(dsn=None):
 start=time.perf_counter();rows,quality=normalize();export_csv(ROOT/'data/processed/observations.csv',rows)
 schema=(ROOT/'sql/schema.sql').read_text();views=(ROOT/'sql/analysis.sql').read_text()
 db=sqlite3.connect(ROOT/'data/processed/housing.sqlite');db.row_factory=sqlite3.Row
 with db:
  db.executescript(schema);db.execute('DELETE FROM observations')
  db.executemany('INSERT INTO observations VALUES (?,?,?,?,?,?,?,?,?,?)',[tuple(r.values()) for r in rows]);db.executescript(views)
 results={n:[dict(r) for r in db.execute('SELECT * FROM '+n)] for n in ['annual_supply','rental_trends','household_scenarios']}
 for n,rs in results.items():export_csv(ROOT/'data/processed'/f'{n}.csv',rs)
 quality['annual_rows']=len(results['annual_supply']);quality['scenario_rows']=len(results['household_scenarios'])
 quality['warnings']=['Completions source ends in 2022; later completion values are NULL, never zero or substituted starts.','Urban rental survey areas are not Charlottetown/Summerside municipal boundaries and are not PEI-wide.','Average observed rent is not asking rent or a fixed-sample rent inflation measure.','Scenario: population change / assumed household size; not a causal estimate, stock deficit, or official projection.']
 if dsn:
  import psycopg
  with psycopg.connect(dsn) as pg:
   pg.execute(schema);pg.execute('DELETE FROM observations')
   with pg.cursor().copy('COPY observations FROM STDIN') as copy:
    for r in rows:copy.write_row(tuple(r.values()))
   pg.execute(views)
   for n,rs in results.items():
    with pg.cursor(row_factory=psycopg.rows.dict_row) as c:
     c.execute('SELECT * FROM '+n);actual=[dict(r) for r in c.fetchall()]
    if actual!=rs:raise AssertionError('PostgreSQL/SQLite result mismatch: '+n)
  quality['postgres_parity']='All three analytical views match SQLite exactly'
 dump(ROOT/'reports/data_quality.json',quality)
 digest=sha(json.dumps(results,sort_keys=True).encode())
 report=dict(completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),seconds=round(time.perf_counter()-start,3),analytical_sha256=digest,rows=len(rows),postgres_verified=bool(dsn))
 dump(ROOT/'reports/run.json',report);db.close();return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--refresh',action='store_true');p.add_argument('--dsn',default=os.getenv('DATABASE_URL'));a=p.parse_args()
 if a.refresh:download()
 print(json.dumps(run(a.dsn),indent=2))
