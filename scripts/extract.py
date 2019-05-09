import os
import sys
import simplejson as json
import argparse
import numpy as np
import pandas as pd
import re

##############################################################
### Read the game play-by-play commentary and extract fields
### from the plays and return a data frame with the extracted
### fields for the game
##############################################################

script_folder = os.path.abspath(os.path.dirname(__file__))
base_folder = os.path.dirname(script_folder)
html_file_folder = base_folder + '/html_scoreboard_files'
parsed_data_folder = base_folder + '/parsed_data'

def clean_event(event):
    event = event.replace("'s", '')
    
    return event

### clean up invalid points due to type in the webpage. Involves some assumption
### If it is not a definite free throw or a three point shot then it is assigned 2 points
def clean_points(row, teams):
    event = row['event']
    action = row['action']
    team = row['team']
    team1_event_point = row['team1_event_point']
    team2_event_point = row['team2_event_point']
    
    if (action is not None and action != 'makes'):
        # if (team1_event_point + team2_event_point != 0):
        #     print(event, team1_event_point, team2_event_point)
            
        team1_event_point = 0
        team2_event_point = 0
        
    if (action is not None and action == 'makes'):
        if (team1_event_point == 0 and team2_event_point == 0):
            point = 2
            r = re.search('(.*)(free throw)(.*)', event)
            if (r is not None):
                point = 1
                
            r = re.search('(.*)(three point)(.*)', event)
            if (r is not None):
                point = 3
                
            if team == teams['away'][2].lower():
                team1_event_point = point
            else:
                team2_event_point = point
    
    row['team1_event_point'] = team1_event_point
    row['team2_event_point'] = team2_event_point
    
    return row

