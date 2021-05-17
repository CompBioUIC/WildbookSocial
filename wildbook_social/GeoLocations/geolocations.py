import pandas as pd
import geopandas as gpd
import descartes
pd.options.mode.chained_assignment = None  # default='warn'
from shapely.geometry import Point
import numpy as np
import itertools
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Bing
import plotly.express as px
import plotly.graph_objects as go

## this file contains all functions previously in database class
## that deal with location metadata, unless it requires updating/modifying documents
## in a collection with location metadata, then those functions are to remain in database.py
class GeoLocations:
    def __init__(self, key, database):
        self.client = MongoClient(key)
        self.dbName = database
        self.db = self.client[database]
        self.dateStr = '2019-06-01T00:00:00.00Z' #06.11.20
        self.timeFrameStart = dateutil.parser.parse(self.dateStr)
    
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
        key = 'AsmRvBYNWJVq55NBqUwpWj5Zo6vRv9N_g6r96K2hu8FLk5ob1uaXJddVZPpMasio'
        locator = Bing(key)
        user_locs = []
        enc_locs = []
        
        #df where there are videos in tf that have BOTH encounter and user loc
        df_both_locs = df.loc[(df.encounter_loc != 0 ) & (df.user_country != 0) & (df.encounter_loc != "none") & \
                               (df.encounter_loc != None) & (df.encounter_loc != "n/a")]
        df_both_locs = df_both_locs.reset_index(drop=True)
        
        
        
        #get encounter lat long coords
        print(len(df_both_locs.encounter_loc.values))
        print(df_both_locs.encounter_loc.values)
        enc_lat = [locator.geocode(x, timeout = 3).latitude for x in df_both_locs.encounter_loc.values]
        enc_long = [locator.geocode(x,timeout = 3).longitude for x in df_both_locs.encounter_loc.values]
            #get user country lat long coords
        user_lat = [locator.geocode(x, timeout = 3).latitude for x in df_both_locs.user_country.values]
        user_long = [locator.geocode(x,timeout = 3).longitude for x in df_both_locs.user_country.values]
        
                                          
        #add enc_coords list and user_coords list to df_both_locs
        df_both_locs['enc_lat'] = enc_lat
        df_both_locs['enc_long'] = enc_long
        df_both_locs['user_lat'] = user_lat
        df_both_locs['user_long'] = user_long
        
        return df_both_locs 
    
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
#         print(df_both_locs.user_location)
        user_lat = []
        user_long = []
        for x in df_both_locs.user_location.values:
            if(x == ''):
                print('empty')
                continue
            try:
                user_lat.append(locator.geocode(x, timeout = 3).latitude)
                user_long.append(locator.geocode(x, timeout = 3).longitude)
            except HTTPError:
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