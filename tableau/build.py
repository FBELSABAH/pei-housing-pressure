"""Build a packaged Tableau workbook with a native Hyper extract and four views."""
import sys,csv,datetime,zipfile,uuid
from pathlib import Path
import xml.etree.ElementTree as E
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pipeline import ROOT
from tableauhyperapi import HyperProcess,Connection,TableDefinition,TableName,SqlType,CreateMode,Inserter,Telemetry
D=ROOT/'tableau/Data';D.mkdir(exist_ok=True)
rows=[]
for filename in ['annual_supply','rental_trends']:
 with (ROOT/'data/processed'/f'{filename}.csv').open() as f:
  for r in csv.DictReader(f):
   for metric in (['population_change','starts','completions'] if filename=='annual_supply' else ['rent_2br','vacancy_pct']):
    if r[metric]!='':rows.append([metric,r.get('geo','PEI'),str(int(float(r['year']))),float(r[metric])])
with (D/'metrics.csv').open('w',newline='') as f:w=csv.writer(f);w.writerow(['metric','area','year','value']);w.writerows(rows)
with HyperProcess(Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as h:
 with Connection(h.endpoint,str(D/'Housing.hyper'),CreateMode.CREATE_AND_REPLACE) as c:
  c.catalog.create_schema('Extract');td=TableDefinition(TableName('Extract','Extract'),[TableDefinition.Column('metric',SqlType.text()),TableDefinition.Column('area',SqlType.text()),TableDefinition.Column('year',SqlType.text()),TableDefinition.Column('value',SqlType.double())]);c.catalog.create_table(td)
  with Inserter(c,td) as i:i.add_rows(rows);i.execute()
def add(p,t,**a):return E.SubElement(p,t,{k.replace('_','-'):str(v) for k,v in a.items()})
r=E.Element('workbook',{'original-version':'18.1','source-build':'2025.1.0','source-platform':'mac','version':'18.1','xmlns:user':'http://www.tableausoftware.com/xml/user'})
manifest=add(r,'document-format-change-manifest');add(manifest,'SheetIdentifierTracking');add(manifest,'WindowsPersistSimpleIdentifiers')
add(r,'preferences');sources=add(r,'datasources');ds=add(sources,'datasource',caption='PEI | Official housing indicators',inline='true',name='housing',version='18.1')
c=add(ds,'connection',**{'class':'hyper','dbname':'Data/Housing.hyper','schema':'Extract','access_mode':'readonly'});add(c,'relation',name='Extract',table='[Extract].[Extract]',type='table')
for name in ['metric','area','year','value']:add(ds,'column',datatype='real' if name=='value' else 'string',name=f'[{name}]',role='measure' if name=='value' else 'dimension',type='quantitative' if name=='value' else 'ordinal' if name=='year' else 'nominal')
sheets=add(r,'worksheets');spec=[('1 | PEI population change','population_change'),('2 | PEI completions (ends 2022)','completions'),('3 | Average two-bedroom rent (CAD)','rent_2br'),('4 | Rental vacancy (%)','vacancy_pct')]
for title,metric in spec:
 sh=add(sheets,'worksheet',name=title);lo=add(sh,'layout-options');tt=add(lo,'title');ft=add(tt,'formatted-text');add(ft,'run',fontname='Arial',fontsize='12',bold='true').text=title
 table=add(sh,'table');v=add(table,'view');src=add(v,'datasources');add(src,'datasource',caption=ds.get('caption'),name='housing');dep=add(v,'datasource-dependencies',datasource='housing')
 for col in ds.findall('column'):dep.append(E.fromstring(E.tostring(col)))
 for name in ['metric','area','year','value']:add(dep,'column-instance',column=f'[{name}]',derivation='Sum' if name=='value' else 'None',name=f'[sum:value:qk]' if name=='value' else f'[none:{name}:ok]' if name=='year' else f'[none:{name}:nk]',pivot='key',type='quantitative' if name=='value' else 'ordinal' if name=='year' else 'nominal')
 filt=add(v,'filter',**{'class':'categorical','column':'[housing].[none:metric:nk]'});add(filt,'groupfilter',function='member',level='[none:metric:nk]',member='"'+metric+'"');add(v,'aggregation',value='true')
 st=add(table,'style');rule=add(st,'style-rule',element='mark');add(rule,'format',attr='mark-color',value='#267269')
 panes=add(table,'panes');pn=add(panes,'pane',selection_relaxation_option='selection-relaxation-allow');pv=add(pn,'view');add(pv,'breakdown',value='auto');add(pn,'mark',**{'class':'Line'});en=add(pn,'encodings');add(en,'color',column='[housing].[none:area:nk]');add(table,'rows').text='[housing].[sum:value:qk]';add(table,'cols').text='[housing].[none:year:ok]';add(sh,'simple-id',uuid='{'+str(uuid.uuid4()).upper()+'}')
dashboards=add(r,'dashboards');dash=add(dashboards,'dashboard',name='PEI Housing Pressure Monitor');add(dash,'style');add(dash,'size',maxheight='850',maxwidth='1200',minheight='850',minwidth='1200');zs=add(dash,'zones');base=add(zs,'zone',h='100000',w='100000',x='0',y='0',id='1',type_v2='layout-basic')
for i,(title,_) in enumerate(spec):add(base,'zone',id=i+3,name=title,x=1500+(i%2)*49000,y=14000+(i//2)*36000,w=47000,h=34000)
for zid,y,h,txt in [(2,500,12000,'PEI HOUSING PRESSURE MONITOR\nProvince-wide population/completions context; separate urban rental survey areas.'),(9,87500,12000,'Completions end 2022. Rental observations through 2025. Missing values are not zero.\nRent/vacancy: privately initiated row/apartment structures of 3+ units. No rural estimate or causal housing deficit.\nSource: Statistics Canada / CMHC. See methodology and source manifest in repository.')]:
 z=add(base,'zone',id=zid,x='1500',y=y,w='97000',h=h,type_v2='text');ft=add(z,'formatted-text');add(ft,'run',fontname='Arial',fontsize='11').text=txt;add(z,'zone-style')
add(base,'zone-style');add(dash,'simple-id',uuid='{'+str(uuid.uuid4()).upper()+'}');wins=add(r,'windows');win=add(wins,'window',**{'class':'dashboard','name':dash.get('name'),'maximized':'true'});vps=add(win,'viewpoints')
for title,_ in spec:vp=add(vps,'viewpoint',name=title);add(vp,'zoom',type='entire-view')
add(win,'active',id='-1');add(win,'simple-id',uuid='{'+str(uuid.uuid4()).upper()+'}')
E.indent(r);target=ROOT/'tableau/PEI_Housing.twb';E.ElementTree(r).write(target,encoding='utf-8',xml_declaration=True)
with zipfile.ZipFile(ROOT/'tableau/PEI_Housing.twbx','w',zipfile.ZIP_DEFLATED) as z:
 for p in [target,D/'Housing.hyper',D/'metrics.csv']:z.write(p,str(p.relative_to(ROOT/'tableau')))
print('Packaged Tableau workbook and Hyper extract:',len(rows),'marks')
