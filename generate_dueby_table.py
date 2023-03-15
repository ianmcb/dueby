import json
import pandas as pd
from datetime import datetime, timedelta
import requests

# Helper for roadfunc. Return the value of the segment of the YBR at time x, 
# given the start of the previous segment (tprev,vprev) and the rate r. 
# (Equivalently we could've used the start and end points of the segment, 
# (tprev,vprev) and (t,v), instead of the rate.)
def rseg(tprev, vprev, r, x): 
  if exprd and r*(x-tprev) > 230: return 1e100 # bugfix: math overflow
  return vprev*exp(r*(x-tprev)) if exprd else vprev+r*(x-tprev)

# Take an initial point and a filled-in graph matrix (including the final row) 
# and a time t and return the value of the centerline at time x.
def roadfunc(tini, vini, road, x):
  road = [(tini,vini,None)] + road
  if   x<road[0][0]: return road[0][1] # road value is vini before tini
  for i in range(1, len(road)):
    if x<road[i][0]: return rseg(road[i-1][0], road[i-1][1], road[i][2]/siru, x)
  return road[-1][1]

def generate_dueby_table(start_date, goals):
    # Set the time increment to one day
    time_increment = timedelta(days=1)

    # Calculate the end date as one month from the start date
    end_date = start_date + timedelta(days=30)

    # Create an empty DataFrame to hold the dueby table
    dueby_table = pd.DataFrame(columns=['goal'] + [date.date() for date in pd.date_range(start_date, end_date, freq=time_increment)])

    # Iterate over each goal
    for goal in goals:
        # Get the road matrix for the goal
        road_matrix = goal['road']

        # Get the initial value and time for the goal
        initial_value = road_matrix[0]['val']
        initial_time = datetime.fromtimestamp(road_matrix[0]['ts'])

        # Create a list to hold the centerline values for each day
        centerline_values = []

        # Calculate the centerline value for each day between the start and end dates
        for date in pd.date_range(start_date, end_date, freq=time_increment):
            # Calculate the value of the goal's centerline at the current date
            centerline_value = roadfunc(initial_time, initial_value, road_matrix, date.timestamp())

            # Append the centerline value to the list
            centerline_values.append(centerline_value)

        # Add the goal and centerline values to the dueby table
        row = [goal['slug']] + centerline_values
        dueby_table = dueby_table.append(pd.Series(row, index=dueby_table.columns), ignore_index=True)

    return dueby_table

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

json.dumps(goals, indent=2) 
