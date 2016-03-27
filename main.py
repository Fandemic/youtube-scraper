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
KEYWORDS = ["gym","fitness"]
MAX_NUM_RESULTS = 500
SEARCH_DEPTH = 1
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
            thread.start_new_thread( findStars, (keyword, 150) )

        '''
        for key in stars:
          try:
              print stars[key]["googlePlusUserId"]
              #print stars[key]["email"]
          except KeyError:
              print "error"
        '''

    except HttpError, e:
        print "An HTTP error %d occurred:\n%s" % (e.resp.status, e.content)
    except:
        print "Error: unable to start thread"

    while 1:
        pass
#==============================================================================#


#=================== findChannels ==================#
#params -> query string
#params -> number of channels
#returns a big dictionary with the stars info
def findStars(query_string, num):

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

        i += 1

        #channelList = ",".join(channels)
        channelList = getChannels(channels,youtube) #generate list of parsed channels
        stars = appendYoutubeInfo(channelList,youtube)
        stars.update(appendGoogleInfo(stars))

        #Append to the csv
        toCSV(stars)


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

    print ""
    for channel in parsedChannels:
        print channel

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
        ID = search_result["id"]
        stars[ID] = {}

        #Append the channel title, url, etc
        stars[ID]["name"] = search_result["snippet"]["title"]
        stars[ID]["store_url"] = "https://fandemic.co/" + search_result["snippet"]["title"].replace(' ', '-').replace("'","").lower()
        stars[ID]["googlePlusUserId"] = search_result["contentDetails"]["googlePlusUserId"]
        print stars[ID]["store_url"]

        emails = get_emails(search_result["snippet"]["description"])
        stars[ID]["email"] = []
        for email in emails:
            stars[ID]["email"].append(email)
            print email


    return stars


#Checks if the stars google+ profile has an email address
def appendGoogleInfo(stars):

    for key in stars:

        try:
            url = "https://plus.google.com/" + stars[key]["googlePlusUserId"] + "/about"
            web_soup = soup(urllib2.urlopen(url),'lxml')
            contact = web_soup.find(name="div", attrs={'role': 'main'})
            emails = get_emails(str(contact))
            for email in emails:
                print email
                stars[key]["email"].append(email)
        except KeyError:
            print "fuckin key error"

    return stars

#Append the description
def appendInstaInfo(stars):
    return 0

def toCSV(stars):
    with open('contacts.csv', 'a') as csvfile:
        writer = csv.writer(csvfile, delimiter=',',
                                quotechar='"', quoting=csv.QUOTE_MINIMAL)

        for key in stars:
            emails = ','.join(stars[key]["email"])
            writer.writerow([stars[key]["name"],
                            stars[key]["store_url"],
                            emails])

def toMongoDB(stars):
    return 0


def get_emails(s):
    """Returns an iterator of matched emails found in string s."""
    # Removing lines that start with '//' because the regular expression
    # mistakenly matches patterns like 'http://foo@bar.com' as '//foo@bar.com'.
    return (email[0] for email in re.findall(regex, s) if not email[0].startswith('//'))


main()
