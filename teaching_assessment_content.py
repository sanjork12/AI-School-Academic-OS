"""Original teacher/demo content. No stable pipeline imports or external calls."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output/teaching_assessment_demo'
NOTICE = 'Teacher-generated teaching/practice material. Not official Pearson material.'
SCHEME_NOTICE = 'TEACHER-GENERATED PRACTICE MARK SCHEME — NOT AN OFFICIAL PEARSON MARK SCHEME'
ILLUSTRATIVE = 'ILLUSTRATIVE DATA — invented for practice, not Pearson LDS observations.'
GUIDE = 'https://qualifications.pearson.com/content/dam/pdf/A%20Level/Mathematics/2017/Teaching%20and%20learning%20materials/gce-maths-assessment-guide.pdf'
REPORT = 'https://qualifications.pearson.com/content/dam/pdf/A-Level/Mathematics/2017/Exam-materials/9ma0-31-pef-20230817.pdf'
PAGE = 'https://qualifications.pearson.com/en/qualifications/edexcel-a-levels/mathematics-2017.html'

def cid(key):
    return 'GROUP-LDS-PURPOSE' if key == 'PURPOSE' else 'CAN-STAT-' + key

COMPETENCIES = [
 ('TYPE-CLASSIFY','Classify qualitative, discrete and continuous data','data_types'),
 ('GROUPED-INTERPRET','Interpret grouped and ungrouped data','data_types'),
 ('VARIABLE-INTERPRET','Interpret variables and units in context','data_types'),
 ('MEAN-CALCULATE','Calculate and interpret a mean','location'),
 ('MEDIAN-CALCULATE','Calculate and interpret a median','location'),
 ('MODE-IDENTIFY','Identify a mode or modal class','location'),
 ('QUANTILE-DETERMINE','Determine and interpret quartiles and percentiles','location'),
 ('LOCATION-SELECT','Select an appropriate measure of location','location'),
 ('RANGE-CALCULATE','Calculate and interpret range','spread'),
 ('IQR-CALCULATE','Calculate and interpret interquartile range','spread'),
 ('VARIANCE-INTERPRET','Calculate and interpret descriptive variance','spread'),
 ('SD-CALCULATE','Calculate descriptive standard deviation','spread'),
 ('SD-INTERPRET','Interpret standard deviation in context','spread'),
 ('DISTRIBUTION-COMPARE','Compare distributions using location and spread','comparison'),
 ('OUTLIER-INTERPRET','Identify and interpret unusual observations','comparison'),
 ('PURPOSE','Purpose and structure of the Pearson Large Data Set','lds'),
 ('LIMITATIONS-EVALUATE','Evaluate data limitations and cleaning decisions','lds'),
 ('CONTEXT-CONCLUDE','Draw qualified contextual conclusions from data','lds'),
]

def part(q, letter, marks, primary, prompt, answer, points, *, supporting=(), demand=2, reasoning=None, alternatives='Accept equivalent correct reasoning.', interpretation='Use the context and units stated in the question.'):
    return dict(part_id=f'{q}({letter})', marks=marks, primary_competency=cid(primary),
                supporting_competencies=[cid(s) for s in supporting], prompt=prompt,
                predicted_difficulty=demand, difficulty_basis='Teacher estimate of task demand, 1 easiest to 5 hardest; not empirically calibrated.',
                reasoning_steps=reasoning or [point[3:] for point in points],
                answer=answer, marking_points=points, acceptable_alternatives=alternatives,
                interpretation_requirements=interpretation)

def question(identifier, title, context, purpose, parts, data=None):
    return dict(question_id=identifier, title=title, context=context, question_purpose=purpose,
                question_format='Original multi-part written practice', provenance='teacher_generated',
                data_provenance='synthetic_illustrative', notice=NOTICE, data_notice=ILLUSTRATIVE,
                data=data or [], parts=parts)

def questions():
    return [
      question('Q1','Variables in a travel survey',
       'A college records travel mode, number of bus changes and journey time in minutes for each student. Journey time is rounded to the nearest minute.',
       'Classify variables and explain what grouping loses.',[
        part('Q1','a',2,'TYPE-CLASSIFY','Classify travel mode and number of bus changes. Use qualitative, quantitative discrete or quantitative continuous as appropriate.',
             'Travel mode: qualitative. Number of bus changes: quantitative discrete.', ['B1 qualitative travel mode','B1 quantitative discrete bus changes'],demand=1),
        part('Q1','b',2,'VARIABLE-INTERPRET','State the underlying type of journey time and explain why rounding does not change that type.',
             'Quantitative continuous. Time can take any value in an interval; rounding only changes recording precision.', ['B1 quantitative continuous','B1 distinguishes underlying measurement from rounding'],supporting=['TYPE-CLASSIFY']),
        part('Q1','c',2,'GROUPED-INTERPRET','The college replaces individual times with counts in 0 <= t < 10, 10 <= t < 20, and so on. State what the counts represent and one piece of information that is lost.',
             'Each count is the frequency in an interval. Exact individual journey times are lost.', ['B1 frequency in each interval','B1 exact individual times lost'])]),
      question('Q2','Choosing a typical waiting time',
       'The waiting times, in minutes, of seven customers are shown. Treat them as the complete set of observations.',
       'Calculate location and choose a robust summary.',[
        part('Q2','a',2,'MEAN-CALCULATE','Calculate the mean waiting time.', '77/7 = 11 minutes.', ['M1 sum 77 divided by 7','A1 11 minutes']),
        part('Q2','b',2,'MEDIAN-CALCULATE','Find the median and interpret it for these customers.', 'Median = 8 minutes. At least half waited no more than 8 minutes and at least half no less.', ['B1 median 8','B1 correct contextual interpretation']),
        part('Q2','c',2,'LOCATION-SELECT','Choose the mean or median to describe a typical wait. Justify your choice using the data.', 'Median: the 30-minute wait pulls the mean upwards; the median resists this extreme value.', ['B1 median','B1 justification referring to 30 minutes and influence on mean'],supporting=['OUTLIER-INTERPRET'],demand=3)
       ], [['Waiting time (minutes)','4, 6, 7, 8, 9, 13, 30']]),
      question('Q3','Grouped download times',
       'A technician groups the download times t, in seconds, for 40 files. Use class midpoints for the estimated mean. Use position 0.75n and linear interpolation for the 75th percentile.',
       'Estimate summaries from grouped data and explain their meaning.',[
        part('Q3','a',3,'MEAN-CALCULATE','Estimate the mean download time. Explain why your answer is an estimate.', 'Midpoints 5, 15, 25. Sum fm = 600, n = 40. Estimated mean = 15 seconds. Actual within-class values are unknown.', ['M1 correct weighted midpoint sum divided by 40','A1 15 seconds','B1 midpoint/unknown within-class values explanation'],supporting=['GROUPED-INTERPRET'],demand=3),
        part('Q3','b',2,'QUANTILE-DETERMINE','Estimate the 75th percentile and interpret it.', 'Position 30 lies at the top of the second class. 10 + ((30 - 10)/20) x 10 = 20 seconds. Approximately 75% take no more than 20 seconds.', ['M1 interpolation or correct cumulative-frequency boundary giving 20','B1 interpretation of 75% in context'],supporting=['GROUPED-INTERPRET'],demand=3)
       ],[['Time t (seconds)','Frequency'],['0 <= t < 10','10'],['10 <= t < 20','20'],['20 <= t < 30','10']]),
      question('Q4','Quartiles and an unusual value',
       'Twelve packet delivery times in minutes are ordered below. Define Q1 and Q3 as the medians of the lower six and upper six values. Use the rule: an outlier lies below Q1 - 1.5 IQR or above Q3 + 1.5 IQR.',
       'Calculate spread and apply an explicitly specified outlier rule.',[
        part('Q4','a',1,'RANGE-CALCULATE','Find the range.', '31 - 5 = 26 minutes.', ['B1 26 minutes']),
        part('Q4','b',2,'IQR-CALCULATE','Find Q1, Q3 and the interquartile range.', 'Q1 = (7 + 8)/2 = 7.5; Q3 = (16 + 17)/2 = 16.5. IQR = 9 minutes.', ['B1 both quartiles correct','A1 IQR 9 minutes'],supporting=['QUANTILE-DETERMINE']),
        part('Q4','c',2,'OUTLIER-INTERPRET','Decide whether 31 minutes is an outlier. State whether this alone justifies deleting it.', 'Upper fence = 16.5 + 1.5 x 9 = 30. Since 31 > 30 it is flagged. No: investigate whether it is an error or a genuine delay.', ['B1 fence 30 and 31 correctly flagged','B1 investigate rather than automatically delete'],supporting=['IQR-CALCULATE','LIMITATIONS-EVALUATE'],demand=3)
       ],[['Delivery time (minutes)','5, 6, 7, 8, 10, 11, 13, 14, 16, 17, 19, 31']]),
      question('Q5','Two bus routes',
       'A student samples 30 comparable weekday journeys on each of two routes. The table summarises journey times in minutes.',
       'Use both location and variation to make a contextual comparison.',[
        part('Q5','a',2,'DISTRIBUTION-COMPARE','Compare the typical journey time and consistency of the two routes, using the statistics.', 'Route A is typically quicker (median 24 vs 28 minutes), but B is more consistent in its middle half (IQR 4 vs 10 minutes).', ['B1 contextual median comparison with values','B1 contextual IQR comparison with values'],supporting=['MEDIAN-CALCULATE','IQR-CALCULATE']),
        part('Q5','b',2,'DISTRIBUTION-COMPARE','A student says: "Every journey on A will be quicker than every journey on B." Explain why the summaries do not justify this claim.', 'Medians and IQRs summarise parts of the distributions, not all individual times. The distributions may overlap, so an A journey may take longer than a B journey.', ['B1 summaries do not give all values/extremes','B1 possible overlap or contextual counterexample'],supporting=['CONTEXT-CONCLUDE'],demand=3)
       ],[['Route','Median (minutes)','IQR (minutes)'],['A','24','10'],['B','28','4']]),
      question('Q6','Variation in machine filling',
       'For eight measured fill volumes x in millilitres, n = 8, sum x = 400 and sum x^2 = 20072. Describe these eight observations using divisor n, not n - 1.',
       'Connect summary statistics, variance, standard deviation and units.',[
        part('Q6','a',3,'VARIANCE-INTERPRET','Calculate the variance of the eight fill volumes and give its units.', 'Mean = 50 ml. Variance = 20072/8 - 50^2 = 9 ml^2.', ['M1 correct variance expression with divisor 8','A1 value 9','B1 squared units ml^2'],supporting=['MEAN-CALCULATE'],demand=3),
        part('Q6','b',2,'SD-CALCULATE','Calculate the standard deviation and give its units.', 'sqrt(9) = 3 ml.', ['M1 square root of variance','A1 3 ml'],supporting=['VARIANCE-INTERPRET'],alternatives='Allow M1 for square root of their non-negative variance; A1 requires 3 ml.'),
        part('Q6','c',3,'SD-INTERPRET','A second machine has mean 50 ml and standard deviation 1.2 ml for a comparable set of fills. Compare the two machines, and explain why standard deviation 3 ml does not mean every fill is between 47 and 53 ml.', 'Both average 50 ml. The second machine has less variation around its mean (1.2 < 3). SD describes overall variation, not a bound on individual values.', ['B1 same mean in context','B1 second machine less variable with SD evidence','B1 SD is not a maximum deviation or guarantee'],supporting=['DISTRIBUTION-COMPARE'],demand=4)
       ]),
      question('Q7','Weather records and missing values',
       'ILLUSTRATIVE DATA: these invented values are not Pearson LDS observations. Daily rainfall at fictional Station P over six scheduled days is 0, 1.2, tr, 0, 4.8, missing (mm). Here tr means 0 < rainfall < 0.05 mm. For this calculation replace tr by 0. Station R has a reported mean of 0.8 mm over six complete days in a different month.',
       'Analyse weather data with an explicit cleaning policy and qualified conclusions.',[
        part('Q7','a',2,'CONTEXT-CONCLUDE','Explain what one observation represents and state the unit.', 'The total rainfall at Station P over one day, measured in millimetres.', ['B1 one day at one station','B1 rainfall in millimetres'],supporting=['VARIABLE-INTERPRET']),
        part('Q7','b',3,'LIMITATIONS-EVALUATE','Estimate the mean rainfall for the available days at P using the stated rule. Explain why you do not divide by six.', '(0 + 1.2 + 0 + 0 + 4.8)/5 = 1.2 mm. Five recorded days remain; missing is not an observed zero.', ['M1 sum 6.0 divided by 5','A1 1.2 mm','B1 missing day cannot be treated as zero'],supporting=['MEAN-CALCULATE'],demand=4),
        part('Q7','c',4,'CONTEXT-CONCLUDE','A researcher concludes that P has a wetter climate than R. Give the limited comparison supported by the means, then explain three distinct reasons why this climate claim is not justified.', 'For the available observations P has higher mean daily rainfall (1.2 vs 0.8 mm). Only a few days are represented; different months may have seasonal effects; the missing day at P may bias its mean. This does not establish a climate difference.', ['B1 limited comparison using means','B1 very small/short sample','B1 different months/seasonality','B1 missing value could bias result'],supporting=['LIMITATIONS-EVALUATE','DISTRIBUTION-COMPARE'],demand=5,
             alternatives='Accept distinct valid limitations tied to the setup; do not credit the same limitation twice.')
       ]),
      question('Q8','A mean changes after inspection',
       'In a second delivery study, 10 recorded times have mean 18 minutes. One time is 54 minutes. A comparable service has mean 15 minutes. The analyst proposes removing 54 because it makes the first service look slow.',
       'Combine an updated mean with an evaluation of an unjustified conclusion.',[
        part('Q8','a',3,'DISTRIBUTION-COMPARE','Calculate the mean of the remaining nine times if 54 is removed. Compare it with 15 minutes.', '(10 x 18 - 54)/9 = 14 minutes. The remaining nine average 1 minute less than the other service, reversing the original comparison (18 > 15).', ['M1 reconstruct total 180 and subtract 54','A1 remaining mean 14','B1 correct contextual comparison with 15'],supporting=['MEAN-CALCULATE','OUTLIER-INTERPRET'],demand=4),
        part('Q8','b',2,'DISTRIBUTION-COMPARE','Evaluate the proposed removal and the claim that the first service is generally faster.', 'Removal to improve the result is unjustified: verify whether 54 is an error or genuine delay. A changed sample mean alone does not establish that the service is generally faster; compare representative samples and variation.', ['B1 valid data-quality reason needed for removal','B1 qualified conclusion with variation/representativeness limitation'],supporting=['LIMITATIONS-EVALUATE','CONTEXT-CONCLUDE'],demand=5)
       ])
    ]

# Each slide has a short explanation, worked material and a student check.
def slide(n,title,keys,lines,check,answer,example=None,table=None,notes='',chart=None):
    return dict(slide_id=n,title=title,competency_ids=[cid(k) for k in keys],body=lines,
                student_check=dict(practice_id=f'CHECK-{n:02}',prompt=check,answer=answer),
                worked_example_id=example,table=table or [],chart=chart,
                speaker_notes=notes,provenance='teacher_generated',data_notice=ILLUSTRATIVE)

def slides():
    return [
      slide(1,'Exploring and summarising data',[],['Pearson Edexcel A Level Mathematics (9MA0)','Statistics / Applied Mathematics','Teacher-generated teaching and practice material','Not official Pearson material'], 'What makes a statistical summary useful?', 'It describes a defined dataset in its context.',notes='Unit plan: two 55-minute teaching lessons, then a separate 55-minute assessment. Calculators needed. Slides 1–14 in lesson 1, 15–24 in lesson 2. All numeric teaching datasets are invented.'),
      slide(2,'Learning objectives',[],['Choose summaries that answer a contextual question.','Calculate location and variation, including grouped estimates.','Compare distributions and explain limitations.','Interpret weather records without overstating conclusions.'],'Which matters more: a correct number or a justified conclusion?','Both: the method must be correct and the conclusion supported.'),
      slide(3,'Statistics within 9MA0',['PURPOSE','CONTEXT-CONCLUDE'],['This unit develops data interpretation for Statistics.','The wider course also includes probability and inference.','Our focus: describing observations before making claims.'],'Does a difference between two sample means prove a population difference?','No. Sampling and variability matter.',notes='Qualification context: '+PAGE+'. LDS teaching role: '+GUIDE+' p9. This unit is a teacher-selected subset, not a complete specification coverage claim.'),
      slide(4,'Data types in context',['TYPE-CLASSIFY','VARIABLE-INTERPRET'],['Qualitative: labels or categories.','Discrete quantitative: counts or separate possible values.','Continuous quantitative: measurements on an interval.'],'A temperature recorded to 0.1 °C: discrete or continuous?','Underlying temperature is continuous. Recording precision does not change that.',example='A',table=[['Variable','Classification'],['Transport mode','Qualitative'],['Number of delays','Quantitative discrete'],['Delay duration (minutes)','Quantitative continuous']]),
      slide(5,'Grouping measurements',['GROUPED-INTERPRET','VARIABLE-INTERPRET'],['Grouping makes patterns easier to see.','Exact values within each class are lost.','Use midpoints only when an estimate is appropriate.'],'Can the exact mean be recovered from this table?','No. Different within-class observations can have the same frequencies.',table=[['Time t (seconds)','Frequency','Midpoint'],['0 ≤ t < 10','4','5'],['10 ≤ t < 20','8','15'],['20 ≤ t < 30','4','25']]),
      slide(6,'Mean, median and a long delay',['MEAN-CALCULATE','MEDIAN-CALCULATE','LOCATION-SELECT'],['Waits (minutes): 3, 5, 6, 7, 9, 12, 28','Mean = 70 ÷ 7 = 10 minutes','Median = 7 minutes','The long wait pulls the mean above the median.'],'If 28 becomes 42, which summary stays fixed?','Median stays 7; mean becomes 84/7 = 12 minutes.',example='B',notes='Original worked example B. Sort first. Interpret mean as total waiting time shared equally, not the most common wait. Median is resistant to the extreme observation.'),
      slide(7,'Frequency summaries',['MEAN-CALCULATE','MODE-IDENTIFY','GROUPED-INTERPRET'],['Estimated mean = Σfm / Σf','Using slide 5: (4×5 + 8×15 + 4×25) / 16 = 15 s','Modal class: 10 ≤ t < 20 seconds','A modal class is an interval, not an exact mode.'],'For 2, 2, 3, 4, what is the mode?','2. A raw mode is the most frequent value.'),
      slide(8,'Quartiles and percentiles',['QUANTILE-DETERMINE','GROUPED-INTERPRET'],['A percentile locates a point in an ordered distribution.','Grouped estimate: L + [(pn − F) / f] × w','L: lower boundary; F: cumulative frequency before class','f: class frequency; w: width; p: desired fraction'],'Using slide 5, estimate the 75th percentile with p = 0.75.','Position 12: 10 + ((12−4)/8)×10 = 20 seconds.',notes='Assume observations spread uniformly within the relevant class. About 75% are at or below the 75th percentile. For raw quartiles use the convention stated in the question; software conventions differ. This interpolation is teacher-selected practice.'),
      slide(9,'Range and the middle half',['RANGE-CALCULATE','IQR-CALCULATE','QUANTILE-DETERMINE'],['Ordered minutes: 2, 4, 5, 7, 8, 10, 11, 13','Use medians of the two halves in this example.','Q1 = 4.5; Q3 = 10.5; IQR = 6 minutes','Range = 13 − 2 = 11 minutes'],'If 13 becomes 30, what happens to range and IQR?','Range becomes 28; IQR stays 6 for this dataset.',example='C',notes='Example C: lower half 2,4,5,7; upper half 8,10,11,13. IQR describes the spread of the central half and is less sensitive to extremes.'),
      slide(10,'Variance and standard deviation',['VARIANCE-INTERPRET','SD-CALCULATE'],['Variance = Σ(x − mean)² / n = Σx²/n − mean²','Standard deviation σ = √variance','Use divisor n to describe the observed dataset.','Variance uses squared units; SD uses original units.'],'For values 2, 4, 6 cm, find variance and SD.','Mean 4; variance 8/3 cm²; SD ≈ 1.63 cm.',notes='Use calculator population SD (often σx), not sample estimate sx, for these tasks. Variance averages squared deviations. SD is their root mean square, not a maximum distance. No normal model is assumed.'),
      slide(11,'Interpreting standard deviation',['SD-INTERPRET','DISTRIBUTION-COMPARE'],['Two fillers both average 200 ml.','Filler A: SD 2 ml. Filler B: SD 7 ml.','A has less variation around its mean.','Neither SD guarantees a limit for every fill.'],'Does B necessarily have a lower mean?','No. Both means are 200 ml.',example='E',chart={'categories':['Filler A','Filler B'],'series':[{'name':'SD (ml)','values':[2,7]}]},notes='Example E. Chart compares standard deviations, not individual fills. No claim about defect rates follows without a distribution and specification limits.'),
      slide(12,'Comparing two distributions',['DISTRIBUTION-COMPARE','CONTEXT-CONCLUDE'],['Compare location AND variation in the same units.','Service A is typically faster by its median.','Service B has less variation in its central half.'],'Which service would you choose, and what is the trade-off?','A for lower typical time; B for greater central consistency. Explain the priority.',example='D',table=[['Delivery time','Median (min)','IQR (min)'],['Service A','18','8'],['Service B','22','3']]),
      slide(13,'A comparison needs a context',['DISTRIBUTION-COMPARE','LIMITATIONS-EVALUATE'],['“A is better” leaves the criterion undefined.','“A has a lower median delivery time” names it.','Comparable routes, dates and sample sizes matter.','Summary statistics alone do not show every value.'],'Can a lower median guarantee every delivery is faster?','No. The distributions can overlap.',notes='Ask students to improve an unsupported claim. Discuss observational comparison, representativeness and missing extremes without introducing formal hypothesis testing.'),
      slide(14,'Outliers and choice of summary',['OUTLIER-INTERPRET','LOCATION-SELECT'],['For this rule: below Q1 − 1.5 IQR or above Q3 + 1.5 IQR.','If Q1 = 8 and Q3 = 14, fences are −1 and 23.','A value of 25 is flagged for investigation.','Median and IQR resist extreme values better than mean and SD.'],'Should a flagged value always be deleted?','No. A genuine unusual observation is evidence, not automatically an error.',example='J',notes='Do not imply this rule is the only possible definition. Follow the rule given in an assessment. Check data provenance and measurement errors before exclusion.'),
      slide(15,'The Pearson Large Data Set',['PURPOSE','LIMITATIONS-EVALUATE'],['Met Office weather observations for eight stations.','May to October in 1987 and 2015.','UK: Camborne, Heathrow, Hurn, Leeming, Leuchars.','Overseas: Beijing, Jacksonville, Perth.'],'Why are these observations not a random sample of every day worldwide?','They cover selected places, months and years.',notes='OFFICIAL-SOURCE-DERIVED FACTS, paraphrased: '+GUIDE+' p9. Students should work with real data, clean it and calculate summaries. No official numerical observations are reproduced in this pack.'),
      slide(16,'Variables, units and observations',['VARIABLE-INTERPRET','PURPOSE'],['One row relates to a particular station and day.','Check the workbook column heading and unit.','Availability of variables differs between locations.'],'Would a rainfall mean in mm be comparable with a windspeed mean in knots?','No. They measure different quantities.',table=[['Weather quantity','Unit to check'],['Daily mean air temperature','°C'],['Daily total rainfall','mm'],['Daily mean windspeed','knots']],notes='Context: '+GUIDE+' p9. Units and interpretation are teacher explanations. Consult the real workbook before analysing a column. Do not assume every overseas station has every UK variable.'),
      slide(17,'Missing, trace and unusual records',['LIMITATIONS-EVALUATE','CONTEXT-CONCLUDE'],['Missing values need a documented policy; missing is not zero.','For rainfall, “tr” represents a very small recorded amount.','A trace convention is an approximation, not a missing value.','Check season, station and units before comparing.'],'What should a report state after excluding a missing record?','The number of valid records, exclusion rule and possible bias.',notes='Pearson 2023 examiner report Q3 discusses trace rainfall below 0.05 mm and the May–October limitation: '+REPORT+'. For our invented example F and Q7 explicitly use 0 for trace. Other defensible approximations may be discussed when no rule is specified.'),
      slide(18,'Grouped estimates in an application',['MEAN-CALCULATE','QUANTILE-DETERMINE','GROUPED-INTERPRET'],['A queue study records 20 waiting times.','Estimated mean = (6×5 + 10×15 + 4×25)/20 = 14 min','Estimated median = 10 + [(10−6)/10]×10 = 14 min','Both estimates assume representative within-class values.'],'Estimate the 75th percentile using position 15.','10 + ((15−6)/10)×10 = 19 minutes.',example='G',table=[['Wait (min)','Frequency'],['0 ≤ t < 10','6'],['10 ≤ t < 20','10'],['20 ≤ t < 30','4']],notes='Example G. The same estimated mean and median here does not prove symmetry. Percentile interpolation assumes uniform within-class distribution.'),
      slide(19,'SD from summary statistics',['SD-CALCULATE','VARIANCE-INTERPRET','MEAN-CALCULATE'],['For six journey times: Σx = 90, Σx² = 1416','Mean = 90/6 = 15 minutes','Variance = 1416/6 − 15² = 11 min²','SD = √11 ≈ 3.32 minutes'],'If all times increase by 4 minutes, how do mean and SD change?','Mean becomes 19 minutes. SD is unchanged.',example='H',notes='Example H. Keep unrounded mean in the calculation. Calculator σx describes these observations. Translation moves every value and the mean equally, so deviations are unchanged.'),
      slide(20,'Weather analysis with a cleaning rule',['LIMITATIONS-EVALUATE','MEAN-CALCULATE','CONTEXT-CONCLUDE'],['ILLUSTRATIVE DATA: invented weather observations','Rainfall (mm): 0, 2.4, tr, 0.6, missing','Use tr = 0 and exclude the missing entry.','Mean over four recorded days = 3.0/4 = 0.75 mm'],'Why would dividing by five be misleading?','It would treat the missing observation as zero rain.',example='F',notes='Example F. This is not Pearson LDS data. The trace substitution slightly understates the mean if trace is positive. State the retained sample size and do not generalise from four days to climate.'),
      slide(21,'Evidence behind a weather comparison',['CONTEXT-CONCLUDE','DISTRIBUTION-COMPARE','LIMITATIONS-EVALUATE'],['ILLUSTRATIVE DATA: invented station summaries','P: mean 0.75 mm; Q: mean 1.10 mm for recorded days','Q has higher mean rainfall in these records.','Different months or missing days could affect the comparison.'],'What further evidence would support a broader comparison?','Comparable longer periods, missing-data checks and measures of spread.',example='I',notes='Example I continues F. Q is a hypothetical summary, not an official station. Challenge “Q has a wetter climate” because the scope of the evidence is limited.'),
      slide(22,'Common mistakes',['SD-CALCULATE','GROUPED-INTERPRET','LIMITATIONS-EVALUATE'],['Dividing by number of classes instead of total frequency.','Using a rounded mean inside the variance calculation.','Reporting SD in squared units.','Treating missing rainfall as an observed zero.'],'A student calculates √(Σx²/n) − mean. What is wrong?','The mean must be squared and subtracted inside the square root.'),
      slide(23,'A written statistical argument',['DISTRIBUTION-COMPARE','CONTEXT-CONCLUDE'],['Name the variable and units.','Show the chosen method and retain working precision.','Support a contextual comparison with numerical evidence.','Limit the claim to what the data can justify.'],'Improve “The second set is more spread out.”','Name the variable and set, state the larger IQR or SD, and interpret variation.'),
      slide(24,'Retrieval and next steps',['MODE-IDENTIFY','SD-INTERPRET','OUTLIER-INTERPRET','PURPOSE'],['Which summary resists one extremely large value?','What is the mode of 1, 2, 2, 5?','Does a small SD mean a small mean?','What months and years appear in the Pearson LDS?'],'Explain one reason an illustrative weather exercise cannot replace working with the official LDS.','It does not expose the full real dataset, coding, variation and contextual details.',notes='Retrieval answers: median; 2; no; May–October 1987 and 2015. Homework: obtain the official workbook via Pearson course materials, inspect its guidance, choose a UK station and a month, identify units and missing codes. Calculate summaries with a documented cleaning policy. Do not label our invented observations as official data.')
    ]
