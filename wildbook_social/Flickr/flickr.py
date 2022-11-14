import requests
import json
import time


class Flickr:
    def __init__(self, db = None):
        self.db = db


    def clean_data(self, reponse_data):
        
        post_metadata = []
        
        for photo in reponse_data['photos']['photo']:        
            data = {}
            data["id"] = photo["id"]
            data["title"] = photo["title"]
            data["owner"] = photo["owner"]
            data["ownername"] = photo["ownername"]
            data["dateupload"] = photo["dateupload"]
            data["datetaken"] = photo["datetaken"]
            data["lastupdate"] = photo["lastupdate"]
            data["views"] = photo["views"]
            data["accuracy"] = photo["accuracy"]
            data["latitude"] = photo["latitude"]
            data["longitude"] = photo["longitude"]
            data["media"] = photo["media"]

            data["encounter"] = {
                            "locationIDs": [], #[Wildbook]
                            "dates": [], #[Wildbook]
                        }
            data["animalsID"] =  [] #[Wildbook]
            data["curationStatus"] =  None #[Wildbook]
            data["curationDecision"] = None #Wildbook]
            data["gatheredAt"] =  time.ctime()
            data["relevant"] = None
            data["wild"] = None
            data["type"] = "flickr"
            try:
                data["url"] = photo["url_l"] #field used to be named 'url_l' for data
            except:
                data["url"] = ""
            data["tags"] = photo["tags"]
            data["description"] = photo['description']['_content']
            post_metadata.append(data)
        return post_metadata

        
    def search(self, q, date_since="2019-12-01", bbox = False, saveTo=False): 
        """ Connects to Flickr API and passes in query contained in `q` parameter. After data is retrieved, clean_data is called to organize metadata
        of posts into suitable format for MongoDB. """
                
        #check to see if a collection and MongoDB instance were passed in to save our results to
        if (saveTo and not self.db):
            saveTo = False
            print("No 'db' argument was provided. Provide a MongoDB instance to save Flickr Data.")
        
        #replace spaces with '+' in our query term passed in
        keyword = q.replace(' ','+')
        
        #configure query url accordingly based on whether we are passing in bbox parameter or not
        if bbox:
            coords = bbox.replace(',', '%2C')
            base_url =  "https://www.flickr.com/services/rest/?method=flickr.photos.search&api_key=6ab5883201c84be19c9ceb0a4f5ba959&text=\
                    {text}&min_taken_date={min_date}&extras=description%2Cdate_upload%2C+date_taken%2C+owner_name%2C+last_update%2C+geo%2C+tags%2C+views%2C+media%2C+url_l&page=\
                    {page}&bbox={bbox_coords}&format=json&nojsoncallback=1"
            url = base_url.format(text=keyword,min_date=date_since,bbox_coords = coords, page='1') #tags=keyword
        else:
            base_url = "https://www.flickr.com/services/rest/?method=flickr.photos.search&api_key=6ab5883201c84be19c9ceb0a4f5ba959&text=\
                    {text}&min_taken_date={min_date}&extras=description%2Cdate_upload%2C+date_taken%2C+owner_name%2C+last_update%2C+geo%2C+tags%2C+views%2C+media%2C+url_l&page=\
                    {page}&format=json&nojsoncallback=1"
            url = base_url.format(text=keyword,min_date=date_since, page='1') #tags=keyword
                    
        #pull and clean metadata from Flickr API
        r = requests.get(url)
        response_data = r.json()
        data = self.clean_data(response_data)
        
        #save cleaned metadata to MongoDB collection (saveTo)
        if (saveTo and self.db):
            print('saving Flickr posts metadata...')
            for item in data:
                self.db.addItem(item, saveTo)
        
        #initialize list of cleaned metadata dictionaries to return at completion of function
        cleaned_metadata = []
        cleaned_metadata.append(data)
        
        #get number of pages with results for Flickr API query 
        pages = response_data['photos']['pages']
        print(pages,'pages found with results for:',keyword)
        
        #paginate through the remaining pages of results 
        for page in range(2, pages+1):
            
            #output so user can keep track of page updates as data is processed + saved
            #there are 100 posts per page
            print('page no.', page)
            
            #configure query url with updated `page` parameter to get that page's results
            if bbox:
                coords = bbox.replace(',', '%2C')
                url = base_url.format(text=keyword,min_date=date_since,bbox_coords = coords, page=page) #tags=keyword
            else:
                url = base_url.format(text=keyword,min_date=date_since, page=page) #tags=keyword
            
            #pull and clean metadata from Flickr API
            r = requests.get(url)
            try:
                response_data = r.json()
            except JSONDecodeError:
                print("r: ", r)
            data = self.clean_data(response_data)
            
            #save cleaned metadata to MongoDB collection (saveTo)
            if (self.db is not None):
                print('saving Flickr posts metadata...')
                for item in data:
                    self.db.addItem(item, saveTo)

            #save current page's posts' metadata to return at end
            cleaned_metadata.append(data)
        
        #return list of processed metadata dictionaries (one dict per post)
        return cleaned_metadata
    

 #method to get user locations with flickr.people.getInfo()
    def getUserLocations(self, user_ids):
        
        '''
            function to retrieve flickr user locations
            __________________________________________
            
            Input:
                user_ids: a list of owner/user ids for whom we want to retrieve the location from (pd.Series type)
            
            Returns:
                user_locations: a list of the user location information retrieved with the people.getInfo flickr api for each user id. 
                                Note: the location information is just returned as the location name in plain english. Will need to 
                                perform additional processing on this data to extract geocoordinate location (lat, long).
            
        '''
        
        user_locations= []
        for user_id in user_ids:
            #get people.getInfo response from flickr api
            base_url = "https://www.flickr.com/services/rest/?method=flickr.people.getInfo&\
                        api_key=b3fb43d7040c83c55121688a2de47b1f&user_id={}&format=json&nojsoncallback=1"
            
            user_id = user_id.replace('@', '%40')
            url = base_url.format(user_id)
            r = requests.get(url)
            
            #attempt to retrieve response and format in json
            try:
                response = r.json()
            except JSONDecodeError:
                print(r)
                print(user_id)
                print(url)
                break
            
            #attempt to retrieve user location
            try:
                user_location = response['person']['location']['_content'] #for photo in response['photo']
            except KeyError:
                user_location = None
                
            #add user loc to output list
            user_locations.append(user_location)
            
        return user_locations
    
            
            


        
