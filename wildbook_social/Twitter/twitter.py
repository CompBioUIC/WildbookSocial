import tweepy
from datetime import date

class Twitter:
    def __init__(self, credentials, db=None):
        self.CONSUMER_KEY = credentials["CONSUMER_KEY"]
        self.CONSUMER_SECRET = credentials["CONSUMER_SECRET"]
        self.ACCESS_TOKEN = credentials["ACCESS_TOKEN"]
        self.ACCESS_SECRET = credentials["ACCESS_SECRET"]
        
        self.auth = tweepy.OAuthHandler(self.CONSUMER_KEY, self.CONSUMER_SECRET)
        self.auth.set_access_token(self.ACCESS_TOKEN, self.ACCESS_SECRET)
        self.api = tweepy.API(self.auth, wait_on_rate_limit=True)
        
        self.db = db
        
#     def search(self, q, date_since="2019-06-01", limit=1, saveTo=False, collection=False):
    def search(self, q, limit=1, saveTo=False, collection=False):
        ''' 
        q - search query, (ex. "Whale Shark")
        limit - number of results (ex. 10 or 100)
        saveTo - Saves all retrieved videos to provided collection
        '''
        if (saveTo and not self.db):
            saveTo = False
            print("Please provide 'db' argument with an instance to database to save tweet(s).")
        #search query must be URL encoded
#         q_encoded = q.replace(' ', '+').replace(':', '%3A')
        q_encoded = q
        print(q_encoded) #just a checkpoint
        #since_id needs to be included so we don't paginate through the same results - read more in tweepy documentation on
        #how to handle this tomorrow. 'since' should be set to newest collected post ID
        tweets = tweepy.Cursor(self.api.search, q=q_encoded, lang="en", count = 100, until= date.today(), \
                               ).items(limit) #since= "1281693437880700928"
        results = []
        
        #loops through to get certain information
        for tweet in tweets:
            tweetDic = {}
            #if there is a media key in entities then get the user name, location,
            #id, date created. url and hashtags from the post
            if (self._checkMedia(tweet) != False) and (tweet.retweeted == False) :
                
                tweetId = tweet.id_str
                createdAt = str(tweet.created_at)
                url = self._checkMedia(tweet)
                self._checkExtendedEntities(tweet)
                user_name = tweet.user.name
                handle = tweet.user.screen_name
                location = tweet.user.location
                user_id = tweet.user.id_str
                hashtags = tweet.entities["hashtags"]
                encounter_loc = tweet.place #retrieve enc location if geotagged
                
                tweetDic["_id"] = tweetId
                tweetDic["created_at"] = createdAt
                tweetDic["user_location"] = location
                tweetDic["encounter_loc"] = encounter_loc #added to retrieve encounter location - 07.20.20
                tweetDic["user_id"] = user_id
                tweetDic["img_url"] = str(url)
                tweetDic["user_name"] = user_name
                tweetDic["user_handle"] = handle
                tweetDic["hashtags"] = hashtags
                tweetDic["wild"] = None
                tweetDic["relevant"] = None

                # Saving item in database
                if (saveTo):
                    self.db.addItem(tweetDic, saveTo)
                results.append(tweetDic)
                
        return results
                
        
    #checks to see if there is media key in entities
    @staticmethod
    def _checkMedia(tweets):
        if "media" in tweets.entities:
            return tweets.entities["media"][0]["media_url"]
        else:
            return False
        
        
    #checks to see if there is an extended entities attribute
    #if so, loop through all of the media and return it
    @staticmethod
    def _checkExtendedEntities(tweets):
        if(hasattr(tweets, 'extended_entities')):
            for img in range(0, len(tweets.extended_entities["media"])):
                return(tweets.extended_entities["media"][img]["media_url"])
            return True
        else:
            return False