### extract schematic data fro plays from the play by plat tet commentary
def main(game_id):
    team_file = parsed_data_folder + '/teams/teams_' + str(game_id) + '.json'
    players_file = parsed_data_folder + '/players/players_' + str(game_id) + '.json'
    plays_file = parsed_data_folder + '/plays/plays_' + str(game_id)
    
    fp = open(team_file, 'r')
    teams = json.load(fp)
    fp.close()
    
    fp = open(players_file, 'r')
    players = json.load(fp)
    fp.close()
    
    plays = pd.read_csv(plays_file, sep = ',', names = ['quarter', 'q_time', 'q_time_remaining', 'team', 'event', 'score'])
    
    plays['team1_score'] = plays['score'].apply(lambda x: int(x.split('-')[0].strip()))
    plays['team2_score'] = plays['score'].apply(lambda x: int(x.split('-')[1].lstrip()))
    
    plays['team1_score_lag'] = plays['team1_score'].shift(1, fill_value = 0)
    plays['team2_score_lag'] = plays['team2_score'].shift(1, fill_value = 0)
    
    plays['team1_score'] = np.maximum(plays['team1_score'], plays['team1_score_lag'])
    plays['team2_score'] = np.maximum(plays['team2_score'], plays['team2_score_lag'])
    
    plays['team1_event_point'] = plays['team1_score'] - plays['team1_score_lag']
    plays['team2_event_point'] = plays['team2_score'] - plays['team2_score_lag']
    
    plays['team1_event_point'] = np.maximum(0, plays['team1_score'] - plays['team1_score_lag'])
    plays['team2_event_point'] = np.maximum(0, plays['team2_score'] - plays['team2_score_lag'])
    plays = plays.drop(columns = ['team1_score_lag', 'team2_score_lag'])
    
    team_home = teams['home'][1]
    team_away = teams['away'][1]
    
    pd.set_option('display.max_colwidth', -1)
    
    event_parsed = []
    
    for e in plays[['event']].values:
        event = e[0]

        
        event = clean_event(event)
        event_secondary = ''
        
        r = re.search('\((.+)\)', event)
        if (r is not None):
            event_secondary = r.group(1)
            event = re.sub('(\(.+\))', '', event)
        
        players_all = players['home'] + players['away']
        
        player1 = None
        player2 = None
        player_secondary = None
        
        ### extract players from the event
        for p in players_all:
            r1 = re.search('^({0})(.*)'.format(p), event)
            r2 = re.search('(.+)({0})(.*)'.format(p), event)
            r3 = re.search('^({0})(.*)'.format(p), event_secondary)
            
            if (r1 is not None):
                player1 = p
                
            if (r2 is not None):
                player2 = p
                
            if (r3 is not None):
                player_secondary = p
        
        if (player1 is not None):
            if (player2 is None):
                player_pattern = player1
            else:
                player_pattern = player1 + '|' + player2
        else:
            player_pattern = ''
        
        ### extract action from the event by removing players
        action = re.sub(player_pattern, '', event).strip().lstrip()
        
        ### extract foot value from the action
        
        foot_value = None
        r_foot = re.search('(.*) ([0-9]+)-foot(.*)', action)
        if (r_foot is not None):
            foot_value = r_foot.group(2)
            action = re.sub('{0}-foot'.format(foot_value), '', action)
            
        ### extract free throw
        
        free_throw = None
        #r_ft = re.search('(.*)free[ ]{1,}throw[ ]{1,}([1-3])[ ]{1,}of[ ]{1,}([1-3])(.*)', action)
        r_ft = re.search('(.*)free[ ]{1,}throw[ ]{1,}([1-3])[ ]{1,}of[ ]{1,}([1-3])(.*)', action)
        if (r_ft is not None):
            ft_val = [r_ft.group(2), r_ft.group(3)]
            free_throw = '-'.join(ft_val)
            action = re.sub('([1-3])[ ]{1,}of[ ]{1,}([1-3])', '', action)
            
        ### extract action point info
        
        point_info = None
        r_pt = re.search('(.*)(two|three)[ ]{1,}point(.*)', action)
        if (r_pt is not None):
            point_info = r_pt.group(2)
            action = re.sub('(two|three)[ ]{1,}point', '', action)
        
        ### extract team action
        team_action = None
        r4 = re.search('(.*)({0})(.*)'.format(team_home), action)
        if (r4 is not None):
            team_action = team_home
            
        r5 = re.search('(.*)({0})(.*)'.format(team_away), action)
        if (r5 is not None):
            team_action = team_away
        
        if (team_action is not None):
            action = re.sub(team_action, '', action)
        
        action_secondary = None
        if (player_secondary is not None):
            action_secondary = re.sub(player_secondary, '', event_secondary)
        
        ### extract action further
        action_what = None
        r_action = re.search('(makes|misses|blocks|foul|turnover)', action)
        if (r_action is not None):
            action_what = re.sub('(.*)(makes|misses|blocks|foul|turnover)', '', action)
            action = r_action.group(1)
            
        r_action = re.search('(offensive|defensive)[ ]{1,}(.*)(rebound)', action)
        if (r_action is not None):
            action_what = r_action.group(2)
            action = re.sub(action_what, '', action)
            
        ### replace multiple space with single space
        if (action is not None):
            action = re.sub('[ ]{2,}', ' ', action.strip().lstrip()).lower()
        
        if (action_secondary is not None):
            action_secondary = re.sub('[ ]{2,}', ' ', action_secondary.strip().lstrip()).lower()
            
        if (team_action is not None):
            team_action = re.sub('[ ]{2,}', ' ', team_action.strip().lstrip()).lower()
            
        if (action_what is not None):
            action_what = re.sub('[ ]{2,}', ' ', action_what.strip().lstrip()).lower()
            if (action_what == ''):
                action_what = None
    
        action_row = [
            player1,
            player2,
            action,
            action_what,
            foot_value,
            free_throw,
            point_info,
            player_secondary,
            action_secondary,
            team_action
        ]
        
        event_parsed.append(action_row)
        
    df_columns = [
        'player1',
        'player2',
        'action',
        'action_what',
        'foot_value',
        'free_throw',
        'point_info',
        'player_secondary',
        'action_secondary',
        'team_action'
    ]
    
    event_parsed_df = pd.DataFrame(event_parsed, columns = df_columns)
    
    plays_processed = pd.merge(plays, event_parsed_df, how = 'inner', left_index = True, right_index = True)
    plays_processed.insert(0, 'game_id', game_id)
        
    plays_processed = plays_processed.apply(clean_points, teams = teams, axis = 1)
    print(plays_processed.to_string())
    
    output_filename = parsed_data_folder + '/plays_processed/plays_processed_{0}.tsv'.format(game_id)
    plays_processed.to_csv(output_filename, sep = '\t', index = None)
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--game_id', required = True)
    
    input_args = parser.parse_args()
    game_id = input_args.game_id
    
    main(game_id)
