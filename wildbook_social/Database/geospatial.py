import csv
import pandas as pd 
import geopandas as gpd
import descartes
from shapely.geometry import Point
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Bing
from geopy.geocoders import Nominatim
from geopy import distance
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import matplotlib.pyplot as plt
import seaborn as sns


## class that handles all visuals and computations to extract encounter and/or user locations
## of documents retrieved across each different social media platform
class Geospatial:
    
    def __init__(self, db_obj):
        self.db = db_obj
    
     
    def heatmap(self,collection, csvName):
        '''customized to youtube only so far: generates a csv with videoID and location of encounter 
           for all wild encounters
           might be able to delete this if the section of code in notebook works
        '''
        
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
    
    
    def getEncounterLocsiNat(self, wild_collection):
        '''create a dataframe of latitudes and longitudes of encounter locs
           for each document in iNat wild_collection
        '''
        
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
        
        
    def reverseGeocodeYT(self, wild_collection, video_channel_country_dics):
        '''
            populates a df with both encounter and user locs from docs in YT wild col within the timeframe  
        '''
        
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
        #key = 'AsmRvBYNWJVq55NBqUwpWj5Zo6vRv9N_g6r96K2hu8FLk5ob1uaXJddVZPpMasio'
        #locator = Bing(key)
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
        

    def reverseGeocodeFlickr(self, user_info, wild_collection):
        '''
            reverse geocode each user location for each corresponding item
            then return df with latitude and longitude of encounter locations 
            and latitude and longitude of user locations
        '''
           
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
                                                  
        #add enc_coords list and user_coords list to df_both_locs
        df_both_locs['user_lat'] = user_lat
        df_both_locs['user_long'] = user_long
        
        return df_both_locs 
    
    
    def plotEncounterAndUserLocations(self, collection, df_coords, platform, enc_locs = False, user_locs = False):
        '''
            function to visualize encounter and corresponding user locations for posts via map using plotly express
        '''
        
        #initialize a space for figure
        fig = go.Figure()
        
        #access different platform's text keywords/labels for labeling each dot on the map
        keys = {'youtube': ['encounter_loc', 'user_country'], 'flickr_june_2019': ['id', 'user_location'], 'iNaturalist': ['enc_lat']}
        
       
        #add the encounter location markers (red)
        if enc_locs == True:
            encounter_loc_label = keys[platform][0]
            fig.add_trace(go.Scattergeo(
                        lon = df_coords['enc_long'],
                        lat = df_coords['enc_lat'],
                        hoverinfo = 'text',
                        text = df_coords[encounter_loc_label], #df_coords['encounter_loc'], 
                        mode = 'markers',
                        marker = dict(
                            size = 4,
                            color = 'rgb(255, 0, 0)',
                            line = dict(
                                width = 3,
                                color = 'rgba(68, 68, 68, 0)'
                            )
                        )))

    
    
        #add the user country markers (green)
        if user_locs == True:
            user_country_label = keys[platform][1]
            fig.add_trace(go.Scattergeo(
                        lon = df_coords['user_long'],
                        lat = df_coords['user_lat'],
                        hoverinfo = 'text',
                        text = df_coords[user_country_label], 
                        mode = 'markers',
                        marker = dict(
                            size = 4,
                            color = 'rgb(0, 255, 0)',
                            line = dict(
                                width = 3,
                                color = 'rgba(65, 65, 65, 0)'
                            )
                        )))

        #add path traces (blue) from user country to encounter locations, if both features are available
        if user_locs and enc_locs:
            for i in range(len(df_coords)):
                fig.add_trace(
                            go.Scattergeo(
                                lon = [df_coords['user_long'][i], df_coords['enc_long'][i]],
                                lat = [df_coords['user_lat'][i], df_coords['enc_lat'][i]],
                                mode = 'lines',
                                line = dict(width = 1,color = 'blue')#,
                            )
                        )
                            
        
        #update parameters of map figure to display
        fig.update_layout(
                    title_text = collection + " sightings since 06.01.2019",
                    showlegend = False,
                    geo = dict(
                        scope = 'world',
                        projection_type = 'equirectangular', #'azimuthal equal area',
                        showland = True,
                        landcolor = 'rgb(243, 243, 243)',
                        countrycolor = 'rgb(204, 204, 204)',
                    ),
                )

        #display
        fig.show("notebook")
        
    
    def visualizeDistanceDifferences(self, df_coords, collection):
        ''' function to plot a histogram on the differences between encounter and corresponding user locations
            x-axis: distance amount (km)
            y-axis: frequency of the distance difference among posts'''
        
        #calculate distance difference for each wild encounter
        distances=[]
        for idx in df_coords.index:
            enc_loc = (df_coords.enc_lat[idx], df_coords.enc_long[idx])
            user_loc = (df_coords.user_lat[idx], df_coords.user_long[idx])
            dist= distance.distance(enc_loc, user_loc).km
            distances.append(dist)
            
        #plot histogram of distances
        plt.figure(figsize=(10,10))
        sns.histplot(data=distances, bins=10)
        plt.title('Differences in Encounter and User Locations for ' + collection + ' Wild Encounters')
        plt.xlabel('Distance(km)')
        plt.ylabel('Frequency')
        