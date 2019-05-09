import requests
from bs4 import BeautifulSoup
import os
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import argparse


###################################
### Get the games for a given date
###################################

CHROME_PATH = '/usr/bin/google-chrome'
CHROMEDRIVER_PATH = '/usr/local/bin/chromedriver'
WINDOW_SIZE = "1920,1080"

script_folder = os.path.abspath(os.path.dirname(__file__))
base_folder = os.path.dirname(script_folder)
html_file_folder = base_folder + '/html_scoreboard_files'
parsed_data_folder = base_folder + '/parsed_data'

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

### extract webpage content by calling the url using headless chrome
### the page is loaded dynamically and hence need to use a webdriver 
### to get the whole HTML that will be rendered
def get_scoreboard_date(day):
    url = 'http://www.espn.com/nba/scoreboard/_/date/{0}'.format(day)
    
    chrome_options = Options()  
    chrome_options.add_argument("--headless")  
    chrome_options.add_argument("--window-size=%s" % WINDOW_SIZE)
    chrome_options.binary_location = CHROME_PATH
    
    driver = webdriver.Chrome(executable_path=CHROMEDRIVER_PATH, chrome_options=chrome_options)
    
    driver.get(url)
    html_source = driver.page_source
    
    html_file = html_file_folder + '/' + day + '_scoreboard.html'
    
    fp = open(html_file, 'w')
    fp.write(html_source)
    fp.close()
    
### parse the scoreboard data ad get the games for the day
def parse_scoreboard_data(day):
    html_file = html_file_folder + '/' + day + '_scoreboard.html'
    
    html_text = load_html_from_file(html_file)
    soup = BeautifulSoup(html_text, 'html.parser')
    
    events_dom = soup.find("div", {"id": "events"})
    
    game_doms = events_dom.find_all("article", recursive = False)
    for game in game_doms:
        game_id = game.get('id')
        
        teams = game.find("tbody", {"id": "teams"}).find_all("tr", recursive = False)
        
        team_names = {}
        for t in teams:
            home_away = t.get("class")[0]
            team_link = t.find("span", {"class": "sb-team-short"})
            team_name = team_link.text
            
            team_names[home_away] = team_name
        
        print(','.join([day, game_id, team_names['away'], team_names['home']]))
        

def main(day, cache):
    if (not cache):
        get_scoreboard_date(day)
        
    parse_scoreboard_data(day)
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--day')
    parser.add_argument('--cache', action = 'store_true')
    
    input_args = parser.parse_args()
    day = input_args.day
    cache = input_args.cache
    
    main(day, cache)
