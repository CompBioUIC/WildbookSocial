from pymongo import MongoClient
import pprint
from IPython.display import YouTubeVideo, Image, display, Video
from wildbook_social import EmbedTweet
from datetime import timedelta
import time
import dateutil.parser
import matplotlib.pyplot as plt
import csv
import pandas as pd
import geopandas as gpd
import descartes
pd.options.mode.chained_assignment = None  # default='warn'
from shapely.geometry import Point
import datetime
from datetime import date
import numpy as np
import itertools
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Bing
from geopy.geocoders import Nominatim
from geopy import distance
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns

class Database:
    def __init__(self, key, database):
        self.client = MongoClient(key)
        self.dbName = database
        self.db = self.client[database]
        self.dateStr = '2019-06-01T00:00:00.00Z' #06.11.20
        self.timeFrameStart = dateutil.parser.parse(self.dateStr)
        
    def addItem(self, payload, collection):
        if self.dbName == 'iNaturalist':
            if self.db[collection].find_one(payload) == None:
                self.db[collection].insert_one(payload);
        else:
            try:
                self.db[collection].insert_one(payload)
            except:
                pass # Item already exists in database
            
    def returnDbCol(self, saveTo):
        return self.db[saveTo]
    
    def getDB(self):
        return self.db
    
    def getAllItems(self, collection):
        res = self.db[collection].find()
        return [x for x in res]
    
    def _updateItem(self, collection, id, payload):
        try:
            self.db[collection].update_one({"_id": id}, {"$set": payload})
            return True
        except(e):
            print("Error updating item", e)
            return False
    
    ## method to rename 'url_l' field in flickr docs to just 'url'
    def renameField(self, collection, oldName, newName):
        self.db[collection].update({}, {'$rename' : {oldName : newName}}, upsert=False, multi=True)
        return
    
    def convertToUTC(self, collection):
        res = self.db[collection].find({"$or":[{"relevant":None}, {"relevant": True}, {"captive": False}]})
        count = 0
        anticount = 0
        
        for doc in res:
            if self.dbName == 'youtube':
                date_str = doc['publishedAt']
                field = 'publishedAt'
            if self.dbName == 'iNaturalist':
                date_str = doc['time_observed_utc']
                field = 'time_observed_utc'
                date_str_2 = doc['created_on']
                field_2 = 'created_on'
            if self.dbName == 'flickr_june_2019':
                date_str = doc['datetaken']
                field = 'datetaken'
            if self.dbName == 'twitter':
                date_str = doc['created_at']
                field = 'created_at'
            if type(date_str) == str:
                doc_id = doc['_id']
                datetime_obj = dateutil.parser.parse(date_str)
                self.db[collection].update_one({'_id': doc_id}, {'$set':{ field: datetime_obj}})
                if self.dbName == "iNaturalist":
                    datetime_obj_2 = dateutil.parser.parse(date_str_2)
                    self.db[collection].update_one({'_id': doc_id}, {'$set':{ field_2: datetime_obj_2}})
                count = count + 1
            else:
                anticount = anticount + 1
                #continue
    def get_observed_created_times(self, wild_col, observed_tf_start,COVID=False):##, observed_tf_end=False, created_tf_start=False, created_tf_end=False):
        if COVID:
            ## sources: https://www.who.int/emergencies/diseases/novel-coronavirus-2019/interactive-timeline#!
            observed_tf_end= datetime.datetime.now()
            created_on_tf_start=  dateutil.parser.parse("2020-03-11") #date when WHO declares COVID pandemic
            res= self.db[wild_col].find({'$and':[{'time_observed_utc': {'$lte': observed_tf_end}}, {'created_on':{'$gte': created_on_tf_start}}]})
        else:
            observed_tf_start = dateutil.parser.parse(observed_tf_start)
            res = self.db[wild_col].find({'time_observed_utc': {'$gte': observed_tf_start}})
        obs_times =[]
        created_times =[]
        for doc in res:
            obs_times.append(doc['time_observed_utc'])
            created_times.append(doc['created_on'])
        return obs_times, created_times
    
    def plot_observed_created_delays(self, wild_col, observed_tf_start="2019-06-01 00:00:00", COVID=False):
        
        #create df with observed times, and times post was created/uploaded at
        observed_on_times, created_on_times= self.get_observed_created_times(wild_col,observed_tf_start,COVID)
        df =pd.DataFrame({"observed_on": observed_on_times,"created_on": created_on_times})
        #find time delays- keep difference in days only
        time_delay = df["created_on"] - df["observed_on"]
        time_delay_days=[]
        for x in range(0, len(time_delay)):
            time_delay_days.append(time_delay[x].days)
        df["time_delay_days"] = time_delay_days
        
        #plot date observed vs date uploaded in scatterplot
        fig, ax = plt.subplots(figsize=(14,14))
        sns.scatterplot(data=df, x="observed_on", y="created_on", hue="time_delay_days", palette='nipy_spectral', ax=ax)
        
        #plot a complementary histogram to visualize COUNTS
        delays = df['time_delay_days']
        plt.figure(figsize=(14,14))
        sns.histplot(data=df, x='time_delay_days')
