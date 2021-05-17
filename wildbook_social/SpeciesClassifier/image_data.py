import urllib.request
import base64
import requests

## Class to do some image formating before passing in Flickr imgs to Species Classifcation API
class Image:
    
    def __init__(self):
        return
    
    ## base64 encoding of images 
    ## (helps to embed in html display with species classification API)
    def get_as_base64(self, url):
        return requests.get(url).content

        
    ## build dictionaries with name, url, and data (base64) fields out of 
    ## unsorted documents in flickr collection so we can sort with MS species classification API
    def get_flickr_img_dicts(self, db, collection):
        
        # connect to mongoDB collection and only retrieve unsorted docs
        res = db[collection].find({'relevant': None })
        
        # list to return of image dictionaries, each in format:
        '''dict = {'name': ObjectId from collection, 
                   'url': img_url from flickr, 
                   'data': base64 encoding of img
                   }
        '''
        img_dictionaries = []
        
        # go through results and add base64 img representation using img url
        for item in res[0:10]:
            _id = item['_id']
            url = item['url']
            ##only sort through docs that have an image available
            if url != "":
                img_dict = {'name': _id,
                             'url': url,
                             'data': self.get_as_base64(url)
                           }
                img_dictionaries.append(img_dict)
        
        return img_dictionaries
        