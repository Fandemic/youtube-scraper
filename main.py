#!/usr/bin/python
"""
Title: Fandemic Social Media Star Finder

Description: Finds all youtubers related to specified
             keywords and subscriber count and gathers info.
             After that it branches off to other social Media
             outlets including Google+ and Instagram
             to finish gathering info.
"""

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
KEYWORDS = ["gym","fitness","aesthetics","bodybuilding","workout"]
MAX_NUM_RESULTS = 500
SEARCH_DEPTH = 5
MIN_SUBS = 10000
MAX_SUBS = 100000
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

#==============================================================================#
stars = {}
#==============================================================================

#============================== MAIN ==========================================#
def main():

    try:

        #stars = findStars("makeup",300)
        thread.start_new_thread( findStars, ("bodybuilding", 150) )
        thread.start_new_thread( findStars, ("aesthetics", 150) )

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
def findStars(query_string,num_channels):

    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
    developerKey=DEVELOPER_KEY)

    pageToken = ""
    i = 50

    while (i <= num_channels):
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
        print "Page " + str(i/50) + "... " + pageToken

        i += 50

        #channelList = ",".join(channels)
        channelList = getChannels(channels,10000,100000,youtube) #generate list of parsed channels
        tempStars = appendYoutubeInfo(channelList,youtube)
        stars.update(appendGoogleInfo(tempStars))


#============= get channels ==============#
#args -> comma seperated of youtube channels
def getChannels(channels,min_fc,max_fc,youtube):

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

        if min_fc <= int(subCount) <= max_fc :
            parsedChannels.append(search_result["id"])

    print ""
    for channel in parsedChannels:
        print channel

    return parsedChannels

#Add all the data for a youtube star that is missing
def appendYoutubeInfo(channels,youtube):

    tempStars = {}
    channelList = ",".join(channels)

    search_response = youtube.channels().list(
     part="snippet,statistics,contentDetails,brandingSettings",
     id=channelList,
    ).execute()


    #print search_response
    for search_result in search_response.get("items", []):

        #print search_result
        ID = search_result["id"]


        emails = get_emails(search_result["snippet"]["description"])
        for email in emails:
            print email



        tempStars[ID] = search_result["contentDetails"]

    return tempStars


#Checks if the stars google+ profile has an email address
def appendGoogleInfo(tempStars):

    for key in tempStars:

        try:
            url = "https://plus.google.com/" + tempStars[key]["googlePlusUserId"] + "/about"
            web_soup = soup(urllib2.urlopen(url),'lxml')
            contact = web_soup.find(name="div", attrs={'role': 'main'})
            emails = get_emails(str(contact))
            for email in emails:
                print email
                tempStars[key]["email"] = email
        except KeyError:
            print "fuckin key error"

    return tempStars

#Append the description
def appendInstaInfo(stars):
    return 0

def get_emails(s):
    """Returns an iterator of matched emails found in string s."""
    # Removing lines that start with '//' because the regular expression
    # mistakenly matches patterns like 'http://foo@bar.com' as '//foo@bar.com'.
    return (email[0] for email in re.findall(regex, s) if not email[0].startswith('//'))


main()