#         plt.hist(delays, histtype = 'bar', rwidth = 0.8) #bins= [0,60,120,180,240,300,360,420]
#         plt.xlabel('Days between observed_on date and created_on date')
#         plt.ylabel('Number of posts')
#         plt.title('Histogram for Time Delay Between Encounter and Upload to iNaturalist')
#         plt.show()
        return df  

    def removeDuplicatesiNat(self,collection):
        res = self.db[collection].find()
        for item in res:
            print(item['id'])
            if not item:
                print('No more items') ##no more items to filter in collection
                break
            else:
                dup = self.db[collection].find({"$and": [{"_id": {"$ne":item["_id"]}}, {"id": item["id"]}]})

                #                 ## some sanity checks
                #                 print("ITEM")
                #                 print(item)

                numDuplicates = len(list(dup))
                print("numDuplicate: ", numDuplicates)
                if numDuplicates > 0:
                    print("numDups is > 0.. deleting duplicate docs...")
                    while(numDuplicates > 0):
                        pipeline = {"$and": [{"_id": {"$ne":item["_id"]}}, {"id": item["id"]}]}
                        self.db[collection].remove(pipeline)
                        numDuplicates -= 1
                    print("done removing duplicates. Following output should be empty")
                    dup = self.db[collection].find({"$and": [{"_id": {"$ne":item["_id"]}}, {"id": item["id"]}]})
                    print(dup)
                    print(len(list(dup)))
        print("Finished removing duplicates from collection")
    
    def doStatistics(self, collection, amount):
        i = 1
        count = 0
        while(amount > 0):
            print("Amount: ", amount)
            #only retrieve videos to filter that meet the time frame of June 1st, 2019 and forward
            if self.dbName == 'youtube':
                item = self.db[collection].find_one({"$and":[{"relevant": None},\
                                                             {"publishedAt":{"$gte": self.timeFrameStart}}]})
            elif self.dbName == 'twitter':
                #dont need to check times bc only get posts in last 7 days
                item = self.db[collection].find_one({"relevant": None}) 
                if not item:
                    break ##no more items to filter in collection
                dup = self.db[collection].find({"$and": [{"_id": {"$ne":item["_id"]}}, {"img_url": item["img_url"]}]})
                
