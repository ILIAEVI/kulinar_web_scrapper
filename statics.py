import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from scraping import ConfigLoader

config = ConfigLoader.load_config('config.json')

mongo_uri = config['mongodb']['uri']
recipe_database = config['mongodb']['db_name']
recipes = config['mongodb']['collection_name']


async def calculate_average_ingredients():
    client = AsyncIOMotorClient(mongo_uri)
    db = client[recipe_database]
    collection = db[recipes]

    pipeline = [
        {
            '$group': {
                '_id': None,
                'total_ingredients': {'$sum': {'$size': '$ingredients'}},
                'total_recipes': {'$sum': 1}
            }
        },
        {
            '$project': {
                '_id': 0,
                'average_ingredients': {'$divide': ['$total_ingredients', '$total_recipes']}
            }
        }
    ]

    result = await collection.aggregate(pipeline).to_list(length=1)

    if result:
        average = result[0]['average_ingredients']
        print(f"Average ingredients: {average:.2f}")
    else:
        print("No recipes found.")


async def calculate_average_cooking_stage():
    client = AsyncIOMotorClient(mongo_uri)
    db = client[recipe_database]
    collection = db[recipes]

    pipeline = [
        {
            '$group': {
                '_id': None,
                'total_stages': {'$sum': {'$size': '$cooking_stages'}},
                'total_recipes': {'$sum': 1}
            }
        },
        {
            '$project': {
                '_id': 0,
                'average_cooking_stage': {'$divide': ['$total_stages', '$total_recipes']}
            }
        }
    ]

    result = await collection.aggregate(pipeline).to_list(length=1)

    if result:
        average = result[0]['average_cooking_stage']
        print(f"Average cooking stages: {average:.2f}")
    else:
        print("No recipes found.")


async def find_top_author():
    client = AsyncIOMotorClient(mongo_uri)
    db = client[recipe_database]
    collection = db[recipes]

    pipeline = [
        {
            '$group': {
                '_id': '$author_name',
                'recipe_count': {'$sum': 1}
            }
        },
        {
            '$sort': {
                'recipe_count': -1
            }
        },
        {
            '$limit': 1
        }
    ]

    result = await collection.aggregate(pipeline).to_list(length=None)

    if result:
        top_author = result[0]['_id']
        top_count = result[0]['recipe_count']
        print(f'Author with the most recipes: {top_author}, Recipe Count: {top_count}')
    else:
        print('No authors found.')


async def find_recipe_with_most_portion():
    client = AsyncIOMotorClient(mongo_uri)
    db = client[recipe_database]
    collection = db[recipes]

    pipeline = [
        {
            '$match': {
                'portion': {'$exists': True}
            }
        },
        {
            '$project': {
                'recipe_name': 1,
                'url': 1,
                'portion': {
                    '$toInt': {
                        '$arrayElemAt': [{'$split': ['$portion', ' ']}, 0]
                    }
                }
            }
        },
        {
            '$sort': {
                'portion': -1
            }
        },
        {
            '$limit': 1
        }
    ]

    result = await collection.aggregate(pipeline).to_list(length=1)

    if result:
        recipe = result[0]
        print(
            f"Recipe with the most portion:\nName: {recipe['recipe_name']}\nURL: {recipe['url']}\nPortion: {recipe['portion']}")
    else:
        print("No recipes found with a valid portion.")


if __name__ == '__main__':
    asyncio.run(calculate_average_ingredients())
    asyncio.run(calculate_average_cooking_stage())
    asyncio.run(find_top_author())
    asyncio.run(find_recipe_with_most_portion())
