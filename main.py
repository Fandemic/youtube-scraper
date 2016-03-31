#!/usr/bin/python
"""
Title: Fandemic Social Media Star Finder

Description: Finds all youtubers related to specified
             keywords and subscriber count and gathers info.
             After that it branches off to other social Media
             outlets including Google+ and Instagram
             to finish gathering info.
"""

import csv
import thread
from apiclient.discovery import build
from apiclient.errors import HttpError
from oauth2client.tools import argparser
from optparse import OptionParser
import os.path
import re
import urllib2
from bs4 import BeautifulSoup as soup

#===============SETTINGS(only make changes here!)==============#
KEYWORDS = ["fitness","aesthetics","workout"]
MAX_NUM_RESULTS = 500
SEARCH_DEPTH = 4
MIN_SUBS = 10000
MAX_SUBS = 150000
#================================================================#

#===================== API KEYS =========================#
DEVELOPER_KEY = "AIzaSyCrr6e_SQhl64jKQnmkNZ2Xcf1EthBgBgU"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
#========================================================#

#=================================Shitty regex================================#
regex = re.compile(("([a-z0-9!#$%&'*+\/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+\/=?^_`"
                    "{|}~-]+)*(@|\sat\s)(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(\.|"
                    "\sdot\s))+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)"))
#==============================================================================#

#============================== MAIN ==========================================#
def main():

    try:

        for keyword in KEYWORDS:
            findStars(keyword)


    except HttpError, e:
        print "An HTTP error %d occurred:\n%s" % (e.resp.status, e.content)

#==============================================================================#


#=================== findChannels ==================#
#params -> query string
#params -> number of channels
#returns a big dictionary with the stars info
def findStars(query_string):

    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
    developerKey=DEVELOPER_KEY)

    pageToken = ""
    i = 1

    while (i <= SEARCH_DEPTH):
        channels = []
       # Call the search.list method to retrieve results matching the specified
       # query term.
        search_response = youtube.search().list(
         q=query_string,
         part="id",
         maxResults=50,
         regionCode="US",
         relevanceLanguage= "en",
         pageToken=pageToken,
         type="channel"
        ).execute()

        for search_result in search_response.get("items", []):

            if search_result["id"]["kind"] == "youtube#channel":

                channels.append(search_result["id"]["channelId"])

        pageToken = search_response["nextPageToken"]
        print "Page " + str(i) + "... " + pageToken


        print "Scraping Channels for page " + str(i)
        channelList = getChannels(channels,youtube) #generate list of parsed channels

        print "Getting youtube info for page " + str(i)
        stars = appendYoutubeInfo(channelList,youtube)

        print "Getting important URL's from page " + str(i)
        stars.update(getImportantURLs(stars))

        print "Getting Google+ info for page " + str(i)
        stars.update(appendGoogleInfo(stars))

        print "Checking Facebook for Email Address, page " + str(i)
        stars.update(appendFacebookInfo(stars))

        print "Checking Instagram for Email Address, page " + str(i)
        stars.update(appendInstagramInfo(stars))

        print "Generating CSV for page " + str(i)
        #Append to the csv
        toCSV(stars)

        i += 1


#============= get channels ==============#
#args -> comma seperated of youtube channels
def getChannels(channels,youtube):

    parsedChannels = []
    channelList = ",".join(channels)

    search_response = youtube.channels().list(
     part="statistics",
     id=channelList,
    ).execute()

    for search_result in search_response.get("items", []):

        subCount = search_result["statistics"]["subscriberCount"]
        viewCount = search_result["statistics"]["viewCount"]
        videoCount = search_result["statistics"]["videoCount"]
        ID = search_result["id"]

        if MIN_SUBS <= int(subCount) <= MAX_SUBS :
            parsedChannels.append(search_result["id"])

    return parsedChannels

#Add all the data for a youtube star that is missing
def appendYoutubeInfo(channels,youtube):

    stars = {}
    channelList = ",".join(channels)

    search_response = youtube.channels().list(
     part="snippet,contentDetails,brandingSettings",
     id=channelList,
    ).execute()


    #print search_response
    for search_result in search_response.get("items", []):

        #ID for reference
        ID = search_result["id"]
        stars[ID] = {}

        #Append the channel title, url, etc
        stars[ID]["name"] = search_result["snippet"]["title"]
        stars[ID]["store_url"] = "https://fandemic.co/" + search_result["snippet"]["title"].replace(' ', '-').replace("'","").lower()

        try:
            stars[ID]["googlePlusUserId"] = search_result["contentDetails"]["googlePlusUserId"]
        except KeyError:
            print stars[ID]["name"], "is missing a Google+ id"

        #Image
        stars[ID]["image"] = {}
        stars[ID]["image"]["banner"] = search_result["brandingSettings"]["image"]["bannerImageUrl"]
        #stars[ID]["image"]["profile"] = search_result["brandingSettings"]["image"]["watchIconImageUrl"]

        emails = get_emails(search_result["snippet"]["description"].lower())
        stars[ID]["email"] = []
        for email in emails:
            stars[ID]["email"].append(email)

    return stars