#                 ## some sanity checks
#                 print("ITEM")
#                 print(item)
                
                numDuplicates = len(list(dup))
                print("numDuplicate: ", numDuplicates)
                if numDuplicates > 0:
                    print("numDups is > 0.. deleting duplicate docs...")
                    while(numDuplicates > 0):
                        pipeline = {"$and": [{"_id": {"$ne":item["_id"]}}, {"img_url": item["img_url"]}]}
                        self.db[collection].remove(pipeline)
                        numDuplicates -= 1
                
                    print("done removing duplicates. Following output should be empty")
                    dup = self.db[collection].find({"$and": [{"_id": {"$ne":item["_id"]}}, {"img_url": item["img_url"]}]})
                    print(dup)
                    print(len(list(dup)))
                    
            elif self.dbName == 'flickr_june_2019':
                #get an item that hasn't been manually filtered
                item = self.db[collection].find_one({'relevant': None})
                #if the item is empty - we ran out of docs
                if item == None:
                    print("No more items to filter through - exiting..")
                    break
                #avoid searching through duplicates
                duplicate_res = self.db[collection].find_one({'$and': [{'id':item['id']}, {'relevant':{"$ne": None}}]})
                if duplicate_res != None:
                    print("This item is a duplicate")
                    self.db[collection].remove({'$and': [{'id': item['id']}, {'relevant': None}]})
                    count += 1
                    amount -= 1
                    i += 1
                    continue

            #manually filter through docs
            if not item:
                break
            if self.dbName=='youtube':
                print("{}: {}".format(i, item['title']['original']))
                display(YouTubeVideo(item['_id']))
            elif self.dbName == 'twitter':
                url="https://twitter.com/{}/status/{}".format(item['user_handle'], item['_id'])
                display(EmbedTweet(url))
            elif self.dbName == 'flickr_june_2019':
                if item['url_l'] != "":
                    display(Image(item['url_l'], height=200, width=200))
                else: 
                    #to handle images without available url's
                    rel = False

            print("Relevant (y/n):", end =" ")
            rel = True if input() == "y" else False 
            #categorize post as wild or captive
            loc = 0
            if rel == True:
                print("Wild (y/n):", end =" ")
                wild = True if input() == 'y' else False #mark as wild (y) or captive (n)
                #prompt user with option to enter location only if encounter is wild (YT videos only)
                if (self.dbName == 'youtube' and wild == True) or (self.dbName == 'twitter' and wild == True):
                    print("Is there a location? (y/n):", end = " ")
                    if input() == "y": loc = input()
            if rel == False: wild = 0  #handle irrelevant posts

            #update with new values
            if self.dbName == 'youtube':
                self._updateItem(collection, item['_id'], {"relevant": rel, "wild": wild, "newLocation": loc })
                print("Response saved! Location : {}.\n".format(loc))
            elif self.dbName == 'twitter':
                self._updateItem(collection, item['_id'], {"relevant": rel, "wild": wild, "encounter_loc": loc })
                print("Twitter Response saved! Location : {}.\n".format(loc))
            else:
                self._updateItem(collection, item['_id'], {"relevant": rel, "wild": wild})
                
            print("Response saved! {} and {}.\n".format("Relevant" if rel else "Not relevant", \
                                                        "Wild" if wild else "Not wild"))
            #update amount of items in collection that need to be filtered
            amount -= 1
            i += 1
        print('No more items to proceed.')
        
    def showStatistics(self, collection):
        total = self.db[collection].count_documents({ "$and": [{"relevant":{"$in":[True,False]}}]})
        if total == 0:
            print("No videos were processed yet.")
            return
        #relevant count
        relevant_count = self.db[collection].count_documents({ "$and": [{"relevant":True}]})
        print("relevant: {} \n".format(relevant_count))
        # percent relevant caluclated out of total
        relevant = self.db[collection].count_documents({ "$and": [{"relevant":True}]}) / total * 100 
        # percent wild calculated out of ONLY relevant items, this way the remaining percent can be
        # assumed to be % of zoo sightings
        try:
            wild = self.db[collection].count_documents({ "$and": [{"relevant":{"$in":[True]}}, {"wild":True}] }) / relevant_count * 100
            # percent wild calculated out of total
            wild_tot = self.db[collection].count_documents({ "$and": [{"relevant":{"$in":[True]}}, {"wild":True}] }) / total * 100
            print("Out of {} items, {}% are relevant.From those that are relevant, {}% are wild. Out of the total, {}% are wild".format(total, round(relevant,1), round(wild,1), round(wild_tot, 1)))
            self.showHistogram(collection)
        except ZeroDivisionError:
            print("No wild documents in collection so far")
        
    def showHistogram(self, collection):
        #UPDATE: fixed so it only displays delay in time between successive posts in time frame (June 01, 2020)
        keys = {'youtube': 'publishedAt', 'twitter': 'created_at', 'iNaturalist': 'time_observed_utc', 
                'flickr_june_2019': 'datetaken'}
        
        #gather results for youtube or twitter
        if self.dbName == 'youtube' or self.dbName == 'twitter' or self.dbName == 'flickr_june_2019':
            res = self.db[collection].find({"$and":[{"wild": True},{keys[self.dbName]:{"$gte": self.timeFrameStart}}]})
        else:
            #gather results for iNaturalist
            res = self.db[collection].find({"$and": [{'captive': False},{'time_observed_utc': \
                                                                         {"$gte":self.timeFrameStart}}]})
        #create a list of all the times (in original UTC format) in respective fields for each platform    
        self.timePosts = [x[keys[self.dbName]] for x in res]
        if len(self.timePosts) < 1:
            print("No videos were processed yet.")
            return
        #IMPORTANT: self.dates() is a list of datetime.date() objects of wild encounters within the time frame
        #it converts .datetime objs to more general .date objs (easier to work with)
        #and then sorts the converted dates in a list with most recent at beginning and least recent towards end
        self.dates = [x.date() for x in self.timePosts] 
        self.dates.sort() 
        
        # Find the difference in days between posting dates of successive posts
        lastDate = [self.dates[0]]  #stores all the dates we have already looked at
        timeDiffs = []
        for date in self.dates:
            res = abs(date - lastDate[-1])#find the time difference between successive posts sorted
            timeDiffs.append(res.days)
            lastDate.append(date)

        # Plotting the histogram
