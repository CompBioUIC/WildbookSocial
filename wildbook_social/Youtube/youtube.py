# from googleapiclient.discovery import build
import googleapiclient.discovery
import time
import csv
import dateutil.parser
# import database as db

class YouTube:
    def __init__(self, KEY, db=None):
        self._YOUTUBE_API_SERVICE_NAME = 'youtube'
        self._YOUTUBE_API_VERSION = 'v3'
        self._KEY = KEY
        self.youtube = googleapiclient.discovery.build(self._YOUTUBE_API_SERVICE_NAME, self._YOUTUBE_API_VERSION, 
                             developerKey=self._KEY)
        self.db = db
        self.nextPageToken = None
        self.page = 1
    
    # Uses youtube.search() API method
    def search(self, q, limit=1, saveTo=False):
        ''' 
        q - search query, (ex. "Whale Shark")
        limit - number of results (ex. 10 or 100)
        fields - Retrieve only selected fields (ex. True, False)
        saveTo - Saves all retrieved videos to provided collection
        '''
        if (saveTo and not self.db):
            saveTo = False
            print("Please provide 'db' argument with an instance to database to save video(s).")
            
        # Going through pages in result
        self.results = []
        while(limit > 0):
            print("Working with page", self.page)
            
            # Quering the result
            searchResult = self.youtube.search().list(
                q=q,
                part='snippet',
                #order = 'date',
                fields='nextPageToken,items(id,snippet(publishedAt,title))',
                type='video',
                maxResults=50 if limit>50 else limit,
                pageToken=self.nextPageToken if self.nextPageToken else '',
#                 publishedAfter = "2019-07-20T00:00:00Z",
#                 publishedBefore = "2019-07-26T00:00:00Z"
                # 06.11.20 edited to search with a more general term for a week
                publishedAfter = "2019-06-01T00:00:00Z", #only gather results from June 01 2019 and forwards
            ).execute()
            items = searchResult['items']
            
            self.nextPageToken = searchResult['nextPageToken']
            self.page += 1
            limit -= 50

            # Going through each result
            modifiedResult = []
            for item in items:

                # Quering more details for this result
                details = self.videos(item['id']['videoId'], fields=True)
                for prop in details[0]:
                    try:
                        item[prop].update(details[0][prop])
                    except KeyError:
                        item[prop] = details[0][prop]

                # WILDBOOK FORMAT
                # try:
                newItem = {
                    "_id": item['id']['videoId'],
                    "channelId" : item['snippet'].get('channelId', 0), #added to count posts per user
                    "videoID": item['id']['videoId'],
                    "title": {
                        "original": item['snippet'].get('title', None),
                        "eng": None, #[Microsoft translate]
                    },
                    "tags": {
                        "original": item['snippet'].get('tags', []),
                        "eng": [], #[Microsoft translate]
                    },
                    "description": {
                        "original": item['snippet'].get('description', None),
                        "eng": None, #[Microsoft translate]
                    },
                    "OCR": {
                        "original": [], #[Azure]
                        "eng": [], #[Azure, Microsoft translate]
                    },
                    "url": 'https://youtu.be/' + item['id']['videoId'],
                    "animalsID": [], #[Wildbook]
                    "curationStatus": None, #[Wildbook]
                    "curationDecision": None, #[Wildbook]
                    "publishedAt": dateutil.parser.parse(item['snippet'].get('publishedAt', 0)),
                    "uploadedAt": None, #[YouTube]
                    "duration": None, #[YouTube]
                    "regionRestriction": None, #[YouTube]
                    "viewCount": item['statistics'].get('viewCount', None),
                    "likeCount": item['statistics'].get('likeCount', None),
                    "dislikeCount": item['statistics'].get('dislikeCount', None),
                    "recordingDetails": {
                        "location": None, #[YouTube]
                        "date": None, #[YouTube]
                    },
                    "encounter": {
                        "locationIDs": [], #[Wildbook]
                        "dates": [], #[Wildbook]
                    },
                    "fileDetails": None, #[YouTube]
                    "gatheredAt": time.ctime(),
                    "relevant": None,
                    "wild": None
                }

                # Saving item in database
                if (saveTo):
                    self.db.addItem(newItem, saveTo)
                modifiedResult.append(newItem)
            
            # Appending result to all previous search results
            self.results += modifiedResult
        
        print("Done!")
        return self.results
    
        
    # Retrieve info about specific video(s)
    def videos(self, id, fields=False):
        searchResult = self.youtube.videos().list(
            part='snippet,statistics',
            fields='items(snippet(channelId,description,tags),statistics)' if fields else '*',
            id=id
        ).execute()

        return searchResult['items']
    
    def getChannelIds(self, list_of_video_ids):
        video_channel = {} #{videoID:channelID}
        #get channelID list from videoID list
        for video_id in list_of_video_ids:
            video_result = self.youtube.videos().list(id = video_id, part ='snippet').execute()
            for item in video_result['items']:
                channel_id = item['snippet'].get('channelId', None)
                #channel_id_list.append(channel)
                video_channel[video_id] = channel_id
        return video_channel #channel_id_list,

        #Part I: 05-09-20 Get ChannelID's from list of videoIDs
        # 1.split list of video ids into smaller lists of 50
        # api only lets us feed in 50 results at a time
        #FIXME: this code works *sometimes* - most times, we are missing results so will get back to this
#         video_ids_split = [list_of_video_ids[x:x+50] for x in range(0, len(list_of_video_ids), 50)]
#         list_of_channel_ids = []
#         dic = {}
#         for sub_list in video_ids_split: 
#             str_of_video_ids = ', '.join(sub_list) #Hxj-iHHAa24, NIi_ewCqOqI' this is the format to follow 
#             print(str_of_video_ids)
#             video_search_result = self.youtube.videos().list(id = str_of_video_ids, part ='snippet').execute()
#             for item in video_search_result['items']:
#                 video_id = item['id']
#                 channel_id = item['snippet'].get('channelId', 'None')
#                 dic[video_id] = channel_id
#         return dic
    
    def getUserCountries(self, video_channel):
#         n = 49
        #1. break channel id list into lists of 50 (max) and use this with channels method
#         channel_id_list_broken = [channel_id_list[i * n:(i + 1) * n] for i in range((len(channel_id_list) + n - 1) // n )]  
#         for x in channel_id_list_broken:
#             x = ','.join(x)
#             while(nextPageToken != '')
#                 res = self.youtube.channels().list(part = 'snippet', \
#                                                    id = x, \
#                                                    nextPageToken = nextPageToken if nextPageToken else '').execute() 
#                 nextPageToken = res['nextPageToken']

         #1. (alternative slower method) - Query one by one
        channel_country = {} #{channelID: country, ....}
        combined_dictionaries = [] #[{videoId: , channelId: , user_country: }, {...}]
        #for channelID in channel_id_list:
        for video_id in video_channel.keys():
            channelID = video_channel[video_id]
            channel_res = self.youtube.channels().list(part = 'snippet', id = channelID).execute()
            
            for item in channel_res['items']:
                channel_country[channelID] = item['snippet'].get('country', 0) 
            
            dic = {'videoId': video_id,
                   'channelId': channelID,
                   'user_country': channel_country[channelID]
                  }
            combined_dictionaries.append(dic)
        return combined_dictionaries #channel_country, 
        
