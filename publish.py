"""Build portable dashboard, preview and decision brief from analytical exports."""
import csv,json,os
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/pei-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from pipeline import ROOT

def read(n):
 with (ROOT/'data/processed'/f'{n}.csv').open() as f:return [{k:None if v=='' else v if k=='geo' else float(v) for k,v in r.items()} for r in csv.DictReader(f)]
def build():
 a=read('annual_supply');r=read('rental_trends');s=read('household_scenarios');q=json.loads((ROOT/'reports/data_quality.json').read_text());manifest=json.loads((ROOT/'data/raw/manifest.json').read_text())
 latest=[x for x in r if x['year']==max(y['year'] for y in r)];ch=next(x for x in latest if x['geo'].startswith('Charlottetown'));su=next(x for x in latest if x['geo'].startswith('Summerside'))
 plt.rcParams.update({'font.family':'DejaVu Sans','axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','figure.facecolor':'#f7f5ef','axes.facecolor':'#ffffff'})
 fig,axs=plt.subplots(2,2,figsize=(15,9));fig.subplots_adjust(top=.85,bottom=.15,wspace=.22,hspace=.48)
 fig.suptitle('PEI HOUSING PRESSURE MONITOR',x=.07,ha='left',fontsize=23,fontweight='bold',color='#173c37')
 fig.text(.07,.91,'Official statistics • Province-wide supply context + separate urban rental signals',fontsize=11,color='#52645f')
 xs=[int(x['year']) for x in a];axs[0,0].plot(xs,[x['population_change'] for x in a],color='#b36139',marker='o');axs[0,0].set_title('01  Population added | PEI, Jan 1 to Jan 1',loc='left',fontsize=11);axs[0,0].set_ylabel('Persons')
 for field,label,color in [('starts','Starts','#267269'),('completions','Completions','#bd783e')]:axs[0,1].plot(xs,[x[field] for x in a],marker='o',label=label,color=color)
 axs[0,1].set_title('02  New homes | PEI, calendar year',loc='left',fontsize=11);axs[0,1].set_ylabel('Units');axs[0,1].legend(frameon=False);axs[0,1].text(.02,.95,'Completions coverage ends 2022',transform=axs[0,1].transAxes,va='top',fontsize=9)
 for geo,color in [('Charlottetown survey area','#267269'),('Summerside survey area','#b36139')]:
  rr=[x for x in r if x['geo']==geo];axs[1,0].plot([x['year'] for x in rr],[x['rent_2br'] for x in rr],marker='o',label=geo.replace(' survey area',''),color=color);axs[1,1].plot([x['year'] for x in rr],[x['vacancy_pct'] for x in rr],marker='o',label=geo.replace(' survey area',''),color=color)
 axs[1,0].set_title('03  Two-bedroom average observed rent',loc='left',fontsize=11);axs[1,0].set_ylabel('Nominal CAD/month');axs[1,1].set_title('04  Rental vacancy | October survey',loc='left',fontsize=11);axs[1,1].set_ylabel('Percent of surveyed units')
 for ax in axs.flat:ax.grid(axis='y',alpha=.18);ax.tick_params(labelsize=9)
 axs[1,0].legend(frameon=False,fontsize=9);axs[1,1].legend(frameon=False,fontsize=9)
 fig.text(.07,.06,'Rental universe: privately initiated row/apartment structures of 3+ units; survey areas, not municipal boundaries.\nNo rural rental estimate. Average rents are not asking rents. No causal population effect or measured housing deficit.',fontsize=10,color='#52645f')
 fig.savefig(ROOT/'reports/dashboard.png',dpi=150);plt.close(fig)
 findings=[f"2025 surveyed two-bedroom average rent: Charlottetown ${ch['rent_2br']:,.0f}; Summerside ${su['rent_2br']:,.0f} per month.",f"2025 rental vacancy: Charlottetown {ch['vacancy_pct']:.1f}%; Summerside {su['vacancy_pct']:.1f}%. These describe covered rental structures, not all housing.","The selected completions series ends in 2022. The monitor explicitly blocks a current supply-balance conclusion."]
 brief_sections=[('What the data shows',' '.join(findings)),('Where to investigate','Prioritize a review of rental availability and rent composition in the Charlottetown survey area, where the selected 2025 vacancy measure is lower. Ask whether changes reflect new units, different unit quality, or existing-tenancy changes before calling them rent inflation.'),('Next decision','Obtain and reconcile the current CMHC provincial completions series before using the monitor for a 2023-2025 supply assessment. Collect household formation, demolitions/conversions and vacancy-universe evidence before estimating unmet housing need.'),('What the data cannot establish','Population growth is not household growth. Scenarios divide annual population change by assumed household sizes of 2.0, 2.5 or 3.0 and subtract completions only for years where both exist. The resulting balance is illustrative, not an official shortage, projection or causal estimate. No scenario after 2022 is reported. Provincial figures are never joined to urban rental observations as if they share geography.'),('Sources and coverage','Statistics Canada / CMHC: 17-10-0009-01 (population); 34-10-0126-01 (annual supply); 34-10-0133-01 (rent); 34-10-0131-01 and 34-10-0132-01 (vacancy). Rental data through 2025; starts through 2025; population through July 2026; completions through 2022. Full source URLs, retrieval times and SHA-256 hashes: data/raw/manifest.json.')]
 styles=getSampleStyleSheet();styles['Normal'].fontSize=10;styles['Normal'].leading=14;styles['Heading2'].fontSize=12;styles['Heading2'].textColor=colors.HexColor('#267269')
 story=[Paragraph('PEI Housing Pressure Monitor',styles['Title']),Paragraph('DECISION BRIEF | Descriptive evidence, with explicit coverage limits',styles['Normal']),Spacer(1,10)]
 for title,text in brief_sections:story.extend([Paragraph(title,styles['Heading2']),Paragraph(text,styles['Normal'])])
 SimpleDocTemplate(str(ROOT/'reports/decision_brief.pdf'),pagesize=(612,792),rightMargin=44,leftMargin=44,topMargin=35,bottomMargin=30).build(story)
 (ROOT/'reports/decision_brief.md').write_text('# PEI Housing Pressure Monitor\n\n'+'\n\n'.join('## '+t+'\n'+v for t,v in brief_sections)+'\n')
 (ROOT/'reports/data_quality.md').write_text('# Data quality report\n\n'+f"Selected observations: {q['selected_records']}; duplicate vector/period keys: {q['duplicate_keys']}; unavailable selected observations: {len(q['unavailable_observations'])}.\n\n"+'\n'.join('- '+x for x in q['warnings'])+'\n\n## Coverage\n'+json.dumps(q['coverage'],indent=2)+'\n\nFull machine-readable evidence: data_quality.json. Missing values remain NULL; no imputation. Out-of-scope records are filtered, not labelled invalid.\n')
 data=json.dumps(dict(annual=a,rental=r,scenarios=s,sources=manifest))
 template=(ROOT/'docs/dashboard_template.html').read_text();(ROOT/'dashboard.html').write_text(template.replace('__DATA__',data));return findings
if __name__=='__main__':print('\n'.join(build()))