#         plt.figure(figsize=(15,5))
#         plt.hist(timeDiffs, bins = 10, histtype = 'bar', rwidth = 0.8)
#         plt.xlabel('Days between succesive posts')
#         plt.ylabel('Number of posts')
#         plt.title('Histogram for Time Between Succesive Wild Posts')
#         plt.show()
        
        #new data visuals with seaborn
        plt.figure(figsize=(20,20))
        sns.histplot(data=timeDiffs, bins=10)
        plt.xlabel('Days between succesive posts')
        plt.ylabel('Number of posts')
        plt.title('Histogram for Time Between Succesive Wild Posts')
        
        
      
    #structures a dictionary as such: {week_0: 2, week_1: 15, week_2: 37 ...} from a list of dates
    #plots number of posts (y axis) vs week # (x axis)
    def postsPerWeek(self): 
        start = self.timeFrameStart.date()
        end = datetime.date.today()
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
    
    # Finds postsPerWeek for a given species + platform
    #structures a dictionary as such: {week_0: 2, week_1: 15, week_2: 37 ...} from a list of dates
    #plots number of posts (y axis) vs week # (x axis)
    def postsPerWeekSpecies(self, collection): #, YYYY = 2019, MM = 6, DD = 1):
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
        #IMPORTANT: dates() is a list of datetime.date() objects of wild encounters within the time frame
        #it converts .datetime objs to more general .date objs (easier to work with)
        #and then sorts the converted dates in a list with most recent at beginning and least recent towards end
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
#             dates = [datetime.datetime.strptime(x, "%Y-%m-%dT%H:%M:%S.%fZ").date() for x in timePosts]
            dates.sort()

        start = self.timeFrameStart.date()
        end = datetime.date.today()
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
        #print("\n week number dictionary: \n", self.dictWeekNumbers)   
    
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
    
    #customized to youtube only so far
    def heatmap(self,collection, csvName):
        csvName = csvName +'.csv'
        #docs_w_loc = self.db[collection].find({'$and': [{'wild': True}, {'newLocation':{'$ne':0}}]})
        docs_w_loc = self.db[collection].find({'newLocation':{'$ne':0}})
        loc_list = []
        for doc in docs_w_loc:
            try:
                dic = {
                    'videoID' : doc['videoID'],
                    'newLocation':doc['newLocation']
                }
                loc_list.append(dic)
                #print(doc)
            except KeyError:
                if KeyError == 'newLocation':
                    pass     
        
        fields = ['videoID', 'newLocation'] 
        with open(csvName, 'w') as locations_csv:
            csvName = csv.DictWriter(locations_csv, fieldnames = fields)
            csvName.writeheader()
            for item in loc_list:
                csvName.writerow(item)
        print('Done. Check in your jupyter files for a .csv file with the name you entered')
        
    #makes a csv with both encounter and user locs from docs in YT wild col within the timeframe  
    def reverse_geocode_yt(self, wild_collection, video_channel_country_dics, csv_name):
        #read in csv file with country codes 
        country_codes = {}
        file = open('/Users/mramir71/Documents/Github/wildbook-social-1/wildbook_social/Database/country_codes.csv', 'r')
        reader = csv.reader(file)
        for row in reader:
            country_codes[row[0]] = row[1]
        country_codes[0] = 0
        
        # convert country codes to full names
        for dic in video_channel_country_dics:
            doc_res = self.db[wild_collection].find({'_id': dic['videoId']})
            try:
                dic['user_country'] = country_codes[dic['user_country']]
            except KeyError:
                pass
            for doc in doc_res:
                dic['encounter_loc'] = doc['newLocation']
                
        #create a dataframe with video_channel_country_dics
        df = pd.DataFrame(video_channel_country_dics)
        
        #use bing geocoder to convert cities/countries -> lat, long coords
