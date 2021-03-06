#!/usr/bin/python
"""
Title: Fandemic Social Media Star Finder

Description: Finds all youtubers related to specified
             keywords and subscriber count and gathers info.
             After that it branches off to other social Media
             outlets including Google+ and Instagram
             to finish gathering info.
"""
import pymongo
from pymongo import MongoClient, errors
import csv
import thread
from apiclient.discovery import build
from apiclient.errors import HttpError
from oauth2client.tools import argparser
from optparse import OptionParser
import os.path
import re
import urllib2
from httplib import BadStatusLine
from bs4 import BeautifulSoup as soup

#===============SETTINGS(only make changes here!)==============#
KEYWORDS = ["fitness","aesthetics","workout","bodybuilding",
            "gym","lifting","crossfit","exercise","callisthenics", "isometrics"
            "strength","weightlifting","muscle","muscularity","fitness sports",
            "natural transformation", "fitness transformation",
            "athlete","fit women","aerobics","powerlifting","healthy eating", "training"]
MAX_SEARCH_DEPTH = 30
MIN_SUBS = 30000
MAX_SUBS = 10000000000
OUTPUT_FILE = "contacts_fitness_v2_MoneyMaker.csv"
#================================================================#

#===================== API KEYS =========================#
DEVELOPER_KEY = "AIzaSyCrr6e_SQhl64jKQnmkNZ2Xcf1EthBgBgU"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
#========================================================#

