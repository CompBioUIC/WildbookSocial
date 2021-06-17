##organized Database Class
from pymongo import MongoClient
import pprint
from IPython.display import YouTubeVideo, Image, display, Video

import matplotlib.pyplot as plt
import csv
import pandas as pd 
import numpy as np
import itertools
pd.options.mode.chained_assignment = None  # default='warn'

import datetime
from datetime import date
from datetime import timedelta
import time
import dateutil.parser

import mimetypes, urllib3
import requests


## class to support database operations done on items in mongoDB
class Database:
    
    def __init__(self, key, database):
        self.client = MongoClient(key)
        self.dbName = database
        self.db = self.client[database]
        self.dateStr = '2019-03-01T00:00:00.00Z' #timeframe begins March 2019
        self.timeFrameStart = dateutil.parser.parse(self.dateStr)
        self.timeFrameEnd = dateutil.parser.parse('2020-03-01T00:00:00.00Z') #changed timeframe to end March 2020
        
        
    ## add a new doc to collection
    def addItem(self, payload, collection):
        if self.dbName == 'iNaturalist':
            if self.db[collection].find_one(payload) == None:
                self.db[collection].insert_one(payload);
        else:
            try:
                self.db[collection].insert_one(payload)
            except:
                pass # Item already exists in database
    
    
    ## return whole db object
    def getDB(self):
        return self.db
    
    
    ## return a db collection object
    def returnDbCol(self, saveTo):
        return self.db[saveTo]
    
    
    def renameCollection(self, oldCollection, newCollection):
        self.db[oldCollection].rename(newCollection)
        print('{} renamed to {}'.format(oldCollection, newCollection))
        return
    
    ## update an existing item's field in collection
    def _updateItem(self, collection, id, payload):
        try:
            self.db[collection].update_one({"_id": id}, {"$set": payload})
            return True
        except(e):
            print("Error updating item", e)
            return False
    
    
    ## method to rename 'url_l' field in flickr collections to just 'url'
    def renameField(self, collection, oldName, newName):
        self.db[collection].update({}, {'$rename' : {oldName : newName}}, upsert=False, multi=True)
        return
    
    
    ## method to convert the 'time observed' field to UTC format across different platforms' collections
    def convertToUTC(self, collection):
        
        #update unsorted and wild documents
        res = self.db[collection].find({"$or":[{"relevant":None}, {"relevant": True}, {"captive": False}]})
        
        for doc in res:
            #youtube
            if self.dbName == 'youtube':
                date_str = doc['publishedAt']
                field = 'publishedAt'
            
            #iNaturalist has two fields regarding times that need to be converted
            if self.dbName == 'iNaturalist':
                date_str = doc['time_observed_utc']
                field = 'time_observed_utc'
                date_str_2 = doc['created_on']
                field_2 = 'created_on'
            
            #flickr
            if self.dbName == 'flickr_june_2019':
                try:
                    date_str = doc['datetaken']
                    field = 'datetaken'
                except KeyError:
                    date_str = None
            
            #twitter
            if self.dbName == 'twitter':
                date_str = doc['created_at']
                field = 'created_at'
            
            #update the corresponding time field with the UTC datetime object (not a string)
            if type(date_str) == str and date_str != None:
                doc_id = doc['_id']
                datetime_obj = dateutil.parser.parse(date_str)
                self.db[collection].update_one({'_id': doc_id}, {'$set':{ field: datetime_obj}})
                
                #for iNaturalist, also update the second time field
                if self.dbName == "iNaturalist":
                    datetime_obj_2 = dateutil.parser.parse(date_str_2)
                    self.db[collection].update_one({'_id': doc_id}, {'$set':{ field_2: datetime_obj_2}})

   
    ## method to remove duplicate documents for iNaturalist mongoDB collection of interest
    def removeDuplicatesiNat(self, collection):
        
        res = self.db[collection].find()
        
        for item in res:
            if not item:
                print('No more items') ##no more items to filter in collection
                break
            
            else:
                #find all duplicates in current collection
                dup = self.db[collection].find({"$and": [{"_id": {"$ne":item["_id"]}}, {"id": item["id"]}]})

                numDuplicates = len(list(dup))
                print("numDuplicate: ", numDuplicates)
                
                if numDuplicates > 0:
                    print("numDups is > 0.. deleting duplicate docs...")
                    
                    #delete all existing duplicates from collection
                    while(numDuplicates > 0):
                        pipeline = {"$and": [{"_id": {"$ne":item["_id"]}}, {"id": item["id"]}]}
                        self.db[collection].remove(pipeline)
                        numDuplicates -= 1
                    
        print("Finished removing duplicates from collection")
    
    
    ## removes duplicate docs from flickr collection and returns bool value indicating if duplicates
    ## were found
    def removeDuplicatesFlickr(self, item, collection):
        
        duplicate_res = self.db[collection].find_one({'$and': [{'id':item['id']}, {'relevant':{"$ne": None}}]})
        
        #delete duplicate docs
        if duplicate_res != None:
            self.db[collection].remove({'$and': [{'id': item['id']}, {'relevant': None}]})
            return True
        
        return False
    
    def is_url_image(self, image_url):
        image_formats = ("image/png", "image/jpeg", "image/jpg")
        r = requests.head(image_url)
        if r.headers["content-type"] in image_formats:
            return True
        return False
    
    ## method to manually filter documents in platform collections
    ## displays image/video to user and asks for relevance and wild/captive classification
    ## method then proceeds to update 'relevant' and 'wild' fields for doc in mongoDB
    ## note- iNaturalist does not require manual filtration
    ## previously named doStatistics()
    def doManualFiltration(self, collection, amount):
        
        #counter variables
        i = 1
        count = 0
        
        #keep filtering as long as unsorted docs are in our collection
        while(amount > 0):
            
            print("Amount: ", amount)
            
            #only retrieve videos to filter that meet the time frame of June 1st, 2019 and forward
            if self.dbName == 'youtube':
                item = self.db[collection].find_one({"$and":[{"relevant": None},\
                                                             {"publishedAt":{"$gte": self.timeFrameStart}}]})
                if not item:
                    break
                                   
            #flickr - find an unsorted item and check for duplicates
            elif self.dbName == 'flickr_june_2019':
                
                #get an item that hasn't been manually filtered
                item = self.db[collection].find_one({'relevant': None})
                
                #if the item is empty - we ran out of docs
                if item == None:
                    print("No more items to filter through - exiting..")
                    break
               
                #remove duplicates if present, and keep searching through docs
                if self.removeDuplicatesFlickr(item, collection):
                    count += 1
                    amount -= 1
                    i += 1
                    continue

            #display image/videos
            try:
                if self.dbName=='youtube':
                    print("{}: {}".format(i, item['title']['original']))
                    display(YouTubeVideo(item['_id']))

                elif self.dbName == 'flickr_june_2019':
                    # try-except handles some documents having the new, updated name 'url' field rather than
                    # the 'url_l' (original, older version) 
                    
                    try:
                        img_url = item['url']
                    except KeyError:
                        img_url = item['url_l']
                    
                    print(img_url) #just checking url
                    
                    if img_url != "" and self.is_url_image(img_url):
                        display(Image(img_url, height=500, width=500))
                        print('Title: {}\nTags: {}\n(Lat, Long): ({},{})\n'.format(item['title'], item['tags'], item['latitude'], item['longitude']))
                        
                    else:
                        print('URL no longer valid/working ... Removing Document ... ')
                        self.db[collection].remove({'id': item['id']})
                        continue
                        

                # prompt user for relevance classification
                print("Relevant (y/n):", end =" ")
                rel = True if input() == "y" else False 

                # For YouTube, location may be specified in title or in video
                # 'loc' allows user to input a location of encounter, if available
                loc = 0 

                # prompt user for wild or captive classification
                if rel == True:
                    print("Wild(y/n):", end =" ")
                    wild = True if input() == 'y' else False 
                    
                    #prompt user with option to enter location only if encounter is wild (YT videos only)
                    if (self.dbName == 'youtube' and wild == True):
                        print("Is there a location? (y/n):", end = " ")
                        if input() == "y": loc = input()

                # irrelevant posts don't need to be labeled as wild/captive            
                if rel == False: wild = 0  

                #update doc (item) with new values
                if self.dbName == 'youtube':
                    self._updateItem(collection, item['_id'], {"relevant": rel, "wild": wild, "newLocation": loc })
                    print("Response saved! Location : {}.\n".format(loc))

                else:
                    self._updateItem(collection, item['_id'], {"relevant": rel, "wild": wild})

                print("Response saved! {} and {}.\n".format("Relevant" if rel else "Not relevant", "Wild" if wild else "Not wild"))
            
            except FileNotFoundError:
                pass
            
            #update amount of items in collection that need to be filtered
            amount -= 1
            i += 1
            
        print('No more items to proceed.')     
      
    ## structures a dictionary containing the number of posts per week within the time frame
    ## as such: {week_0: 2, week_1: 15, week_2: 37 ...} from a list of dates
    def postsPerWeek(self, dates):
        self.dates = dates
        start = self.timeFrameStart.date()
        end = self.timeFrameEnd.date()#datetime.date.today()
        weekNumber = 1
        count = 0
        self.dictWeekNumbers = {}
        self.postsPerWeekDict = {}
        numOfPosts = len(self.dates)

        #make a dictionary to order weekStartDates
        #format of self.dictWeekNumbers = { 1 : 06.01.19, 2: 06.08.19, 3:06.15.19 ... }
        date = start
        while date < end:
            self.dictWeekNumbers[weekNumber] = date 
            date += datetime.timedelta(days = 7)
            weekNumber += 1
    
        #make a dictionary self.postsPerWeek
        #keys are datetime objects of the date to start a new week
        #values are number of posts that were posted anytime from that date to date + 6 days
        #format self.postsPerWeekDict = { 06.01.19 : 4, 06.08.19 : 5, 06.15.19 : 1 ... }
        for key,value in self.dictWeekNumbers.items():
            current_week = value
            next_week = current_week + datetime.timedelta(days = 7)
            for date in self.dates:
                if (date >= current_week) and (date < next_week):
                    count += 1
            self.postsPerWeekDict[current_week] = count
            count = 0
       
        return self.postsPerWeekDict, numOfPosts
    
    
    ## Finds postsPerWeek for a given species + platform
    ## structures a dictionary as such: {week_0: 2, week_1: 15, week_2: 37 ...} from a list of dates
    ## plots number of posts (y axis) vs week # (x axis)
    def postsPerWeekSpecies(self, collection): #, YYYY = 2019, MM = 6, DD = 1):
        #keys to access each platform's different date/time field
        keys = {'youtube': 'publishedAt', 'twitter': 'created_at', 'iNaturalist': 'time_observed_utc', 'flickr_june_2019': 'datetaken'}

        #gather results for youtube or twitter or flickr
        if self.dbName == 'youtube':
            res = self.db[collection].find({"$and":[{"wild": True},{"publishedAt":{"$gte": self.timeFrameStart}}]})
        elif self.dbName == 'flickr_june_2019':
            res = self.db[collection].find({"$and":[{"wild": True},{"datetaken":{"$gte": self.timeFrameStart}}]})
        elif self.dbName == 'twitter':
            res = self.db[collection].find({"$and":[{"wild": True},{"created_at":{"$gte": self.timeFrameStart}}]})
        else:
            #gather results for iNaturalist "$ne":0
            res = self.db[collection].find({"$and": [{'captive': False},{'time_observed_utc':{"$gte":self.timeFrameStart}}]})

        #create a list of all the times (in original UTC format) in respective fields for each platform    
        timePosts = [x[keys[self.dbName]] for x in res]
        if len(timePosts) < 1:
            print("No videos were processed yet.")
            return
        
        ## get list of dates of platform's posts and sort
        if self.dbName == 'youtube' or self.dbName == 'twitter' or self.dbName == 'flickr_june_2019':
            dates = [x.date() for x in timePosts] 
            dates.sort() 
        else:
            dates = []
            for x in timePosts:
                try:
                    dates.append(x.date())
                except TypeError:
                    print('TypeError', type(x), x)
            dates.sort()

        start = self.timeFrameStart.date()
        end = self.timeFrameEnd.date() ##datetime.date.today()
        weekNumber = 1
        count = 0
        dictWeekNumbers = {}
        postsPerWeekDict = {}
        numOfPosts = len(dates)

        #make a dictionary to order weekStartDates
        #format of self.dictWeekNumbers = { 1 : 06.01.19, 2: 06.08.19, 3:06.15.19 ... }
        date = start
        while date < end:
            dictWeekNumbers[weekNumber] = date 
            date += datetime.timedelta(days = 7)
            weekNumber += 1
    
        #make a dictionary self.postsPerWeek
        #keys are datetime objects of the date to start a new week
        #values are number of posts that were posted anytime from that date to date + 6 days
        #format self.postsPerWeekDict = { 06.01.19 : 4, 06.08.19 : 5, 06.15.19 : 1 ... }
        for key,value in dictWeekNumbers.items():
            current_week = value
            next_week = current_week + datetime.timedelta(days = 7)
            for date in dates:
                if (date >= current_week) and (date < next_week):
                    count += 1
            postsPerWeekDict[current_week] = count
            count = 0
        
        return postsPerWeekDict, numOfPosts
        
        
    #use numpy to compute and plot the smoothed out posts per week stats in order to visualize any trends
    #plot average number of posts (y-axis) vs week # (x axis)
    #returns a list of simple moving average data points
    def movingAveragePosts(self,window):
        #create a list of just the counts of posts for each week 
        postsPerWeekList = [item for item in self.postsPerWeekDict.values()] #FIXME: CHECK ORDER DUE TO DICTIONARY 
        #print('calculating simple moving average...\n')
        #calculating moving average with data points in postsPerWeekList
        weights = np.repeat(1.0, window)/window
        self.smas = np.convolve(postsPerWeekList, weights, 'valid') #calculate simple moving averages (smas)
        return self.smas  
    
    
    # Finds postsPerWeek for a given species + platform
    def movingAveragePostsSpecies(self,collection, window):
        postsPerWeekDict, numOfPosts = self.postsPerWeekSpecies(collection)
        #create a list of just the counts of posts for each week 
        postsPerWeekList = [item for item in postsPerWeekDict.values()] #FIXME: CHECK ORDER DUE TO DICTIONARY 
        #print('calculating simple moving average...\n')
        #calculating moving average with data points in postsPerWeekList
        weights = np.repeat(1.0, window)/window
        smas = np.convolve(postsPerWeekList, weights, 'valid') #calculate simple moving averages (smas)
        return smas
    
            
    #add channelId and user_country fields to docs in general and wild YT collections for all docs in timeframe
    def updateDocsChannelCountry(self, general_collection, wild_collection, video_channel_country_dics):
        for dic in video_channel_country_dics:
            self.db[general_collection].update_one({'_id': dic['videoId']}, {'$set': {'channelId': dic['channelId'],\
                                                                            'user_country': dic['user_country']}})
            self.db[wild_collection].update_one({'_id': dic['videoId']}, {'$set': {'channelId': dic['channelId'],\
                                                                            'user_country': dic['user_country']}})
        
    #For YouTube Playground
    #get videoID's for each document that belongs to a wild encounter within timeframe
    #dates consists of each date that our documents within the timeframe were published at
    #return a list of videoID's
    def getVideoIDs(self, collection):
        docs = self.db[collection].find({'$and': [{"wild": True}, {"publishedAt": {"$gte": self.timeFrameStart}}]})         
        self.listOfVideoIDs = [doc['videoID'] for doc in docs]
        return self.listOfVideoIDs
    
    #for Flickr Playground
    #build a list of dictionaries of all owner id's for wild encounter posts within the time frame
    #format: [{'id':photo_id, 'user_id': owner_id}, {...}]
    #we will then use the list of dicts to get user locations
    def getDictOfOwnerIds(self, collection):
        docs = self.db[collection].find({"wild": True})
        listOfDicts = []
        for doc in docs:
            ownerIdDict = {'id': doc['id'],
                           'user_id': doc['owner'] }
            listOfDicts.append(ownerIdDict)
        return listOfDicts

        
    def getFlickrTags(self, collection, getIrrelevantData):
        # Make a query to the specific DB and Collection
        if(getIrrelevantData):
            cursor = self.db[collection].find({"relevant": False})
        else:
            cursor = self.db[collection].find()#query)

        # Expand the cursor and construct the DataFrame
        df =  pd.DataFrame(list(cursor))

        return df
    
    #add newLocation field to relevant, wild docs in YT database
    #to avoid errors when building dataframe
    def addLocationField(self, collection):
        self.db[collection].update_many({"$and":[{"wild": True}, {"relevant": True}, \
                                                 {"newLocation": {"$exists": False}}]}, \
                                        {"$set": {"newLocation": 0}}) 
        
        
    #method to form collections consisting of only wild docs for wildbook api call
    def relevantDocuments(self, existingCollection, nameOfDb):
        keys = {'youtube': {'wild':True}, 
                'twitter': {'wild':True}, 
                'iNaturalist': {'captive':False}, 
                'flickr_june_2019': {'wild':True}}
        newDocs = self.db[existingCollection].find(keys[nameOfDb])
        newCollection = existingCollection + " wild"
        
        #insert "wild" encounter items from existingCollection into newCollection
        #if not already in newCollection
        for item in newDocs:
            if self.db[newCollection].find_one(item) == None:
                self.db[newCollection].insert_one(item)
            else:
                pass
        
        
    def getWildCountsAllSpecies(self, nameOfDb):
        species_cols = {'youtube': ["humpback whales", "new whale sharks test", "iberian lynx", "Reticulated Giraffe", \
                                    "grevys zebra", "plains zebras"],
                        'flickr': ['humpback whale specific', 'whale shark specific','iberian lynx general multilingual', \
                                  'reticulated giraffe specific', 'grevy zebra general',\
                                  'plains zebra specific'],
                        'iNaturalist': ["humpback whales", "whale sharks", "iberian lynx", "reticulated giraffe",\
                                     "grevy's zebra", "plains zebra"]
                        }
        species_wild_counts = []
        species_rel_counts =[]
        
        
        for collection in species_cols[nameOfDb]:
            if nameOfDb == 'iNaturalist':
                wild_count = self.db[collection].count({"captive": False})
                rel_count = wild_count
                
            else:
                wild_count = self.db[collection].count({"wild": True})
                rel_count = self.db[collection].count({"relevant": True})
                
            species_wild_counts.append(wild_count)
            species_rel_counts.append(rel_count)
            
            
        df_counts = pd.DataFrame({'Species': species_cols[nameOfDb],
                                   'Num_Wild_Docs': species_wild_counts,
                                   'Num_Relevant_Docs': species_rel_counts})
        
        return df_counts
            
    
    def getNumFiltered(self, collection):
        filtered_count = self.db[collection].count({"relevant":{"$ne":None}})
        col_count = self.db[collection].count()
        
        #print('The number of documents searched through for collection: {} is {}'.format(collection, filtered_count))
        return filtered_count, col_count
    
    ## create a df consisting of collection_name fofr query terms, count of wild docs,
    ## and count of relevant docs. Df is used in creating nested pie chart for comparison of 
    ## query terms on a per species basis
    ## Parameters: 
    ## speciesColNames = a list of collection names created for each query term 
    def makeQueryTermDataframe(self, speciesColNames):
        df = pd.DataFrame(columns = ["Col_Name", "Wild_Count", "Captive_Count", "Relevant_Count", "Num_Filtered", "Num_Total"])
        row_idx = 0
        
        for col_name in speciesColNames:
            wild_count = self.db[col_name].count({"wild": True})
            captive_count = self.db[col_name].count({"$and":[{"wild": False}, {"relevant": True}]})
            rel_count = self.db[col_name].count({"relevant": True})
            num_filtered, num_total = self.getNumFiltered(col_name)
            
            print(wild_count, rel_count)
            new_item = {"Col_Name": col_name,
                        "Wild_Count": wild_count,
                        "Captive_Count": captive_count,
                        "Relevant_Count": rel_count, 
                        "Num_Filtered": num_filtered,
                        "Num_Total": num_total
                       }
            df.loc[row_idx] = new_item
            row_idx += 1
        