#         key = 'AsmRvBYNWJVq55NBqUwpWj5Zo6vRv9N_g6r96K2hu8FLk5ob1uaXJddVZPpMasio'
#         locator = Bing(key)
        user_locs = []
        enc_locs = []
        
        #df where there are videos in tf that have BOTH encounter and user loc
        df_both_locs = df.loc[(df.encounter_loc != 0 ) & (df.user_country != 0) & (df.encounter_loc != "none") & \
                               (df.encounter_loc != None) & (df.encounter_loc != "n/a")]
        df_both_locs = df_both_locs.reset_index(drop=True)
                
        ## handle AttributeError
        geolocator = Nominatim(user_agent='wb_geocoder')#"geoapiExercises")
        enc_lat=[]
        enc_long=[]
        user_lat=[]
        user_long=[]
        
        print(len(df_both_locs))
        enc_idx =-1 
        for x in df_both_locs.encounter_loc.values:
            enc_idx+=1
            try:
                lat=geolocator.geocode(x).latitude
                long=geolocator.geocode(x).longitude
                enc_lat.append(lat)
                enc_long.append(long)
            except AttributeError:
                ## loc could not be geocoded, drop this row in df_coords to make lists equal length
                print('Error in enc locs: ', x, enc_idx)
                df_both_locs= df_both_locs.drop(index=enc_idx)
                
        user_idx=-1
        for x in df_both_locs.user_country.values:
            user_idx+=1
            try:
                lat= geolocator.geocode(x).latitude
                long= geolocator.geocode(x).longitude
                user_lat.append(lat)
                user_long.append(long)
            except AttributeError:
                ## loc could not be geocoded, drop this row in df_coords
                print('Error in user locs: ', x)
                df_both_locs= df_both_locs.drop(index=enc_idx)

        print(len(enc_lat))
        print(len(enc_long))
        print(len(user_lat))
        print(len(user_long))
                                          
        #add enc_coords list and user_coords list to df_both_locs
        df_both_locs['enc_lat'] = enc_lat
        df_both_locs['enc_long'] = enc_long
        df_both_locs['user_lat'] = user_lat
        df_both_locs['user_long'] = user_long
        
        return df_both_locs 
    
    ## create a dataframe of latitudes and longitudes of encounter locs
    ## for each document in iNat wild_collection
    def plot_enc_locs_iNat(self, wild_collection):
        doc_res= self.db[wild_collection].find()
        enc_lats=[]
        enc_longs=[]
        ## gather encounter lats and longs for each doc in wild col
        for doc in doc_res:
            enc_lats.append(doc['latitude'])
            enc_longs.append(doc['longitude'])
        
        ## build df
        df_coords= pd.DataFrame({"enc_lat": enc_lats, 
                                 "enc_long": enc_longs})
        
        return df_coords
    
    
    # reverse geocode each user location for each corresponding item
    # then return df with latitude and longitude of encounter locations 
    # and latitude and longitude of user locations
    def reverse_geocode_flickr(self, user_info, wild_collection):
        # add the encounter locations to our user info dictionaries
        # which already contain user location
        for dic in user_info:
            doc_res = self.db[wild_collection].find({'id': dic['id']})
            for doc in doc_res:
                dic['enc_lat'] = doc['latitude']
                dic['enc_long'] = doc['longitude']
        
        #create a df from our user_info list of dictionaries
        df = pd.DataFrame(user_info)
    
        #use bing geocoder to convert cities/countries -> lat, long coords
        key = 'AsmRvBYNWJVq55NBqUwpWj5Zo6vRv9N_g6r96K2hu8FLk5ob1uaXJddVZPpMasio'
        locator = Bing(key)
        user_locs = []
        enc_locs = []
        
        #df where there are videos in tf that have BOTH encounter and user loc
        df_both_locs = df.loc[(df.enc_long != 0) & (df.user_location != None) & (df.user_location != '')]
        df_both_locs = df_both_locs.reset_index(drop=True)
        
        #get user country lat long coords
        user_lat = []
        user_long = []
        for x in df_both_locs.user_location.values:
            if(x == ''):
                print('empty')
                continue
            try:
                user_lat.append(locator.geocode(x, timeout = 3).latitude)
                user_long.append(locator.geocode(x, timeout = 3).longitude)
            except AttributeError:
                user_lat.append(None)
                user_long.append(None)
                
        #drop rows in df where user_lat = None, user_long = None
