import requests
import base64
from IPython.display import Image
from IPython.core.display import HTML
from azure.storage.blob import ContainerClient

#code adapted from Species Classification API demo
# https://www.microsoft.com/en-us/ai/ai-for-earth-tech-resources
# http://dolphinvm.westus2.cloudapp.azure.com/ai4e/notebooks/species-classification-api-demo.html

# Global Constants related to the Species Classification API
CONTENT_TYPE_KEY = 'Content-Type'
CONTENT_TYPE = 'application/octet-stream'
AUTHORIZATION_HEADER = 'Ocp-Apim-Subscription-Key'
BASE_URL = 'https://aiforearth.azure-api.net/'
CLASSIFY_FORMAT = '{0}/species-classification/v{1}/predict?topK={2}&predictMode={3}'
API_VERSION = '2.0'
PREDICT_MODE = 'classifyOnly'
API_KEY = '3c313eb853de41788b3e35e9bcf1ba2e' 

class SpeciesClassifier:
    
    def __init__(self):
        return
        
    def get_images(self, search_term=None):
        if search_term is None:
            return self.get_blob_images()
        else:
            return self.get_bing_images(search_term)

    def get_bing_images(self, search_term):

        headers = {"Ocp-Apim-Subscription-Key" : BING_SUBSCRIPTION_KEY}
        params  = {"q" : search_term, "license" : BING_IMAGE_LICENSE, "imageType" : BING_IMAGE_TYPE, 
                   "safeSearch" : BING_SAFE_SEARCH}
        response = requests.get(BING_SEARCH_URL, headers=headers, params=params)
        response.raise_for_status()
        search_results = response.json()

        images_data = []
        count = 0

        for img in search_results["value"][:16]:

            if(count == MAX_NUM_SEARCH_IMAGES): break

            image_data = requests.get(img["thumbnailUrl"])
            image_data.raise_for_status()
            images_data.append({"url": img["thumbnailUrl"], "name" : search_term, "data": image_data.content})
            count += 1

        return images_data   

    def get_blob_images(self):

        images_data = []
        generator = blob_container_client.list_blobs()

        for blob in generator:                  
            blob_client = blob_container_client.get_blob_client(blob.name)
            blob_content = blob_client.download_blob().readall()
            imagebase64 = base64.b64encode(blob_content).decode('utf-8')
            images_data.append({"url": "data:image/png;base64," + str(imagebase64), "name" : blob.name, "data": blob_content})

        return images_data   

    def get_images_html_string(self, image_list):

        html_string = ""
        for i in range(len(image_list)):
            html_string += "<img class='image' src='"+ image_list[i]['url'] + "'/>"
        return html_string

    def display_raw_images(self, images): 

        html_string = "<style>" \
                      "* { box-sizing: border-box;} " \
                      " .column {float: left;width: 50%;padding: 10px; overflow:visible} " \
                      " .column > img {height:50%}" \
                      " .row:after {content: "";display: table;clear: both;} " \
                      "</style>"

        html_string += '<div class="row"><div class="column">' 

        #get images in even index
        image_list = images[::2]
        html_string += self.get_images_html_string(image_list)  
        html_string += "</div>"

        html_string += '<div class="column">'

        #get images in odd index
        image_list = images[1::2]
        html_string += self.get_images_html_string(image_list)
        html_string += "</div></div>"

        display(HTML(html_string))  

    def display_single_image(self, image): 

        html_string = "<style>" \
                      "div.output_subarea{overflow-x:hidden !important}" \
                      ".container{margin:0 auto}" \
                      ".single_image{width:50%} " \
                      "</style>"

        html_string += "<div class='container'>" \
                           "<div class='image_container'>" \
                               "<img class='single_image' src='"+ image['url'] + "'/>"\
                           "</div>" \
                       "</div>"


        display(HTML(html_string))  
        
    #manually filter images to get ground truth of species predictions
    def get_ground_truth(self, img_url, species_prediction): 

        html_string = "<style>" \
                      "div.output_subarea{overflow-x:hidden !important}" \
                      ".container{margin:0 auto}" \
                      ".single_image{width:50%} " \
                      "</style>"

        html_string += "<div class='container'>" \
                           "<div class='image_container'>" \
                               "<img class='single_image' src='"+ img_url + "'/>"\
                           "</div>" \
                       "</div>"


        display(HTML(html_string))
        print('Species Predicted In Image: ', species_prediction)
        print("Is the species prediction correct? (y/n):", end = " ")
        if input() == "n": 
            print("The predicted species is incorrect. Please specify the correct species: ")
            true_prediction = input()
        else:
            true_prediction = species_prediction
        
        return true_prediction

    def display_classification_results(self, species, species_common, progress, is_first_item): 

        html_string = ""

        if(is_first_item):

            html_string = "<style>" \
                          ".progress-container {margin:0 auto; min-height: 25px;margin:0;width:100%; margin-top:10px}" \
                          ".progress-bar{background-color:#ffc107; padding:3px}" \
                          ".progress-text{color:black; margin-top:5px;} " \
                          ".species .species-common {" \
                          " color:black !important; font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;" \
                          " font-size:14px;line-height:20px;}" \
                          "</style>"

        progress = progress + "%"
        style = "width:" + progress + ""
        bing_search_link = 'https://bing.com/images/search?q=' + species

        html_string += "<a style='color:black;' class='species' href='" + bing_search_link +"' target='_blank'>" + species + "</a>" \
                       "<span class='species-common'>  ( " + species_common + " ) </span>" \
                       "<div class='progress progress-container'>" \
                       "<div class='progress-bar' style='" + style + "' >" \
                       "<span class='progress-text'>" + progress + "</span></div></div>" \

        display(HTML(html_string))

    def build_classify_url(self, topK=5, base_url=BASE_URL, version=API_VERSION, predictMode=PREDICT_MODE):

        return CLASSIFY_FORMAT.format(base_url, version, topK, predictMode)

    def get_api_headers(self, content_type):

        return { CONTENT_TYPE_KEY: content_type, AUTHORIZATION_HEADER: API_KEY }

    def get_api_response(self, imgdata):

        url = self.build_classify_url()

        #print('Running API...')

        r = requests.post(url, headers=self.get_api_headers(CONTENT_TYPE), data=imgdata) 

        if(r.status_code != 200):
            return r.json(), True

        #print('...done')

        return r.json(), False

    def classify_and_display_results(self, image_data):

        result = self.get_api_response(image_data['data'])

        if(result == None):

            print ("Error occured while calling API...Please try again")
            return

        self.display_single_image(image_data)

        print('result: ', result)
        predictions = result[0]['predictions']

        is_first_item = True 

        for item in predictions:

            species = item['species']
            species_common = item['species_common']
            prob = round(item['confidence'], 2)

            self.display_classification_results(species, species_common,  str(prob), is_first_item)   
            is_first_item = False

    ## run each non-sorted image through the classifier to generate a 'relevant' status
    def predict_image_relevancy(self, db, collection, flickr_img_dicts, species_keyword):
        ## feed in flickr_img_dicts to MS Classification API.
        for image in flickr_img_dicts:
            res = self.get_api_response(image['data']) 
            (predictions_dict, status_bool_value) = res

            ## search for most general keyword in predictions generated by API,
            ## as API does not classify by giraffe sub-species. So, we are limited 
            ## to using the API to simply check if a giraffe is in frame (May differ
            ## across species)
            relevant_status = False
            for item in predictions_dict['predictions']:
                if item['species_common'] == species_keyword:
                    relevant_status = True
                    ## Here, set 'relevant' field as True for corresponding doc of img in Flickr collection
                    db[collection].update_one({'_id': image['name']}, {'$set': {'relevant': True}})

            if relevant_status == False:
                ## set relevant: False in mongoDB for corresponding img (search by obj id)
                db[collection].update_one({'_id': image['name']}, {'$set': {'relevant': False}})
                
        print('Done predicting if {} is in frame...'.format(species_keyword))
