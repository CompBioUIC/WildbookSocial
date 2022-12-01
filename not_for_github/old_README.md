# ReadMe.md

Contents:
---------

1. backup_data(old): folder with outdated csv files + other data previously used to generate figures. Has now been outdated since this data does not contain information on ALL  filtered data

2. flickr_unique_urls: folder with csv files used to create dataframes consisting of unique urls across all collections per species. These csv files were used to cross-check overlapping documents (ex. same image stored in multiple species collections) and make sure relevant/wild status was consistent across collections. (These files were previously in the same directory as the jupyter notebooks that use them (species_flickr...py), so may have to adjust code accordingly to use them again if needed)

3. flickr_user_and_encounter_locations: folder with species coordinate csv files. Each csv file will contain any/all user and/or encounter location information we can find for RELEVANT encounters (wild status can vary, but docs must be relevant). These files will be used to generate encounter/user distribution maps based on geographical information available.
	3a. inside this folder, theres another folder mongo_db_relevant_docs_data, which contains CSV files of all relevant documents in our mongodb species collections. Each csv has fields directly gathered from our mongodb attributes: 
	0. relevant
	1.url, 
	2. title, 
	3. latitude (of encounter), 
	4. longitude (also of encounter), 
	5. wild, 
	6. datetaken, 
	7. owner, and 
	8. ownername. 
	12. confidence (MS classifier prediction) - note: some entries/collections may not have this field available if MS classifier was not used 
	
	For creating csvs from mongodb purposes: query:'
	Select fields in order:
    	1) datetaken
    	2) latitude
    	3) longitude
    	4) owner
    	5) ownername
    	6) relevant
    	7) title
    	8) url
    	9) wild
    	10) confidence (can use excel to add empty column for consistency when merging all species collection csvs into one pooled csv per species)
	
	Select CSV as export file type, and after navigating to appropriate directory (mongo_db_relevant_docs_data), rename the file to the format:
	species_collection_name_relevant_images.csv
    	
	Added into merged/pooled csv of data from all the species' collections
    	11) user latitude
    	12) user longitude
    	
    	13) residing collection
	
	
	- These csv files will be merged by same species to create an overall spreadsheet of all UNIQUE (no duplicates) relevant images pooled together by species with encounter and user lat/long coordinates/locations (if available) and stored in pooled_coordinate_csvs. The maps folder contains figures plotting user, encounter, and any connections between them on a geographic map. There should be a total of six spreadsheets (one per species) in the flickr_user_and_encounter_locations/mongo_db_relevant_docs/pooled_coordinate_csvs folder directory. Each spreadsheet will have all attributes 1-8 noted above (may have missing entries), as well as additional attributes (9) residing collections (collection url can be found in mongodb), (10) user latitude, (11) user longitude)

4. Jupyter Notebooks: 


### Flickr: 
- <Species_Name>_FlickrClassifierPlayground.ipynb: these notebooks contain data cleaning operations, as well as code that was used to integrate the MS classifier for relevance classification assistance. They also contain the code for cross-checking rel/wild labels across the species' collections.

- FlickrPlayground.ipynb: contains the first iteration of analytics completed for a partial subset of our flickr data. These are now outdated and need to be rerun with newly finished filtered data (as of Jan 24, 2022). Will keep using this file to generate analytics figures for flickr species collections (combined and individually)

- FlickrPlayground-HumpbackWhaleSpecificClassifierLocations.ipynb: a test notebook for gathering info on test documents run through the MS classifier. Contains some geospatial information

- FlickrClassifierPlayground.ipynb: Testing File for the Implementation of MS Classifier with Flickr Data to help speed up classification for ground truths (after integration into species specific classifier playgrounds, this file is no longer useful, but will keep for reference)

### iNaturalist

- iNaturalist.ipynb: one-stop for all analytics, data collection + data filtration from iNaturalist

### YouTube

- YouTube.ipynb: one-stop for all analytics, data collection + data filtration from YouTube