#         rows = df_both_locs.loc[df_both_locs.user_lat == None or df_both_loc.user_location == '']
#         print(rows)
#         df_both_locs = df_both_locs.loc[df_both_locs.user_lat == None or df_both_loc.user_location == '']
#         df_both_locs.drop(rows)
                                                  
        #add enc_coords list and user_coords list to df_both_locs
        df_both_locs['user_lat'] = user_lat
        df_both_locs['user_long'] = user_long
        
        return df_both_locs
    
    # plot user and encounter locations, with a line connecting corresponding entries
    def plotEncounterUserLocs(self, df_coords, saveTo, platform):
        #initialize a space for figure
        fig = go.Figure()
        
        #what to add as text parameter for markers
        keys = {'youtube': 'user_country', 'flickr_june_2019': 'user_location'}

        #add the user country markers
        fig.add_trace(go.Scattergeo(
            lon = df_coords['user_long'],
            lat = df_coords['user_lat'],
            hoverinfo = 'text',
            text = df_coords['user_country'], #df_coords[keys[platform]], #df_coords['user_country'],
            mode = 'markers',
            marker = dict(
                size = 4,
                color = 'rgb(0, 255, 0)',
                line = dict(
                    width = 3,
                    color = 'rgba(65, 65, 65, 0)'
                )
            )))

        #add the encounter location markers
        fig.add_trace(go.Scattergeo(
            lon = df_coords['enc_long'],
            lat = df_coords['enc_lat'],
            hoverinfo = 'text',
            text = df_coords['encounter_loc'], #df_coords[keys[platform]], #df_coords['encounter_loc'],
            mode = 'markers',
            marker = dict(
                size = 4,
                color = 'rgb(255, 0, 0)',
                line = dict(
                    width = 3,
                    color = 'rgba(68, 68, 68, 0)'
                )
            )))

        # #begin to add path traces from user country to encounter locations
        # flight_paths = []
        for i in range(len(df_coords)):
            fig.add_trace(
                go.Scattergeo(
                    lon = [df_coords['user_long'][i], df_coords['enc_long'][i]],
                    lat = [df_coords['user_lat'][i], df_coords['enc_lat'][i]],
                    mode = 'lines',
                    line = dict(width = 1,color = 'blue')#,
        #             opacity = float(df_coords['cnt'][i]) / float(df_flight_paths['cnt'].max()),
                )
            )

        #update parameters of map figure to display
        fig.update_layout(
            title_text = saveTo + " sightings since 06.01.2019",
            showlegend = False,
            geo = dict(
                scope = 'world',
                projection_type = 'equirectangular', #'azimuthal equal area',
                showland = True,
                landcolor = 'rgb(243, 243, 243)',
                countrycolor = 'rgb(204, 204, 204)',
            ),
        )
        print('showing')
        fig.show()
        
    #makes a csv with both encounter and user locs from docs in Flickr wild col within the timeframe 
    def allLocsCsvFlickr(self, wild_collection, owner_id_loc_dicts):
        csv_name_all_locs = wild_collection + " All Locs Flickr.csv"
        #add encounter location onto ownerIdLocDicts
        for dic in owner_id_loc_dicts:
            doc_res = self.db[wild_collection].find({'id': dic['id']})
            for doc in doc_res:
                dic['encounter_loc'] = "{lat}, {long}".format(lat = doc['latitude'], long = doc['longitude'])
        
        #build df
        df = pd.DataFrame              
        #create csv        
