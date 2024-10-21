from django.core.management.base import BaseCommand
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from scraping.section_scraper.section_scraper.spiders.sections import SectionsSpider  # Import spider

class Command(BaseCommand):
    help = 'Runs the section Scrapy spider'

    def handle(self, *args, **kwargs):
        process = CrawlerProcess(get_project_settings())  # Get Scrapy settings from your Scrapy project
        process.crawl(SectionsSpider)  # Run the spider
        process.start()  # Start the crawling process