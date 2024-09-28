# PyMongo & Web Scrapping

## Overview

This project aims to scrape existing recipes from the website [kulinari.ge](https://kulinari.ge). The scraper will extract essential information about each recipe and store it in a MongoDB database for further analysis.

## Instruction:
     pip install -r requirements.txt
     python scraping.py
     python statistic.py



## To-Do List

### Web Scraping

**Scrape Recipe Data**
   - [ ] Fetch HTML content from the website.
   - [ ] Use web scraping techniques to retrieve:
     - [ ] Recipe name
     - [ ] Recipe URL
     - [ ] Main category name and URL
     - [ ] Subcategory name
     - [ ] Main image URL
     - [ ] Description
     - [ ] Author name
     - [ ] Etc

### Database Operations

**MongoDB Setup**
   - [ ] Set up a MongoDB database.
   - [ ] Design the schema for storing recipes:
     - [ ] Recipe name
     - [ ] URL
     - [ ] Main category
     - [ ] Subcategory
     - [ ] Image URL
     - [ ] Description
     - [ ] Author name
     - [ ] Etc

**Save Data to MongoDB**
   - [ ] Implement functionality to save scraped recipe data into the MongoDB database.

### Statistics Calculation

**Calculate Recipe Statistics**
   - [ ] Retrieve data from MongoDB.
   - [ ] Calculate the following statistics:
     - [ ] Average number of ingredients per recipe.
     - [ ] Average number of steps per recipe.
     - [ ] Total number of recipes.
     - [ ] Other relevant statistics (to be determined).