#         fields = ['id', 'user_id','encounter_loc', 'user_location']
#         with open(csv_name_all_locs, 'w') as all_locs_csv:
#             csv_name_all_locs = csv.DictWriter(all_locs_csv, fieldnames = fields)
#             csv_name_all_locs.writeheader()
#             for dic in owner_id_loc_dicts:
# #                 if dic['encounter_loc'] != "0, 0" and dic['user_location'] != " ":
#                   csv_name_all_locs.writerow(dic)
#         print('Done.Check in your jupyter files for a .csv file for user and encounter locations')
            
    #add channelId and user_country fields to docs in gen. and wild YT collections for all docs in timeframe
    def update_docs_channel_country(self, general_collection, wild_collection, video_channel_country_dics):
        for dic in video_channel_country_dics:
            self.db[general_collection].update_one({'_id': dic['videoId']}, {'$set': {'channelId': dic['channelId'],\
                                                                            'user_country': dic['user_country']}})
            self.db[wild_collection].update_one({'_id': dic['videoId']}, {'$set': {'channelId': dic['channelId'],\
                                                                            'user_country': dic['user_country']}})
        
    #For YouTube Playground
    #get videoID's for each document that belongs to a wild encounter within timeframe
    #self.listOfDates consists of each date that our documents within the timeframe were published at
    #return a list of videoID's
    def getVideoIDs(self, collection):
        docs = self.db[collection].find({"wild": True})     
        #dateutil.parser.parse(doc['publishedAt']).date()
        self.listOfVideoIDs = [doc['videoID'] for doc in docs if doc['publishedAt'].date() in self.dates] 
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

    #method to compute the number of wild encounter posts a user uploads
    #configured for the following plastforms so far:
    #1. YouTube, 2. , 3. ,4.
    # postsPerUser works by constructing a pandas Dataframe object for each user who posted a wild encounter
    # columns in the dataframe are: CHANNEL_ID(user), COUNTRY_ABBREVIATION, COUNTRY_FULL, NUM_POSTS
    # each row of the dataframe would then correspond to a different user
    #user_countries is a list of dictionaries such that [{ channelID: country_abbreviation}, {...}, {...}]
    def postsPerUser(self, wild_collection, channel_id_list): #, user_dict_list):
        #//////for YouTube///////
        #iterate through the list of channel id's and increase count -- store in user_count_dict 
        #user_count_dict is structured as {channelId : count, channelId: count, ...}
        self.list_of_users = [] # structured as [{channelID: count, country: ___ }, ...]
        user_count_dict = {} 
        for each_user_id in channel_id_list:
            if each_user_id not in user_count_dict.keys():
                user_count_dict[each_user_id] = 0
            user_count_dict[each_user_id] = user_count_dict[each_user_id] + 1
        
        #if CSV writing fails, uncomment this - paste what is printed into excel and go from there
        for user_id in user_count_dict:
            print(user_id, ':', user_count_dict[user_id])  
        return self.list_of_users
    
        
    #method to build a dataframe consisting of encounter times, upload times, 
    #encounter location, and user location for each post gathered
    #this is for visualizing/plotting difference b/w upload and encounter times
    def buildDataFrame(self, collection):
        #setup
        find_keys = {"youtube": "publishedAt", "iNaturalist": "time_observed_utc"}
        if self.dbName != "iNaturalist": 
            wild_col = collection + " wild"
        else: 
            wild_col = collection
        #retrieve relevant, wild documents within timeframe
        if self.dbName != "youtube" and self.dbName != "iNaturalist":
            res = self.db[wild_col].find()
        else:
            res = self.db[wild_col].find({find_keys[self.dbName]:{"$gte": self.timeFrameStart}})    
        res_list = [x for x in res]
        
        #keys to access fields needed to make rows and cols of dataframe
        #for each key's (self.dbName) list of values in df_keys:
        #INDEX 0: doc key for post id's across platforms
        #INDEX 1: doc key for encounter times
        #INDEX 2: doc key for time post was uploaded
        #INDEX 3: doc key for wild encounter locations
        #INDEX 4: will be doc key for user locations 
        df_keys = {'youtube': ['videoID', 'publishedAt', 'publishedAt', 'newLocation' ], 
                   'twitter': ['_id', 'created_at', 'created_at', 'location'], 
                   'iNaturalist': ['id', 'time_observed_utc', 'created_on', ['latitude', 'longitude']], 
                   'flickr_june_2019': ['id', 'datetaken', 'dateupload', ['latitude', 'longitude']]}
        
        #1.create list of id's for each post (rows)
        id_list = [x[df_keys[self.dbName][0]] for x in res_list] 
        print(len(id_list))
        
        #2.create a list of wild encounter times (col 1)
        #for youtube, we will use 'publishedAt' as a stand in
        #however it is worth investigating the fileDetails.creationTime obj for each video
        #twitter also does not have field to pinpoint exact encounter time so we use published time
        encounter_times = [x[df_keys[self.dbName][1]] for x in res_list]
        
        #3.create a list of upload times
        #NOTE: dataupload for flicker is a UNIX time objective so we must convert to UTC
        upload_times = [x[df_keys[self.dbName][2]] for x in res_list]
        if self.dbName == 'flickr_june_2019':
            upload_times_temp = [dateutil.parser.parse(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(x))))\
                                 for x in upload_times]
            upload_times = upload_times_temp

        #4.create a list of encounter locations (location of video or post encounter)
        if self.dbName == 'flickr_june_2019' or self.dbName == 'iNaturalist':
            geo_coords = [str(x['latitude']) + ", " + str(x['longitude']) \
                          if x['latitude'] != None or x['longitude'] != None else None for x in res_list]
            encounter_locations = geo_coords #eventually convert to an actual location via reverse geocoding
        else:
            encounter_locations = [x[df_keys[self.dbName][3]] for x in res_list] 
        
        #5.create a list of user locations
        #for YT, try to add the channelID for each video onto the doc in mongo itself
        #and change YT script to do this from now on
        user_locations = [None for x in res_list]
        
        #6. Assemble the dataframe
        data = {"ID" : id_list,
                "ENCOUNTER TIME" : encounter_times,
                "UPLOAD TIME": upload_times,
                "ENCOUNTER LOC" : encounter_locations,
                "USER LOC" : user_locations 
                }
        df = pd.DataFrame(data)
        
        #7.zip encounter times and upload times list to find difference and graph
        #delay_times = [(x[1] - x[0]).days for x in zipped_times]
        #df['DELAY'] = df['UPLOAD TIME']- df['ENCOUNTER TIME']
        zipped_times = [zip(encounter_times, upload_times)] 
        delay_times = []
        for x in zipped_times:
            for item in x:
                delay = item[1].date() - item[0].date()
                delay_times.append(delay.days)
        df['DELAY'] = delay_times
        df.plot.bar(x = 'ID', y = 'DELAY', figsize=(10,10))
        return df
    
    def getFlickrTags(self, collection, getIrrelevantData):
        # Make a query to the specific DB and Collection
        if(getIrrelevantData):
            cursor = self.db[collection].find({"relevant": False})
        else:
            cursor = self.db[collection].find()#query)

        # Expand the cursor and construct the DataFrame
        df =  pd.DataFrame(list(cursor))

        # # Delete the _id
        # if no_id:
        #     del df['_id']
        return df
    
    #add newLocation field to relevant, wild docs in YT database
    #to avoid errors when building dataframe
    def addLocationField(self, collection):
        self.db[collection].update_many({"$and":[{"wild": True}, {"relevant": True}, \
                                                 {"newLocation": {"$exists": False}}]}, \
                                        {"$set": {"newLocation": 0}}) 
        
        
    #method to form collections consisting of only wild docs for wildbook api call
    #only tailored towards YouTube currently
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
                
    def clearCollection(self, collection, msg=''):
        if (msg == 'yes'):
            self.db[collection].delete_many({})
            print("Collection was cleared.")
        else:
            print("Pass 'yes' into clearCollection() method to really clear it.")
            
    def close(self):
        self.client.close()
        
