import urllib.request
import base64
import requests
# import mimetypes, urllib3


## Class to do some image formating before passing in Flickr imgs to Species Classifcation API
class Image:
    
    def __init__(self):
        return
    
    ## base64 encoding of images 
    ## (helps to embed in html display with species classification API)
    def get_as_base64(self, url):
        return requests.get(url).content
    

    def is_url_image(self, image_url):
        image_formats = ("image/png", "image/jpeg", "image/jpg")
        r = requests.head(image_url)
        if r.headers["content-type"] in image_formats:
            return True
        return False

        
    ## build dictionaries with name, url, and data (base64) fields out of 
    ## unsorted documents in flickr collection so we can sort with MS species classification API
    def get_flickr_img_dicts(self, db, collection, numToClassify):
        
        # connect to mongoDB collection and only retrieve unsorted docs
        res = db[collection].find({'relevant': None })
        
        # list to return of image dictionaries, each in format:
        '''dict = {'name': ObjectId from collection, 
                   'url': img_url from flickr, 
                   'data': base64 encoding of img
                   }
        '''
        img_dictionaries = []
        count_removed = 0
        # go through results and add base64 img representation using img url
        for item in res[0:numToClassify]:
            _id = item['_id']
            try:
                url = item['url']
            except KeyError:
                db[collection].remove({'_id': _id})
                count_removed += 1
                continue
                
            ##only sort through docs that have an image available
            if url != "" and self.is_url_image(url):
                img_dict = {'name': _id,
                             'url': url,
                             'data': self.get_as_base64(url)
                           }
                img_dictionaries.append(img_dict)
            else:
                count_removed += 1
                db[collection].remove({'_id': _id})
            
        print('Total removed: {}'.format(count_removed))
        return img_dictionaries
        