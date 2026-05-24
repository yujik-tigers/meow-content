import argparse
import asyncio

from script.scrap.base import RawDataScraper
from script.scrap.reddit_meme_scraper import RedditMemeScraper
from script.upload.base import RawDataUploader
from script.upload.local_mysql_uploader import LocalMySQLUploader
from script.upload.mysql_uploader import MySQLUploader

SCRAPERS = {
    "reddit_meme": RedditMemeScraper,
}

UPLOADERS = {
    "mysql": MySQLUploader,
    "local_mysql": LocalMySQLUploader,
}


async def main(scraper_type: str, uploader_type: str) -> None:
    scraper: RawDataScraper = SCRAPERS[scraper_type]()
    uploader: RawDataUploader = UPLOADERS[uploader_type]()

    raw_data = await scraper.scrap()
    entities = [item.to_entity() for item in raw_data]
    await uploader.upload(entities)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scraper-type",
        required=True,
        choices=list(SCRAPERS),
        help="사용할 scraper 종류",
    )
    parser.add_argument(
        "--uploader-type",
        required=True,
        choices=list(UPLOADERS),
        help="사용할 uploader 종류",
    )
    args = parser.parse_args()
    asyncio.run(main(args.scraper_type, args.uploader_type))
