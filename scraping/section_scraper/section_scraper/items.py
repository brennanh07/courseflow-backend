# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class SectionScraperItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    crn = scrapy.Field()
    course = scrapy.Field()
    class_type = scrapy.Field()
    modality = scrapy.Field()
    credit_hours = scrapy.Field()
    capacity = scrapy.Field()
    professor = scrapy.Field()
    days = scrapy.Field()
    begin_time = scrapy.Field()
    end_time = scrapy.Field()
    location = scrapy.Field()
    exam_code = scrapy.Field()
