#!/usr/bin/env python

# Based on forked gist :https://gist.github.com/vishwanath79/eb9e4e4e821b3ae02e2ecadd8326a70a

import argparse
import re
import smtplib
from datetime import datetime
from time import time

import colorlog
import requests
from lxml import html

from Config import send, rec, key

logger = colorlog.getLogger()


def parse(locality, checkin_date, checkout_date, sort, hotelname):
    checkIn = checkin_date.strftime("%Y/%m/%d")
    checkOut = checkout_date.strftime("%Y/%m/%d")
    logger.info("Scraper Inititated for Locality:%s" % locality)
    # TA rendering the autocomplete list using this API
    logger.info("Finding search result page URL")
    geo_url = 'https://www.tripadvisor.com/TypeAheadJson?action=API&startTime=' + str(int(
        time())) + '&uiOrigin=GEOSCOPE&source=GEOSCOPE&interleaved=true&types=geo,theme_park&neighborhood_geos=true&link_type=hotel&details=true&max=12&injectNeighborhoods=true&query=' + locality
    api_response = requests.get(geo_url).json()
    # getting the TA url for th equery from the autocomplete response
    url_from_autocomplete = "http://www.tripadvisor.com" + api_response['results'][0]['url']
    logger.info('URL found %s' % url_from_autocomplete)
    geo = api_response['results'][0]['value']
    # Formating date for writing to file

    date = checkin_date.strftime("%Y_%m_%d") + "_" + checkout_date.strftime("%Y_%m_%d")
    # form data to get the hotels list from TA for the selected date
    form_data = {
        'adults': '2',
        'dateBumped': 'NONE',
        'displayedSortOrder': sort,
        'geo': geo,
        'hs': '',
        'isFirstPageLoad': 'false',
        'rad': '0',
        'refineForm': 'true',
        'requestingServlet': 'Hotels',
        'rooms': '1',
        'scid': 'null_coupon',
        'searchAll': 'false',
        'seen': '0',
        'sequence': '7',
        'o': "0",
        'staydates': date
    }
    # Referrer is necessary to get the correct response from TA if not provided they will redirect to home page
    headers = {
        'Accept': 'text/javascript, text/html, application/xml, text/xml, */*',
        'Accept-Encoding': 'gzip,deflate',
        'Accept-Language': 'en-US,en;q=0.5',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
        'Host': 'www.tripadvisor.com',
        'Pragma': 'no-cache',
        'Referer': url_from_autocomplete,
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:28.0) Gecko/20100101 Firefox/28.0',
        'X-Requested-With': 'XMLHttpRequest'
    }
    logger.info("Downloading search results page")
    page_response = requests.post(url="https://www.tripadvisor.com/Hotels", data=form_data, headers=headers).text
    # print(page_response)
    logger.info("Parsing results ")
    parser = html.fromstring(page_response)
    hotel_lists = parser.xpath('//div[contains(@class,"hotel_content easyClear sem")]')
    # print(hotel_lists)
    hotel_data = []
    for hotel in hotel_lists:
        XPATH_HOTEL_LINK = './/div[@class="listing_title"]/a/@href'

        XPATH_REVIEWS = './/span[@class="more review_count"]//text()'
        XPATH_RANK = './/div[@class="popRanking"]//text()'
        XPATH_RATING = './/div[@class="rating"]//span[contains(@class,"bubble_rating")]/@alt'
        XPATH_HOTEL_NAME = './/a[contains(@class,"property_title")]//text()'
        XPATH_HOTEL_FEATURES = './/a[contains(@class,"tag")]/text()'
        XPATH_HOTEL_PRICE = './/div[contains(@class,"price")]/text()'
        XPATH_VIEW_DEALS = './/div[contains(@id,"VIEW_ALL_DEALS")]//span[@class="taLnk"]/text()'
        XPATH_BOOKING_PROVIDER = './/div[contains(@class,"providerLogo")]/img/@alt'

        raw_booking_provider = hotel.xpath(XPATH_BOOKING_PROVIDER)
        raw_no_of_deals = hotel.xpath(XPATH_VIEW_DEALS)
        raw_hotel_link = hotel.xpath(XPATH_HOTEL_LINK)
        raw_no_of_reviews = hotel.xpath(XPATH_REVIEWS)
        raw_rank = hotel.xpath(XPATH_RANK)
        raw_rating = hotel.xpath(XPATH_RATING)
        raw_hotel_name = hotel.xpath(XPATH_HOTEL_NAME)
        raw_hotel_features = hotel.xpath(XPATH_HOTEL_FEATURES)
        raw_hotel_price_per_night = hotel.xpath(XPATH_HOTEL_PRICE)

        url = 'http://www.tripadvisor.com' + raw_hotel_link[0] if raw_hotel_link else  None

        reviews = re.findall('(\d+\,?\d+)', raw_no_of_reviews[0])[0].replace(',', '') if raw_no_of_reviews else None
        #rank = ''.join(raw_rank) if raw_rank else None
        rating = ''.join(raw_rating).replace(' of 5 bubbles', '') if raw_rating else None
        name = ''.join(raw_hotel_name).strip() if raw_hotel_name else None
        hotel_features = ','.join(raw_hotel_features)

        price_per_night = ''.join(raw_hotel_price_per_night).replace('\n', '') if raw_hotel_price_per_night else None
        no_of_deals = re.sub('\D+', '', ''.join(raw_no_of_deals)) if raw_no_of_deals else None
        # no_of_deals = re.sub('\D+','',no_of_deals)
        booking_provider = ''.join(raw_booking_provider).strip() if raw_booking_provider else None

        data = {
            'hotel_name': name,
            'url': url,
            'locality': locality,
            'reviews': reviews,
            'tripadvisor_rating': rating,
            'checkOut': checkOut,
            'checkIn': checkIn,
            'hotel_features': hotel_features,
            'price_per_night': price_per_night,
            'no_of_deals': no_of_deals,
            'booking_provider': booking_provider

        }
        hotel_data.append(data)
    # return hotel_data
    target = []
    for row in hotel_data:
        if row['hotel_name'] == hotelname:
            # return (row['hotel_name'], "--", row["checkIn"], "--", row["checkOut"], " PRICE -- ", row["price_per_night"])
            targethotel = row['hotel_name'], "--", row["checkIn"], "--", row["checkOut"], " PRICE -- ", row[
                "price_per_night"]
            # print(targethotel)
            # return str(targethotel)
            target.append(targethotel)
            boilerplate = "\n----------------------ALL OTHER HOTELS--------------------------------------------------------\n"
            target.append(boilerplate)

        for row in hotel_data:
        # return (row['hotel_name'], "--", row["checkIn"], "--", row["checkOut"], " PRICE -- ",row["price_per_night"])
        targethotels = row['hotel_name'], "--", row["checkIn"], "--", row["checkOut"], " PRICE -- ", row[
            "price_per_night"]
        # print(targethotels)
        target.append(targethotels)

    # print(target)
    return '\n'.join(''.join(str(t)) for t in target)


