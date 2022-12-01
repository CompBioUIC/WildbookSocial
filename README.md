# Using Social Media APIs to collect and understand data for wildlife monitoring applications.

This repository contains a set of python files and jupyter notebooks connecting to YouTube, Flickr, and iNaturalist APIs to collect wildlife encounter data. 

## Contents

1. **wildbook_social** folder: contains python scripts to connect to social media platform APIs. Each platform gets its own folder with a nested script inside that does the actual connecting to the API. Data is retrieved from API and formatted before being stored in its respective MongoDB database/collection. 
- The **Database** folder contains scripts used for formatting/updating and visualizing data from MongoDB. 
- The **Geolocations** folder contains a script that is used to help handle coordinate data during visualization. 
- The **SpeciesClassifier** folder contains code previously used to configure Microsoft's Species Classification repository and assign relevant statuses to large amounts of pictures where manual annotation was cumbersome. The SpeciesClassifier no longer functions, so as of Dec 1 2022, these files are no longer relevant to our use. 

2. **notebooks** folder: contains jupyter notebooks that connect to and query social media platform APIs. Flickr and YouTube notebooks also contain sections for the user to manually annotate images and assign relevant and captivity statuses. 
- The **species_classifier** subfolder contains notebooks that previously ran the Microsoft species classifier to accelerate manual annotation. 

3. **analysis** folder: contains jupyter notebooks that perform data analysis on data collected from social media APIs and understand any underlying biases. Currently a work in progress to organize and format figures neatly. 

4. **csv, figures, and json** folders: self explanatory. Contain files/figures for analysis.  
