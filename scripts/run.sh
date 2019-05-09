#!/bin/bash

FILE_DIR=$(dirname $(readlink -f "${BASH_SOURCE[0]}"))
ROOT_DIR=$(readlink -e "$FILE_DIR/..")

### Run scraper for all games
while read game 
do
    game_id=$(echo $game | awk -F',' '{print $2}')
    echo $game_id

    python3 scripts/scrape.py --game_id $game_id
    sleep 2

done < $ROOT_DIR/games


### Run processing for all games from the scraped data
while read game 
do
    game_id=$(echo $game | awk -F',' '{print $2}')
    echo $game_id

    python3 scripts/extract.py --game_id $game_id

done < $ROOT_DIR/games

### Insert processed plays data into postres table
for game_file in $(ls $ROOT_DIR/parsed_data/plays_processed)
do
    echo $game_file
    game_id=$(echo $game_file | awk -F'.' '{print $1}' | awk -F'_' '{print $3}')
    echo $game_id

   psql -d nba -c "delete from plays_201819 where game_id = '$game_id'"
   psql -d nba -c "\COPY plays_201819 FROM $ROOT_DIR/parsed_data/plays_processed/$game_file delimiter E'\t' csv header"
done