#Checks if the stars google+ profile has an email address
def appendGoogleInfo(stars):

    for key in stars:

        try:
            url = "https://plus.google.com/" + stars[key]["googlePlusUserId"] + "/about"

            try:
                web_soup = soup(urllib2.urlopen(url),'lxml')
            except:
                web_soup = soup(urllib2.urlopen(url),'lxml')

            contact = web_soup.find(name="div", attrs={'role': 'main'})
            emails = get_emails(str(contact).lower())
            for email in emails:
                stars[key]["email"].append(email)
        except KeyError:
            print "fuckin key error"

    return stars

def appendFacebookInfo(stars):

    for key in stars:

        if stars[key]["facebook_url"] != "":


            if stars[key]["facebook_url"].endswith('/'):
                stars[key]["facebook_url"] = stars[key]["facebook_url"][:-1]


            try:
                url = stars[key]["facebook_url"] + "/info/?tab=page_info"

                try:
                    web_soup = soup(urllib2.urlopen(url),'lxml')

                    infoString = web_soup.find(name="div", attrs={'data-id': 'page_info'})
                    emails = get_emails(str(infoString).lower())
                    for email in emails:
                        print email
                        stars[key]["email"].append(email)

                except urllib2.HTTPError:
                    print "Invalid Facebook URL Format :("
                except:
                    web_soup = soup(urllib2.urlopen(url),'lxml')

            except KeyError:
                print "fuckin key error"

    return stars


def appendInstagramInfo(stars):

    for key in stars:

        if stars[key]["instagram_url"] != "":


            if stars[key]["instagram_url"].endswith('/'):
                stars[key]["instagram_url"] = stars[key]["instagram_url"][:-1]


            try:
                url = url_formatter(stars[key]["instagram_url"])

                web_soup = soup(urllib2.urlopen(url),'lxml')

                infoString = web_soup.find('body')

                emails = get_emails(str(infoString).lower())
                for email in emails:
                    print email
                    stars[key]["email"].append(email)

            except urllib2.HTTPError:
                print "Invalid Instagram URL Format :("
            except KeyError:
                print "instagram fuckin key error"


    return stars


#Gets the important URLs from the users youtube page
def getImportantURLs(stars):

    for key in stars:

        stars[key]["twitter_url"] = ''
        stars[key]["facebook_url"] = ''
        stars[key]["instagram_url"] = ''

        try:
            url = "https://youtube.com/channel/" + key
            web_soup = soup(urllib2.urlopen(url),'lxml')

            data = web_soup.findAll('div',attrs={'id':'header-links'});
            for div in data:
                links = div.findAll('a')
                for a in links:

                    #print a['title'].lower(),a['href']
                    if a['title'].lower() == 'twitter':
                        stars[key]["twitter_url"] = a['href']
                    elif a['title'].lower() == 'facebook':
                        stars[key]["facebook_url"] = a['href']
                    elif a['title'].lower() == 'instagram':
                        stars[key]["instagram_url"] = a['href']

        except KeyError:
            print "fuckin key error"

    return stars


def toCSV(stars):
    with open('contacts.csv', 'a') as csvfile:
        writer = csv.writer(csvfile, delimiter=',',
                                quotechar='"', quoting=csv.QUOTE_MINIMAL)

        for key in stars:
            emails = ','.join(stars[key]["email"])

            try:
                writer.writerow([stars[key]["name"],
                                stars[key]["store_url"],
                                stars[key]["facebook_url"],
                                stars[key]["twitter_url"],
                                stars[key]["instagram_url"],
                                emails])
            except UnicodeEncodeError:
                print "Record failed to write to CSV because of unicode error";


def toMongoDB(stars):
    return 0


def get_emails(s):
    """Returns an iterator of matched emails found in string s."""
    # Removing lines that start with '//' because the regular expression
    # mistakenly matches patterns like 'http://foo@bar.com' as '//foo@bar.com'.
    return (email[0] for email in re.findall(regex, s) if not email[0].startswith('//'))

def url_formatter(url):
    if url.startswith('http://www.'):
        return 'https://' + url[len('http://www.'):]
    if url.startswith('www.'):
        return 'https://' + url[len('www.'):]
    if (url.startswith('https://') == False) and (url.startswith('http://') == False):
        return 'https://' + url
    return url

main()