#         #add column sums to our dataframe on the last row
#         df.loc[row_idx] = {'Col_Name': 'Totals',
#                            'Wild_Count': df['Wild_Count'].sum(),
#                            'Relevant_Count': df['Relevant_Count'].sum()}
        
        return df    
            
        
    def makeVideoChannelCountryDicts(self, collection, df_user_locations):
        #function to avoid using API and work with the data we already have stored
        #to create dictionaries in the form of [{videoId: , channelId: , user_country: }, {...}]
        video_channel_country = []
        for i in df_user_locations.index:
            
            #search docs by channelID
            channelID = df_user_locations['channelID'][i]
            
            #find the document and check if newLocation (encounter location) is != 0 and != null
            res = self.db[collection].find({'channelId': channelID})
            
            try:
                if res != None and res[0]['newLocation'] != None and res[0]['newLocation'] != 0:
                    #print(res[0]['user_country'])

                    #if we have an encounter location AND user location, make a dictionary and add to the list
                    temp = {'videoId': res[0]['videoID'],
                            'channelId': res[0]['channelId'], 
                            'user_country': res[0]['user_country']}

                    video_channel_country.append(temp)
                    
            except KeyError: 
                pass
                
        return video_channel_country
            
    
    
    def clearCollection(self, collection, msg=''):
        if (msg == 'yes'):
            self.db[collection].delete_many({})
            print("Collection was cleared.")
        else:
            print("Pass 'yes' into clearCollection() method to really clear it.")
            
    def close(self):
        self.client.close()