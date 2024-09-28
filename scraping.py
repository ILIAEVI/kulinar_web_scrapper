import json
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import logging
from motor.motor_asyncio import AsyncIOMotorClient


logging.basicConfig(level=logging.INFO)


class ConfigLoader:
    """Helper class to load the configuration from a JSON file."""

    @staticmethod
    def load_config(file_path):
        """Loads JSON configuration from a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            logging.error(f"Configuration file '{file_path}' not found!")
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON file '{file_path}': {e}")
        return None


class ScrapingMixin:
    """Mixin to provide utility functions for web scraping."""
    @staticmethod
    async def get_soup(session, url):
        """Fetches the content from the URL and returns a BeautifulSoup object."""
        try:
            async with session.get(url) as response:
                response.raise_for_status()
                return BeautifulSoup(await response.text(), 'html.parser')
        except Exception as e:
            logging.error(f"Error fetching URL {url}: {e}")
            return None

    @staticmethod
    def clean_text(text):
        """Cleans up text by removing newlines, extra spaces, and special characters."""
        return ' '.join(text.replace('\n', ' ').replace('\xa0', ' ').split())

    async def get_cooking_stages(self, soup, config):
        """Extracts cooking stages from the soup object based on the config."""
        stages = []
        try:
            stage_divs = soup.find_all('div', class_=config["recipe_page_classes"]["cooking_stages"])

            for item in stage_divs:
                stage = self.clean_text(item.find('div', class_=config["recipe_page_classes"]["stage_count"]).text)
                description = self.clean_text(item.find('p').text)
                stages.append({'stage': stage, 'text': description})
            return stages
        except AttributeError as e:
            logging.error(f"Error extracting cooking stages: {e}")


class Scraper(ScrapingMixin):
    def __init__(self, config):
        self.config = config
        self.base_url = config["base_url"]
        self.main_category_name = config["main_category_name"]
        self.main_category_url = None

    async def initialize_main_category(self, session):
        """Initialize the main category URL after fetching categories."""
        categories = await self.get_categories(session, self.base_url + self.config["categories_url"])
        self.main_category_url = self.get_one_category_url(categories)

    async def get_categories(self, session, url):
        """Fetches and returns all categories from the given URL."""
        soup = await self.get_soup(session, url)
        if soup is None:
            logging.error("Failed to retrieve categories: Invalid URL or network issue.")
            return []

        try:
            categories_div = soup.find('div', class_=self.config["category_classes"]["main_category"])
            categories = [
                Category(
                    url.find('div', class_=self.config["category_classes"]["category_text"]).get_text(strip=True),
                    self.base_url + url['href']
                ).to_dict()
                for url in categories_div.find_all('a', class_=self.config["category_classes"]["category_item"])
            ]
            return categories
        except AttributeError as e:
            logging.error(f"Error extracting categories: {e}")
            return []

    def get_one_category_url(self, categories):
        """Fetches the URL of the specified main category."""
        for category in categories:
            if category['name'] == self.main_category_name:
                return category['url']

        logging.error(f"Main category '{self.main_category_name}' not found.")
        return None

    async def get_all_recipes_urls(self, session, categories):
        """Fetches all recipe URLs from the provided categories."""
        try:
            tasks = [self._extract_recipe_urls(session, category) for category in categories]
            return await asyncio.gather(*tasks)
        except Exception as e:
            logging.error(f"Error fetching recipe URLs: {e}")
            return []

    async def _extract_recipe_urls(self, session, category):
        """Helper function to extract recipe URLs from a single category."""
        soup = await self.get_soup(session, category['url'])
        if soup is None:
            logging.error(f"Failed to fetch recipes from category '{category['name']}'")
            return []

        try:
            class_conf = self.config["recipes_classes"]["recipes_container"]
            recipe_links = soup.find('div', class_=class_conf).find_all('a', class_=self.config["recipes_classes"]["recipe_link"])
            return [
                SubCategory(category['name'], category['url'], [self.base_url + link['href'] for link in recipe_links]).to_dict()
            ]
        except AttributeError as e:
            logging.error(f"Error extracting recipes for category '{category['name']}': {e}")
            return []


class RecipeScraper(Scraper):
    """Handles scraping of individual recipe pages."""

    async def scrape_recipe(self, session, data):
        """Scrapes recipe details from the provided sub-category data."""
        tasks = []
        for sub_category in data:
            for recipe_url in sub_category.get('recipe_urls', []):
                tasks.append(self.extract_recipe_details(session, recipe_url, sub_category['sub_category_name'], sub_category['sub_category_url']))
        return await asyncio.gather(*tasks)

    async def extract_recipe_details(self, session, recipe_url, sub_category_name, sub_category_url):
        """Extracts details of a single recipe."""
        soup = await self.get_soup(session, recipe_url)
        if soup is None:
            logging.error(f"Failed to retrieve recipe details from {recipe_url}")
            return None

        try:
            recipe_title = self.clean_text(
                soup.find('div', class_=self.config["recipe_page_classes"]["recipe_title"]).get_text())
            main_image_url = soup.find('div', class_=self.config["recipe_page_classes"]["main_image"]).find('img')['src']
            description = self.clean_text(
                soup.find('div', class_=self.config["recipe_page_classes"]["description"]).get_text())
            author_name = self.clean_text(soup.find('div', class_=self.config["recipe_page_classes"]["author"]).find(
                self.config["recipe_page_classes"]["author_name"]).get_text())
            ingredients = [self.clean_text(div.get_text()) for div in
                           soup.find_all('div', class_=self.config["recipe_page_classes"]["ingredients"])]
            cooking_stages = await self.get_cooking_stages(soup, self.config)
            portion = soup.find_all('div', class_=self.config["recipe_page_classes"]["portion"])[1].text.strip()
            if portion == "ულუფა":
                portion = "1 ულუფა"

            return {
                'recipe_name': recipe_title,
                'url': recipe_url,
                'main_category_name': self.main_category_name,
                'main_category_url': self.main_category_url,
                'sub_category_name': sub_category_name,
                'sub_category_url': sub_category_url,
                'main_image_url': main_image_url,
                'description': description,
                'author_name': author_name,
                'ingredients': ingredients,
                'cooking_stages': cooking_stages,
                'portion': portion
            }
        except AttributeError as e:
            logging.error(f"Error extracting recipe details: {e}")
            return None


class Category:
    """Represents a category object."""

    def __init__(self, name, url):
        self.name = name
        self.url = url

    def to_dict(self):
        return {'name': self.name, 'url': self.url}


class SubCategory:
    """Represents a sub-category object with associated recipes."""

    def __init__(self, sub_category_name, sub_category_url, recipe_urls):
        self.sub_category_name = sub_category_name
        self.sub_category_url = sub_category_url
        self.recipe_urls = recipe_urls

    def to_dict(self):
        return {
            'sub_category_name': self.sub_category_name,
            'sub_category_url': self.sub_category_url,
            'recipe_urls': self.recipe_urls
        }


async def save_to_mongodb(results, mongo_uri, db_name, collection_name):
    """Saves the scraped results to MongoDB."""
    client = AsyncIOMotorClient(mongo_uri)
    db = client[db_name]
    collection = db[collection_name]

    if results:
        await collection.insert_many(results)
        logging.info(f"Saved {len(results)} recipes to MongoDB collection '{collection_name}'")

    client.close()

async def delete_collection(mongo_uri, db_name, collection_name):
    client = AsyncIOMotorClient(mongo_uri)
    db = client[db_name]

    existing_collections = await db.list_collection_names()

    if collection_name in existing_collections:
        await db[collection_name].drop()
        print(f"Collection '{collection_name}' has been deleted.")
    else:
        print(f"Collection '{collection_name}' does not exist.")


async def main():
    configuration = ConfigLoader.load_config('config.json')
    scraper = RecipeScraper(configuration)

    async with aiohttp.ClientSession() as session:
        await scraper.initialize_main_category(session)

        logging.info(f"Fetching categories from {configuration['base_url'] + configuration['categories_url']}")

        if not scraper.main_category_url:
            logging.error(f"Category '{scraper.main_category_name}' not found!")
        else:
            logging.info(f"Fetching sub-categories for {scraper.main_category_name}")
            sub_categories = await scraper.get_categories(session, scraper.main_category_url)

            logging.info("Fetching and scraping all recipe URLs...")
            recipes = await scraper.get_all_recipes_urls(session, sub_categories)
            flattened_recipes = [recipe for sublist in recipes for recipe in sublist]
            results = await scraper.scrape_recipe(session, flattened_recipes)

            print(json.dumps(results, ensure_ascii=False, indent=4))

            mongo_uri = configuration['mongodb']['uri']
            db_name = configuration['mongodb']['db_name']
            collection_name = configuration['mongodb']['collection_name']

            await delete_collection(mongo_uri, db_name, collection_name)

            await save_to_mongodb(results, mongo_uri, db_name, collection_name)

if __name__ == '__main__':
    final_results = asyncio.run(main())