#=================================Email Regex================================#
regex = re.compile(("([a-z0-9!#$%&'*+\/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+\/=?^_`"
                    "{|}~-]+)*(@)(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(\.|"
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

    search_depth = MAX_SEARCH_DEPTH

    while (i <= search_depth):
        channels = []
        # Call the search.list method to retrieve results matching the specified
        # query term.

        try:
            search_response = youtube.search().list(
             q=query_string,
             part="id",
             maxResults=50,
             regionCode="US",
             relevanceLanguage= "en",
             pageToken=pageToken,
             type="channel"
            ).execute()
        except Exception, e:
            "can't connect.. WTF!!!! trying again"
            search_response = youtube.search().list(
             q=query_string,
             part="id",
             maxResults=50,
             regionCode="US",
             relevanceLanguage= "en",
             pageToken=pageToken,
             type="channel"
            ).execute()

        search_depth = search_response["pageInfo"]["totalResults"] / search_response["pageInfo"]["resultsPerPage"]

        for search_result in search_response.get("items", []):

            if search_result["id"]["kind"] == "youtube#channel":

                channels.append(search_result["id"]["channelId"])

        print "Scraping keyword " + query_string


        print "Scraping Channels for page " + str(i)
        channelList = getChannels(channels,youtube) #generate list of parsed channels

        print "Getting youtuber's info for page " + str(i)
        stars = appendYoutubeInfo(channelList,youtube)

        print "Getting social media URL's from page " + str(i)
        stars.update(getImportantURLs(stars))

        print "Checking Google+ for Enail Address, page " + str(i)
        stars.update(appendGoogleInfo(stars))

        print "Checking Facebook for Email Address, page " + str(i)
        stars.update(appendFacebookInfo(stars))

        print "Checking Instagram for Email Address, page " + str(i)
        stars.update(appendInstagramInfo(stars))

        print "Creating MongoDB/CSV records for page " + str(i)
        toMongoDB(stars)

        try:
            pageToken = search_response["nextPageToken"]
            print pageToken
        except KeyError:
            print "Max depth has been reached. Moving to next keyword."
            break

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
     part="snippet,statistics,contentDetails,brandingSettings",
     id=channelList,
    ).execute()


    #print search_response
    for search_result in search_response.get("items", []):

        #ID for reference

        ID =  search_result["snippet"]["title"].replace(" ","-").lower()
        stars[ID] = {}
        stars[ID]["id"] = search_result["snippet"]["title"].replace(" ","-").lower()

        #Append the channel title, url, etc
        stars[ID]["name"] = search_result["snippet"]["title"]

        #store url and youtube url
        stars[ID]["url"] = {}
        stars[ID]["url"]["store"] = "https://fandemic.co/" + search_result["snippet"]["title"].replace(' ', '-').replace("'","").lower()
        stars[ID]["url"]["youtube"] = "https://www.youtube.com/channel/" + search_result["id"]

        try:
            stars[ID]["googlePlusUserId"] = search_result["contentDetails"]["googlePlusUserId"]
        except KeyError:
            #print stars[ID]["name"], "is missing a Google+ id"
            pass

        #channel statistics
        stars[ID]["statistics"] = search_result["statistics"]

        #image
        stars[ID]["image"] = {}

        try:
            stars[ID]["image"]["banner"] = search_result["brandingSettings"]["image"]["bannerMobileHdImageUrl"]
        except KeyError:
            #print "Can't find the banner, providing the basic bitch one"
            pass
            try:
                stars[ID]["image"]["banner"] = search_result["brandingSettings"]["image"]["bannerMobileHdImageUrl"]
            except KeyError:
                #print "Basic bitch one did not work either. Looks like you're screwed..."
                pass

        #check for emails in description
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
            stars[key]["url"]["googlePlus"] = url

            try:
                web_soup = soup(urllib2.urlopen(url),'lxml')
            except:
                web_soup = soup(urllib2.urlopen(url),'lxml')

            contact = web_soup.find(name="div", attrs={'role': 'main'})
            emails = get_emails(str(contact).lower())
            for email in emails:
                stars[key]["email"].append(email)
        except KeyError:
            #print "fuckin key error"
            pass

    return stars

def appendFacebookInfo(stars):

    for key in stars:

        if stars[key]["url"]["facebook"] != "":


            if stars[key]["url"]["facebook"].endswith('/'):
                stars[key]["url"]["facebook"] = stars[key]["url"]["facebook"][:-1]


            try:
                url = stars[key]["url"]["facebook"] + "/info/?tab=page_info"

                try:
                    web_soup = soup(urllib2.urlopen(url),'lxml')

                    infoString = web_soup.find(name="div", attrs={'data-id': 'page_info'})
                    emails = get_emails(str(infoString).lower())
                    for email in emails:
                        #print email
                        stars[key]["email"].append(email)

                except urllib2.HTTPError:
                    #print "Invalid Facebook URL Format :("
                    pass
                except:
                    web_soup = soup(urllib2.urlopen(url),'lxml')

            except KeyError:
                print "fuckin key error"
                pass

    return stars


def appendInstagramInfo(stars):

    for key in stars:

        if stars[key]["url"]["instagram"] != "":


            if stars[key]["url"]["instagram"].endswith('/'):
                stars[key]["url"]["instagram"] = stars[key]["url"]["instagram"][:-1]


            try:
                url = url_formatter(stars[key]["url"]["instagram"])

                #print url

                web_soup = soup(urllib2.urlopen(url),'lxml')

                infoString = web_soup.find('body')

                emails = get_emails(str(infoString).lower())
                for email in emails:
                    #print email
                    stars[key]["email"].append(email)

            except urllib2.HTTPError:
                #print "Invalid Instagram URL Format :("
                pass
            except KeyError:
                #print "instagram fuckin key error"
                pass


    return stars


#Gets the important URLs from the users youtube page
def getImportantURLs(stars):

    for key in stars:

        stars[key]["url"]["twitter"] = ''
        stars[key]["url"]["facebook"] = ''
        stars[key]["url"]["instagram"] = ''

        try:
            url = stars[key]["url"]["youtube"]
            web_soup = soup(urllib2.urlopen(url),'lxml')

            #Get all the social media url's
            social_urls = web_soup.findAll('div',attrs={'id':'header-links'});
            for div in social_urls:
                links = div.findAll('a')
                for a in links:

                    #print a['title'].lower(),a['href']
                    if a['title'].lower() == 'twitter':
                        stars[key]["url"]["twitter"] = a['href']
                    elif a['title'].lower() == 'facebook':
                        stars[key]["url"]["facebook"] = a['href']
                    elif a['title'].lower() == 'instagram':
                        stars[key]["url"]["instagram"] = a['href']

            #Get the users youtube profile photo
            profile_img = web_soup.find('img',attrs={'class':'channel-header-profile-image'})['src'];
            stars[key]["image"]["profile"] = profile_img.replace("100", "500") #changes image size


        except KeyError:
            #print "fuckin key error"
            pass

    return stars



def toCSV(star):

    with open(OUTPUT_FILE, 'a') as csvfile:
        writer = csv.writer(csvfile, delimiter=',',
                                quotechar='"', quoting=csv.QUOTE_MINIMAL)

        star["email"] = list(set(star["email"]))
        emails = ','.join(star["email"])

        try:
            writer.writerow([star["name"],
                            star["url"]["store"],
                            star["statistics"]["subscriberCount"],
                            star["statistics"]["viewCount"],
                            star["url"]["facebook"],
                            star["url"]["instagram"],
                            emails])
        except UnicodeEncodeError:
            #print "Record failed to write to CSV because of unicode error"
            pass



def toMongoDB(stars):

    client = MongoClient('45.79.159.210', 27017)
    db = client.fandemic

    #Open mongoDB database
    for key in stars:

        stars[key]['active'] = False
        stars[key]['category'] = "fitness"

        #checks if the stars ID is unique
        try:
            result = db.stars.insert_one(stars[key])
            toCSV(stars[key])
        except pymongo.errors.DuplicateKeyError:
            #print "Star is already in DB bro!"
            pass

    client.close()


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
