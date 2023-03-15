import json
from pprint import pprint
from datetime import datetime, timedelta
import requests
from time import strftime, localtime
import re

exprd = False

DIY    = 365.25      # this is what physicists use, eg, to define a light year
SID    = 86400       # seconds in a day
BDAWN  = 1202749200  # 2008-02-11, dawn of Kibotzer/Beeminder
BDUSK  = 2147317201  # ~2038, specifically rails's ENDOFDAYS+1 (was 2^31-2weeks)

SECS = { # Number of seconds in a year, month, week, day, and hour
'y' : DIY*SID,
'm' : DIY/12*SID,
'w' : 7*SID,
'd' : SID,
'h' : 3600,
}

# Util function "foldlist" that's like Ruby's inject but keeps the intermediate results:
# foldlist(f,x, [e1, e2, ...]) -> [x, f(x,e1), f(f(x,e1), e2), ...]
def foldlist(f, x, lst):
    result = [x]
    for item in lst:
        x = f(x, item)
        result.append(x)
    return result

# Given the endpoint of the last redline segment (tprev,vprev) and 2 out of 3 of
#   t = goal date for a redline segment (unixtime)
#   v = goal value 
#   r = rate in hertz (s^-1), ie, redline rate per second
# return the third, namely, whichever one is passed in as null.
def tvr(tprev, vprev, t, v, r):
  if exprd and v != None:  # no such thing as exprd's now so ignore this
    if v     == 0: v     = 1e-6 # zero values and exprds don't mix!
    if vprev == 0: vprev = 1e-6 # just make them near zero I guess?

  if t == None:
    if r == 0: return BDUSK
    else:  return min(BDUSK, tprev + (log(v/vprev)/r if exprd else (v-vprev)/r))
  if v == None: 
    if exprd and r*(t-tprev) > 35: return vprev*1e15 # bugfix: math overflow
    return vprev*exp(r*(t-tprev)) if exprd else vprev+r*(t-tprev)
  if r == None:
    if t == tprev: return 0 # special case: zero-length line segment
    return log(v/vprev)/(t-tprev) if exprd else (v-vprev)/(t-tprev)

# Helper for fillroad for propagating forward filling in all the nulls
def nextrow(prev, road):
  tprev, vprev, rprev = prev
  t, v, r = road
  x = tvr(tprev, vprev, t,v,r) # the missing t, v, or r
  if t==None: return (x, v, r)
  if v==None: return (t, x, r)
  if r==None: return (t, v, x)

# Takes graph matrix (with last row appended) and fills it in
def fillroad(tini, vini, road, siru):
  road = [(dayfloor(t), v, r if r==None else r/siru) for (t,v,r) in road]
  road = foldlist(nextrow, (tini, vini, 0), road)[1:]
  return [(t, v, r*siru) for (t,v,r) in road]

# Helper for roadfunc. Return the value of the segment of the YBR at time x, 
# given the start of the previous segment (tprev,vprev) and the rate r. 
# (Equivalently we could've used the start and end points of the segment, 
# (tprev,vprev) and (t,v), instead of the rate.)
def rseg(tprev, vprev, r, x): 
  if exprd and r*(x-tprev) > 230: return 1e100 # bugfix: math overflow
  return vprev*exp(r*(x-tprev)) if exprd else vprev+r*(x-tprev)

# Take an initial point and a filled-in graph matrix (including the final row) 
# and a time t and return the value of the centerline at time x.
def roadfunc(fullroad, x, siru):
  if x<fullroad[0][0]: return fullroad[0][1] # road value is vini before tini
  for i in range(1, len(fullroad)):
    if x<fullroad[i][0]: return rseg(fullroad[i-1][0], fullroad[i-1][1], fullroad[i][2]/siru, x)
  return fullroad[-1][1]

from datetime import datetime, timedelta

def generate_dueby_table(goal, days):
    fullroad = goal['fullroad']
    rate = goal['rate']
    curval = goal['curval']

    # Get the current time in epoch seconds
    now = int(datetime.utcnow().timestamp())

    # Calculate the start and end times for the dueby table (n days in the future)
    start_time = now
    end_time = now + days*24*60*60
    dates = range(start_time, end_time+1, 24*60*60)

    # Initialize the dueby table as a list of dicts
    dueby_table = [{'date': d, 'value': None} for d in dates]

    # Iterate over each goal and calculate the due value for each date in the dueby table
    siru = SECS[goal['runits']] # seconds in rate units

    for i, date in enumerate(dates):
        value = roadfunc(fullroad, date, siru) - curval
        dueby_table[i]['value'] = value if value > 0 else 0

    return dueby_table

def pprint_dueby(table):
    for t in table:
        day = strftime('%Y-%m-%d', localtime(t['date']))
        val = round(t['value'])
        print(f"{day}: +{val}")


def date_range(start_date, end_date):
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(n)

def dayfloor(t):
    dt = datetime.utcfromtimestamp(t)
    return int((datetime(dt.year, dt.month, dt.day) - datetime(1970, 1, 1)).total_seconds())


#print("getting goals")
# Set your Beeminder username and auth_token
username   = 'ianminds'
auth_token = 's3cr3t'

# Set the API endpoint and parameters
api_endpoint = f'https://www.beeminder.com/api/v1/users/{username}/goals.json'
params = {'auth_token': auth_token}

# Send a GET request to the API endpoint with the parameters
response = requests.get(api_endpoint, params=params)
# Parse the response JSON and extract the list of goals
goals = response.json()

#for goal in goals[0:9]:
for goal in goals:
    slug = goal['slug']
    if re.match(r'read-2022\d{3}', slug):
            continue
    print("dueby for goal ", goal['slug'])
    table = generate_dueby_table(goal, 14)
    pprint_dueby(table)
    print("")
    print("")
