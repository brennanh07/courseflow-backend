import os
import sys
import django
import re

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# Configure Django settings before importing models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'class_scheduler.settings')
django.setup()

# Now we can import Django models
from scheduler.models import Subject


js_subject_code = """
document.ttform.subj_code.options[1]=new Option("AAD - Architecture, Arts, and Design","AAD",false, false);
document.ttform.subj_code.options[2]=new Option("AAEC - Agricultural and Applied Economics","AAEC",false, false);
document.ttform.subj_code.options[3]=new Option("ACIS - Accounting and Information Systems","ACIS",false, false);
document.ttform.subj_code.options[4]=new Option("ADV - Advertising","ADV",false, false);
document.ttform.subj_code.options[5]=new Option("AFST - Africana Studies","AFST",false, false);
document.ttform.subj_code.options[6]=new Option("AHRM - Apparel, Housing, and Resource Management","AHRM",false, false);
document.ttform.subj_code.options[7]=new Option("AINS - American Indian Studies","AINS",false, false);
document.ttform.subj_code.options[8]=new Option("AIS - Academy of Integrated Science","AIS",false, false);
document.ttform.subj_code.options[9]=new Option("ALCE - Agricultural, Leadership, and Community Education","ALCE",false, false);
document.ttform.subj_code.options[10]=new Option("ALS - Agriculture and Life Sciences","ALS",false, false);
document.ttform.subj_code.options[11]=new Option("AOE - Aerospace and Ocean Engineering","AOE",false, false);
document.ttform.subj_code.options[12]=new Option("APS - Appalachian Studies","APS",false, false);
document.ttform.subj_code.options[13]=new Option("APSC - Animal and Poultry Sciences","APSC",false, false);
document.ttform.subj_code.options[14]=new Option("ARBC - Arabic","ARBC",false, false);
document.ttform.subj_code.options[15]=new Option("ARCH - Architecture","ARCH",false, false);
document.ttform.subj_code.options[16]=new Option("ART - Art and Art History","ART",false, false);
document.ttform.subj_code.options[17]=new Option("AS - Military Aerospace Studies","AS",false, false);
document.ttform.subj_code.options[18]=new Option("ASPT - Alliance for Social, Political, Ethical, and Cultural Thought","ASPT",false, false);
document.ttform.subj_code.options[19]=new Option("AT - Agricultural Technology","AT",false, false);
document.ttform.subj_code.options[20]=new Option("BC - Building Construction","BC",false, false);
document.ttform.subj_code.options[21]=new Option("BCHM - Biochemistry","BCHM",false, false);
document.ttform.subj_code.options[22]=new Option("BDS - Behavioral Decision Science","BDS",false, false);
document.ttform.subj_code.options[23]=new Option("BIOL - Biological Sciences","BIOL",false, false);
document.ttform.subj_code.options[24]=new Option("BIT - Business Information Technology","BIT",false, false);
document.ttform.subj_code.options[25]=new Option("BMES - Biomedical Engineering and Sciences","BMES",false, false);
document.ttform.subj_code.options[26]=new Option("BMSP - Biomedical Sciences and Pathobiology","BMSP",false, false);
document.ttform.subj_code.options[27]=new Option("BMVS - Biomedical and Veterinary Sciences","BMVS",false, false);
document.ttform.subj_code.options[28]=new Option("BSE - Biological Systems Engineering","BSE",false, false);
document.ttform.subj_code.options[29]=new Option("CEE - Civil and Environmental Engineering","CEE",false, false);
document.ttform.subj_code.options[30]=new Option("CEM - Construction Engineering and Management","CEM",false, false);
document.ttform.subj_code.options[31]=new Option("CHE - Chemical Engineering","CHE",false, false);
document.ttform.subj_code.options[32]=new Option("CHEM - Chemistry","CHEM",false, false);
document.ttform.subj_code.options[33]=new Option("CHN - Chinese","CHN",false, false);
document.ttform.subj_code.options[34]=new Option("CINE - Cinema","CINE",false, false);
document.ttform.subj_code.options[35]=new Option("CLA - Classical Studies","CLA",false, false);
document.ttform.subj_code.options[36]=new Option("CMDA - Computational Modeling and Data Analytics","CMDA",false, false);
document.ttform.subj_code.options[37]=new Option("CMST - Communication Studies","CMST",false, false);
document.ttform.subj_code.options[38]=new Option("CNST - Construction","CNST",false, false);
document.ttform.subj_code.options[39]=new Option("COMM - Communication","COMM",false, false);
document.ttform.subj_code.options[40]=new Option("CONS - Consumer Studies","CONS",false, false);
document.ttform.subj_code.options[41]=new Option("COS - College of Science","COS",false, false);
document.ttform.subj_code.options[42]=new Option("CRIM - Criminology","CRIM",false, false);
document.ttform.subj_code.options[43]=new Option("CS - Computer Science","CS",false, false);
document.ttform.subj_code.options[44]=new Option("CSES - Crop and Soil Environmental Sciences","CSES",false, false);
document.ttform.subj_code.options[45]=new Option("DANC - Dance","DANC",false, false);
document.ttform.subj_code.options[46]=new Option("DASC - Dairy Science","DASC",false, false);
document.ttform.subj_code.options[47]=new Option("ECE - Electrical and Computer Engineering","ECE",false, false);
document.ttform.subj_code.options[48]=new Option("ECON - Economics","ECON",false, false);
document.ttform.subj_code.options[49]=new Option("EDCI - Education, Curriculum and Instruction","EDCI",false, false);
document.ttform.subj_code.options[50]=new Option("EDCO - Counselor Education","EDCO",false, false);
document.ttform.subj_code.options[51]=new Option("EDCT - Career and Technical Education","EDCT",false, false);
document.ttform.subj_code.options[52]=new Option("EDEL - Educational Leadership","EDEL",false, false);
document.ttform.subj_code.options[53]=new Option("EDEP - Educational Psychology","EDEP",false, false);
document.ttform.subj_code.options[54]=new Option("EDHE - Higher Education","EDHE",false, false);
document.ttform.subj_code.options[55]=new Option("EDIT - Instructional Design and Technology","EDIT",false, false);
document.ttform.subj_code.options[56]=new Option("EDP - Environmental Design and Planning","EDP",false, false);
document.ttform.subj_code.options[57]=new Option("EDRE - Education, Research and Evaluation","EDRE",false, false);
document.ttform.subj_code.options[58]=new Option("EDTE - Technology Education","EDTE",false, false);
document.ttform.subj_code.options[59]=new Option("ENGE - Engineering Education","ENGE",false, false);
document.ttform.subj_code.options[60]=new Option("ENGL - English","ENGL",false, false);
document.ttform.subj_code.options[61]=new Option("ENGR - Engineering","ENGR",false, false);
document.ttform.subj_code.options[62]=new Option("ENSC - Environmental Science","ENSC",false, false);
document.ttform.subj_code.options[63]=new Option("ENT - Entomology","ENT",false, false);
document.ttform.subj_code.options[64]=new Option("ESM - Engineering Science and Mechanics","ESM",false, false);
document.ttform.subj_code.options[65]=new Option("FA - Fine Arts","FA",false, false);
document.ttform.subj_code.options[66]=new Option("FIN - Finance","FIN",false, false);
document.ttform.subj_code.options[67]=new Option("FIW - Fish and Wildlife Conservation","FIW",false, false);
document.ttform.subj_code.options[68]=new Option("FL - Modern and Classical Languages and Literatures","FL",false, false);
document.ttform.subj_code.options[69]=new Option("FMD - Fashion Merchandising and Design","FMD",false, false);
document.ttform.subj_code.options[70]=new Option("FR - French","FR",false, false);
document.ttform.subj_code.options[71]=new Option("FREC - Forest Resources and Environmental Conservation","FREC",false, false);
document.ttform.subj_code.options[72]=new Option("FST - Food Science and Technology","FST",false, false);
document.ttform.subj_code.options[73]=new Option("GBCB - Genetics, Bioinformatics, Computational Biology","GBCB",false, false);
document.ttform.subj_code.options[74]=new Option("GEOG - Geography","GEOG",false, false);
document.ttform.subj_code.options[75]=new Option("GEOS - Geosciences","GEOS",false, false);
document.ttform.subj_code.options[76]=new Option("GER - German","GER",false, false);
document.ttform.subj_code.options[77]=new Option("GIA - Government and International Affairs","GIA",false, false);
document.ttform.subj_code.options[78]=new Option("GR - Greek","GR",false, false);
document.ttform.subj_code.options[79]=new Option("GRAD - Graduate School","GRAD",false, false);
document.ttform.subj_code.options[80]=new Option("HD - Human Development","HD",false, false);
document.ttform.subj_code.options[81]=new Option("HEB - Hebrew","HEB",false, false);
document.ttform.subj_code.options[82]=new Option("HIST - History","HIST",false, false);
document.ttform.subj_code.options[83]=new Option("HNFE - Human Nutrition, Foods and Exercise","HNFE",false, false);
document.ttform.subj_code.options[84]=new Option("HORT - Horticulture","HORT",false, false);
document.ttform.subj_code.options[85]=new Option("HTM - Hospitality and Tourism Management","HTM",false, false);
document.ttform.subj_code.options[86]=new Option("HUM - Humanities","HUM",false, false);
document.ttform.subj_code.options[87]=new Option("IDS - Industrial Design","IDS",false, false);
document.ttform.subj_code.options[88]=new Option("IS - International Studies","IS",false, false);
document.ttform.subj_code.options[89]=new Option("ISC - Integrated Science","ISC",false, false);
document.ttform.subj_code.options[90]=new Option("ISE - Industrial and Systems Engineering","ISE",false, false);
document.ttform.subj_code.options[91]=new Option("ITAL - Italian","ITAL",false, false);
document.ttform.subj_code.options[92]=new Option("ITDS - Interior Design","ITDS",false, false);
document.ttform.subj_code.options[93]=new Option("JMC - Journalism and Mass Communication","JMC",false, false);
document.ttform.subj_code.options[94]=new Option("JPN - Japanese","JPN",false, false);
document.ttform.subj_code.options[95]=new Option("JUD - Judaic Studies","JUD",false, false);
document.ttform.subj_code.options[96]=new Option("LAHS - Liberal Arts and Human Sciences","LAHS",false, false);
document.ttform.subj_code.options[97]=new Option("LAR - Landscape Architecture","LAR",false, false);
document.ttform.subj_code.options[98]=new Option("LAT - Latin","LAT",false, false);
document.ttform.subj_code.options[99]=new Option("LDRS - Leadership Studies","LDRS",false, false);
document.ttform.subj_code.options[100]=new Option("MACR - Macromolecular Science and Engineering","MACR",false, false);
document.ttform.subj_code.options[101]=new Option("MATH - Mathematics","MATH",false, false);
document.ttform.subj_code.options[102]=new Option("ME - Mechanical Engineering","ME",false, false);
document.ttform.subj_code.options[103]=new Option("MED - Medicine","MED",false, false);
document.ttform.subj_code.options[104]=new Option("MGT - Management","MGT",false, false);
document.ttform.subj_code.options[105]=new Option("MINE - Mining Engineering","MINE",false, false);
document.ttform.subj_code.options[106]=new Option("MKTG - Marketing","MKTG",false, false);
document.ttform.subj_code.options[107]=new Option("MN - Military Navy","MN",false, false);
document.ttform.subj_code.options[108]=new Option("MS - Military Science (AROTC)","MS",false, false);
document.ttform.subj_code.options[109]=new Option("MSE - Materials Science and Engineering","MSE",false, false);
document.ttform.subj_code.options[110]=new Option("MTRG - Meteorology","MTRG",false, false);
document.ttform.subj_code.options[111]=new Option("MUS - Music","MUS",false, false);
document.ttform.subj_code.options[112]=new Option("NANO - Nanoscience","NANO",false, false);
document.ttform.subj_code.options[113]=new Option("NEUR - Neuroscience","NEUR",false, false);
document.ttform.subj_code.options[114]=new Option("NR - Natural Resources","NR",false, false);
document.ttform.subj_code.options[115]=new Option("NSEG - Nuclear Science and Engineering","NSEG",false, false);
document.ttform.subj_code.options[116]=new Option("PAPA - Public Administration/Public Affairs","PAPA",false, false);
document.ttform.subj_code.options[117]=new Option("PHIL - Philosophy","PHIL",false, false);
document.ttform.subj_code.options[118]=new Option("PHS - Population Health Sciences","PHS",false, false);
document.ttform.subj_code.options[119]=new Option("PHYS - Physics","PHYS",false, false);
document.ttform.subj_code.options[120]=new Option("PM - Property Management","PM",false, false);
document.ttform.subj_code.options[121]=new Option("PORT - Portuguese","PORT",false, false);
document.ttform.subj_code.options[122]=new Option("PPE - Philosophy, Politics, and Economics","PPE",false, false);
document.ttform.subj_code.options[123]=new Option("PPWS - Plant Pathology, Physiology and Weed Science","PPWS",false, false);
document.ttform.subj_code.options[124]=new Option("PR - Public Relations","PR",false, false);
document.ttform.subj_code.options[125]=new Option("PSCI - Political Science","PSCI",false, false);
document.ttform.subj_code.options[126]=new Option("PSVP - Peace Studies","PSVP",false, false);
document.ttform.subj_code.options[127]=new Option("PSYC - Psychology","PSYC",false, false);
document.ttform.subj_code.options[128]=new Option("REAL - Real Estate","REAL",false, false);
document.ttform.subj_code.options[129]=new Option("RED - Residential Environments and Design","RED",false, false);
document.ttform.subj_code.options[130]=new Option("RLCL - Religion and Culture","RLCL",false, false);
document.ttform.subj_code.options[131]=new Option("RTM - Research in Translational Medicine","RTM",false, false);
document.ttform.subj_code.options[132]=new Option("RUS - Russian","RUS",false, false);
document.ttform.subj_code.options[133]=new Option("SBIO - Sustainable Biomaterials","SBIO",false, false);
document.ttform.subj_code.options[134]=new Option("SOC - Sociology","SOC",false, false);
document.ttform.subj_code.options[135]=new Option("SPAN - Spanish","SPAN",false, false);
document.ttform.subj_code.options[136]=new Option("SPES - School of Plant and Environmental Sciences","SPES",false, false);
document.ttform.subj_code.options[137]=new Option("SPIA - School of Public and International Affairs","SPIA",false, false);
document.ttform.subj_code.options[138]=new Option("STAT - Statistics","STAT",false, false);
document.ttform.subj_code.options[139]=new Option("STL - Science, Technology, & Law","STL",false, false);
document.ttform.subj_code.options[140]=new Option("STS - Science and Technology Studies","STS",false, false);
document.ttform.subj_code.options[141]=new Option("SYSB - Systems Biology","SYSB",false, false);
document.ttform.subj_code.options[142]=new Option("TA - Theatre Arts","TA",false, false);
document.ttform.subj_code.options[143]=new Option("TBMH - Translational Biology, Medicine and Health","TBMH",false, false);
document.ttform.subj_code.options[144]=new Option("UAP - Urban Affairs and Planning","UAP",false, false);
document.ttform.subj_code.options[145]=new Option("UH - University Honors","UH",false, false);
document.ttform.subj_code.options[146]=new Option("UNIV - University Course Series","UNIV",false, false);
document.ttform.subj_code.options[147]=new Option("VM - Veterinary Medicine","VM",false, false);
document.ttform.subj_code.options[148]=new Option("WATR - Water","WATR",false, false);
document.ttform.subj_code.options[149]=new Option("WGS - Women's and Gender Studies","WGS",false, false);
"""

def extract_subjects(input_string):
    pattern = r'new Option\("([^"]+)"\,"([^"]+)"'
    matches = re.findall(pattern, input_string)
    subjects = [{"abbreviation": match[1], "title": match[0]} for match in matches]
    return subjects


def insert_subjects(subjects):
    for subject in subjects:
        Subject.objects.create(abbreviation=subject["abbreviation"], title=subject["title"])

    
subjects = extract_subjects(js_subject_code)
insert_subjects(subjects)
