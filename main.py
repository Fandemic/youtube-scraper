#!/usr/bin/python
#Fandemic YouTube Scraper
#main.py

from apiclient.discovery import build
from apiclient.errors import HttpError
from oauth2client.tools import argparser

DEVELOPER_KEY = "AIzaSyCrr6e_SQhl64jKQnmkNZ2Xcf1EthBgBgU"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"


def findChannels():
  youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
    developerKey=DEVELOPER_KEY)

  # Call the search.list method to retrieve results matching the specified
  # query term.
  search_response = youtube.search().list(
    q="Fitness,workout,gym",
    part="id",
    maxResults=50,
    type="channel"
  ).execute()

  channels = []

  # Add each result to the appropriate list, and then display the lists of
  # matching videos, channels, and playlists.
  for search_result in search_response.get("items", []):

    if search_result["id"]["kind"] == "youtube#channel":

      channels.append(search_result["id"]["channelId"])


  print "Channels:\n", ",".join(channels)



if __name__ == "__main__":

  try:
    youtube_search()
  except HttpError, e:
    print "An HTTP error %d occurred:\n%s" % (e.resp.status, e.content)
