from pymongo import MongoClient
from IPython.display import YouTubeVideo, Image, display
from datetime import timedelta
import dateutil.parser
import matplotlib.pyplot as plt
import csv
import pandas as pd
import datetime
from datetime import date
import numpy as np

class Database_Beta:
    def __init__(self, key, database):
        self.client = MongoClient(key)
        self.dbName = database
        self.db = self.client[database]
        
    def addItem(self, payload, collection):
        if self.dbName == 'iNaturalist':
            if self.db[collection].find_one(payload) == None:
                self.db[collection].insert_one(payload);
        else:
            try:
                self.db[collection].insert_one(payload)
            except:
                # Item already exists in database
                pass
        
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
            if self.dbName == 'flickr':
                date_str = doc['datetaken']
                field = 'datetaken'
            if type(date_str) == str:
                doc_id = doc['_id']
                datetime_obj = dateutil.parser.parse(date_str)
                self.db[collection].update_one({'_id': doc_id}, {'$set':{ field: datetime_obj}})
                count = count + 1
            else:
                anticount = anticount + 1
                #continue
                
    def doStatistics(self, collection, amount):
        i = 1
        while(amount > 0):
            #only retrieve videos to filter that meet the time frame of June 1st, 2019 and forward
            dateStr = '2019-06-01T00:00:00.00Z'
            self.timeFrameStart = dateutil.parser.parse(dateStr)
            if self.dbName == 'youtube':
                item = self.db[collection].find_one({"$and":[{"relevant": None},{"publishedAt":{"$gte": self.timeFrameStart}}]})
            elif self.dbName == 'twitter':
                item = self.db[collection].find_one({"$and":[{"relevant": None},{"createdat":{"$gte": self.timeFrameStart}}]})
            elif self.dbName == 'flickr_june_2019':
                item = self.db[collection].find_one({'relevant': None})
            
            if not item:
                break
            if self.dbName=='youtube':
                print("{}: {}".format(i, item['title']['original']))
                display(YouTubeVideo(item['_id']))
            elif self.dbName == 'twitter':
                display(Image(item['img_url'], height=100, width=200))
            elif self.dbName == 'flickr_june_2019':
                if item['url_l'] != "":
                    display(Image(item['url_l'], height=100, width=200))
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
                if self.dbName == 'youtube' and wild == True:
                    print("Is there a location? (y/n):", end = " ")
                    if input() == "y": loc = input()
            if rel == False: wild = 0  #handle irrelevant posts

            #update with new values
            if self.dbName == 'youtube':
                self._updateItem(collection, item['_id'], {"relevant": rel, "wild": wild, "newLocation": loc })
                print("Response saved! Location : {}.\n".format(loc))
            else:
                self._updateItem(collection, item['_id'], {"relevant": rel, "wild": wild})
                
            print("Response saved! {} and {}.\n".format("Relevant" if rel else "Not relevant", "Wild" if wild else "Not wild"))
            #update amount of items in collection that need to be filtered
            amount -= 1
            i += 1
        print('No more items to proceed.')
        
    def showStatistics(self, collection):
        print("TESTING BETA\n")
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
        wild = self.db[collection].count_documents({ "$and": [{"relevant":{"$in":[True]}}, {"wild":True}] }) / relevant_count * 100
        # percent wild calculated out of total
        wild_tot = self.db[collection].count_documents({ "$and": [{"relevant":{"$in":[True]}}, {"wild":True}] }) / total * 100
        print("Out of {} items, {}% are relevant.From those that are relevant, {}% are wild. Out of the total, {}% are wild".format(total, round(relevant,1), round(wild,1), round(wild_tot, 1)))
        self.showHistogram(collection)
        
    def showHistogram(self, collection):
        #UPDATE: fixed so it only displays delay in time between successive posts in time frame (June 01, 2020)
        keys = {'youtube': 'publishedAt', 'twitter': 'created_at', 'iNaturalist': 'time_observed_utc', 'flickr': 'datetaken'}
        #gather results for youtube or twitter
        if self.dbName == 'youtube' or self.dbName == 'twitter' or self.dbName == 'flickr':
            dateStr_2 = '2019-06-01T00:00:00.00Z'
            self.timeFrameStart_2 = dateutil.parser.parse(dateStr_2)
            res = self.db[collection].find({"$and":[{"wild": True},{"publishedAt":{"$gte": self.timeFrameStart_2}}]})
        else:
            #gather results for iNaturalist
            res = self.db[collection].find({"$and": [{'captive': False},{'time_observed_utc':{"$ne":None}}]})
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
        plt.figure(figsize=(15,5))
        plt.hist(timeDiffs, bins = 10, histtype = 'bar', rwidth = 0.8)
        plt.xlabel('Days between succesive posts')
        plt.ylabel('Number of posts')
        plt.title('Histogram for Time Between Succesive Wild Posts')
        plt.show()
        
      
    #structures a dictionary as such: {week_0: 2, week_1: 15, week_2: 37 ...} from a list of dates
    #plots number of posts (y axis) vs week # (x axis)
    def postsPerWeek(self): #, YYYY = 2019, MM = 6, DD = 1):
        start = self.timeFrameStart_2.date()
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
        #print("\n week number dictionary: \n", self.dictWeekNumbers)   
    
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
    
    #customized to youtube only so far
    def heatmap(self,collection, csvName):
        self.csvName = csvName +'.csv'
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
        with open(self.csvName, 'w') as locations_csv:
            csvName = csv.DictWriter(locations_csv, fieldnames = fields)
            csvName.writeheader()
            for item in loc_list:
                csvName.writerow(item)
        print('done! Check in your jupyter files for a .csv file with the name you entered')
        
    #get videoID's for each document that belongs to a wild encounter within timeframe
    #self.listOfDates consists of each date that our documents within the timeframe were published at
    #return a list of videoID's
    def getVideoIDs(self, collection):
        docs = self.db[collection].find({"wild": True})     
        #dateutil.parser.parse(doc['publishedAt']).date()
        self.listOfVideoIDs = [doc['videoID'] for doc in docs if doc['publishedAt'].date() in self.listOfDates] 
        return self.listOfVideoIDs
    
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
#             #go through the user_dict_list and find the country the channel belongs to. Add it to user_count_dict
#             #fixme: do this efficiently!! FIXME: come back and work on this 
#             for user_dict in user_dict_list:
#                 user_count_dict['country'] = user_dict[each_user_id] 
            #self.list_of_users.append(user_count_dict) #if CSV writing fails delete this
        
        #if CSV writing fails, uncomment this - paste what is printed into excel and go from there
        for user_id in user_count_dict:
            print(user_id, ':', user_count_dict[user_id])
        
        return self.list_of_users
    
    def csvWriter(self,list_of_dictionaries, csvName):
       #fields = ['channelId' ] 
        with open(csvName, 'w') as new_csv:
            csvName = csv.DictWriter(new_csv, fieldnames = fields)
            csvName.writeheader()
            for item in list_of_dictionaries:
                csvName.writerow(item)
        print('done! Check in your jupyter files for a .csv file with the name you entered')
      
    
    #method to form collections consisting of only wild docs for wildbook api call
    #only tailored towards YouTube currently
    def relevantDocuments(self, existingCollection):
        newDocs = self.db[existingCollection].find({"wild": True})
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
        