if __name__ == '__main__':
    # LOGGING SETUP
    logger.setLevel(colorlog.colorlog.logging.INFO)
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter())
    logger.addHandler(handler)

    parser = argparse.ArgumentParser()
    parser.add_argument('checkin_date', help='Hotel Check In Date (Format: YYYY/MM/DD')
    parser.add_argument('checkout_date', help='Hotel Chek Out Date (Format: YYYY/MM/DD)')
    sortorder_help = """
    available sort orders are :\n
    priceLow - hotels with lowest price,
    distLow : Hotels located near to the search center,
    recommended: highest rated hotels based on traveler reviews,
    popularity :Most popular hotels as chosen by Tipadvisor users 
    """
    parser.add_argument('sort', help=sortorder_help, default='priceLow ')
    parser.add_argument('locality', help='Search Locality')
    parser.add_argument('hotelname', help='Specific hotel name')
    args = parser.parse_args()
    locality = args.locality
    checkin_date = datetime.strptime(args.checkin_date, "%Y/%m/%d")
    checkout_date = datetime.strptime(args.checkout_date, "%Y/%m/%d")
    sort = args.sort
    checkIn = checkin_date.strftime("%Y/%m/%d")
    checkOut = checkout_date.strftime("%Y/%m/%d")
    today = datetime.now()
    hotelname = args.hotelname
    if today < datetime.strptime(checkIn, "%Y/%m/%d") and datetime.strptime(checkIn, "%Y/%m/%d") < datetime.strptime(
            checkOut, "%Y/%m/%d"):
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.ehlo()
        server.starttls()
        server.login(send, key)
        logger.info("Getting news")
        msg = parse(locality, checkin_date, checkout_date, sort, hotelname)
        server.sendmail(send, rec, msg.encode('ascii', 'replace'))
        logger.info("Sending mail")
        server.quit()



    # checking whether the entered date is already passed
    elif today > datetime.strptime(checkIn, "%Y/%m/%d") or today > datetime.strptime(checkOut, "%Y/%m/%d"):
        print("Invalid Checkin date: Please enter a valid checkin and checkout dates,entered date is already passed")

    elif datetime.strptime(checkIn, "%Y/%m/%d") > datetime.strptime(checkOut, "%Y/%m/%d"):
        print("Invalid Checkin date: CheckIn date must be less than checkOut date")
