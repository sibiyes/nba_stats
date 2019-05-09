import requests
from bs4 import BeautifulSoup
import os
import re
from datetime import time
import simplejson as json
import argparse

#############################################################
### get the webpage from the corresponding URL and scrape the 
### play by play game date and the player info and write
### the parsed data to a text file
#############################################################

script_folder = os.path.abspath(os.path.dirname(__file__))
base_folder = os.path.dirname(script_folder)
html_file_folder = base_folder + '/html_files'
parsed_data_folder = base_folder + '/parsed_data'

### extract play-by-play webpage content from the url corresponding to the game
def get_playbyplay(game_id):    
    url = 'http://www.espn.com/nba/playbyplay?gameId={0}'.format(game_id)
    page = requests.get(url)

    html_file = html_file_folder + '/' + game_id + '/playbyplay.html'

    fp = open(html_file, 'w')
    fp.write(page.text)
    fp.close()

### extract gamecast webpage content from the url corresponding to the game    
def get_gamecast(game_id):
    url = 'http://www.espn.com/nba/game?gameId={0}'.format(game_id)
    page = requests.get(url)

    html_file = html_file_folder + '/' + game_id + '/gamecast.html'

    fp = open(html_file, 'w')
    fp.write(page.text)
    fp.close()

def get_team_code(img_url):
    team_code = re.search("(.*)/i/teamlogos/nba/500/(.*)\.png", img_url).group(2)

    return team_code

### scrape the game play by play events by scrapping the html
def scrape_plays(plays_dom):
    if (plays_dom is None):
        return None
    
    table = plays_dom.find("table")        
    table_rows = table.find_all("tr")

    plays_parsed = []
    for row in table_rows:
        row_elements = list(row.children)

        if (row_elements[0].name == 'th'):
            continue

        time_stamp = row_elements[0].text
        team_image = row_elements[1].find("img")
        team_image_url = team_image.attrs['src']

        team_code = get_team_code(team_image_url)

        game_details = row_elements[2].text
        score = row_elements[3].text

        parsed_row = [time_stamp, team_code, game_details, score]

        plays_parsed.append(parsed_row)

    return plays_parsed

def parse_playclock_time(time_string):
    time_string_split = time_string.split(':')
    if (len(time_string_split) > 2):
        raise Exception('Invalid playclock time')

    if (len(time_string_split) == 1):
        minute = 0
        second = float(time_string_split[0])
    else:
        minute  = int(time_string_split[0])
        second = float(time_string_split[1])

    return (minute, second)

### parse game time and return elapsed time in a quarter
def quarter_time_elapsed(play, quarter):
    quarter_time_remaining = play[0]
    minute, second = parse_playclock_time(quarter_time_remaining)

    time_played_seconds = (60 - second)%60
    #time_played_minutes = (quarter -1)*12 + (12 - minute - 1) + ((60 - second)//60)
    time_played_minutes = (12 - minute - 1) + ((60 - second)//60)
    
    time_elapsed = time(0, int(time_played_minutes), int(time_played_seconds)).strftime('%M:%S')

    return time_elapsed

### load html file from local storage
def load_html_from_file(html_file):
    fp = open(html_file)

    html_rows = []
    line = fp.readline()

    while (line != ''):
        html_rows.append(line.strip())
        line = fp.readline()

    fp.close()

    html_text = ''.join(html_rows)
    
    return html_text
    
### parse play-by-play data from the scrapped data
def parse_playbyplay(game_id):
    html_file = html_file_folder + '/' + game_id + '/playbyplay.html'

    fp = open(html_file)

    html_rows = []
    line = fp.readline()

    while (line != ''):
        html_rows.append(line.strip())
        line = fp.readline()

    fp.close()

    html_text = ''.join(html_rows)
    
    soup = BeautifulSoup(html_text, 'html.parser')

    play_by_play_dom = soup.find("div", {"id": "gamepackage-qtrs-wrap"})
    
    quarters = {}
    
    ### Look for quarter doms and add them to the quarters dict
    q = 1
    while(True):
        ot_div_id = 'gp-quarter-{0}'.format(q)
        ot_dom = play_by_play_dom.find("div", {"id": ot_div_id})
        
        if (ot_dom is not None):
            quarters[q] = ot_dom
            q += 1
        else:
            break    

    ### parsing quarter dom
    parsed_data_file = parsed_data_folder + '/plays/plays_' + str(game_id)

    fp = open(parsed_data_file, 'w')
    
    for q in quarters:
        quarter_dom = quarters[q]
        plays_parsed = scrape_plays(quarter_dom)


        for row in plays_parsed:
            t = quarter_time_elapsed(row, q)
            row = [q, t] + row
            print(row)
            row = [str(x) for x in row]
            output_line = ','.join(row)
            fp.write(output_line + '\n')

    fp.close()
    
### parse gamecast data to obtain team info and player for each team
def parse_gamecast(game_id):
    html_file = html_file_folder + '/' + game_id + '/playbyplay.html'    
    html_text = load_html_from_file(html_file)
    
    soup = BeautifulSoup(html_text, 'html.parser')
    
    competiitors_dom = soup.find("div", {"class": "competitors"})
    team_away = competiitors_dom.find("div", {"class": "team away"}).find("a", {"class": "team-name"})
    team_home = competiitors_dom.find("div", {"class": "team home"}).find("a", {"class": "team-name"})
    
    team_away_full = []
    for n in team_away.findAll("span"):
        team_away_full.append(n.text)
    
    team_home_full = []
    for n in team_home.findAll("span"):
        team_home_full.append(n.text)
    
    team_all = {
        "away": team_away_full,
        "home": team_home_full
    }
    
    team_info_dom = soup.find("div", {"id": "accordion-1"})
    
    away_team = team_info_dom.find("div", {"class": "team away"})
    home_team = team_info_dom.find("div", {"class": "team home"})
    
    away_players_list = away_team.find("ul", {"class": "playerfilter"})
    home_players_list = home_team.find("ul", {"class": "playerfilter"})
    
    away_players_all = []
    home_players_all = []
    
    for player in away_players_list.findAll("li"):
        player_id = player.get("data-playerid")
        if (player_id == "0"):
            continue
        
        player_name = player.text
        away_players_all.append(player_name)
        
    for player in home_players_list.findAll("li"):
        player_id = player.get("data-playerid")
        if (player_id == "0"):
            continue
        
        player_name = player.text
        home_players_all.append(player_name)
    
    players_all = {
        "away": away_players_all,
        "home": home_players_all
    }
    
    print(team_all)
    print(players_all)
    
    team_file = parsed_data_folder + '/teams/teams_' + str(game_id) + '.json'
    players_file = parsed_data_folder + '/players/players_' + str(game_id) + '.json'
    
    fp = open(team_file, 'w')
    json.dump(team_all, fp)
    fp.close()
    
    fp = open(players_file, 'w')
    json.dump(players_all, fp)
    fp.close()    
    
def main(game_id):
    #game_id = '401034614'
    
    folder_path = html_file_folder + '/' + game_id
    
    if not (os.path.exists(folder_path)):
        os.makedirs(folder_path)
    
    get_playbyplay(game_id)
    get_gamecast(game_id)
    
    parse_playbyplay(game_id)
    parse_gamecast(game_id)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--game_id')
    
    input_args = parser.parse_args()
    game_id = input_args.game_id
    
    main(game_id)
